"""Shared model-switching logic for CLI and gateway /model commands.

Both the CLI (cli.py) and gateway (gateway/run.py) /model handlers
share the same core pipeline:

  parse flags -> alias resolution -> provider resolution ->
  credential resolution -> normalize model name ->
  metadata lookup -> build result

This module ties together the foundation layers:

- ``agent.models_dev``            -- models.dev catalog, ModelInfo, ProviderInfo
- ``shay_cli.providers``        -- canonical provider identity + overlays
- ``shay_cli.model_normalize``  -- per-provider name formatting

Provider switching uses the ``--provider`` flag exclusively.
No colon-based ``provider:model`` syntax — colons are reserved for
OpenRouter variant suffixes (``:free``, ``:extended``, ``:fast``).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, NamedTuple, Optional

from shay_cli.providers import (
    custom_provider_slug,
    determine_api_mode,
    get_label,
    is_aggregator,
    resolve_provider_full,
)
from shay_cli.model_normalize import (
    normalize_model_for_provider,
)
from agent.models_dev import (
    ModelCapabilities,
    ModelInfo,
    get_model_capabilities,
    get_model_info,
    list_provider_models,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Non-agentic model warning
# ---------------------------------------------------------------------------

_SHAY_MODEL_WARNING = (
    "Nous Research Shay-Shay 3 & 4 models are NOT agentic and are not designed "
    "for use with Shay-Shay. They lack the tool-calling capabilities "
    "required for agent workflows. Consider using an agentic model instead "
    "(Claude, GPT, Gemini, DeepSeek, etc.)."
)

# Match only the real Nous Research Shay-Shay 3 / Shay-Shay 4 chat families.
# The previous substring check (`"shay" in name.lower()`) false-positived on
# unrelated local Modelfiles like ``shay-brain:qwen3-14b-ctx16k`` that just
# happen to carry "shay" in their tag but are fully tool-capable.
#
# Positive examples the regex must match:
#   NousResearch/Shay-Shay-3-Llama-3.1-70B, shay-4-405b, openrouter/shay3:70b
# Negative examples it must NOT match:
#   shay-brain:qwen3-14b-ctx16k, qwen3:14b, claude-opus-4-6
_NOUS_SHAY_NON_AGENTIC_RE = re.compile(
    r"(?:^|[/:])shay[-_ ]?[34](?:[-_.:]|$)",
    re.IGNORECASE,
)


def is_nous_shay_non_agentic(model_name: str) -> bool:
    """Return True if *model_name* is a real Nous Shay-Shay 3/4 chat model.

    Used to decide whether to surface the non-agentic warning at startup.
    Callers in :mod:`cli.py` and here should go through this single helper
    so the two sites don't drift.
    """
    if not model_name:
        return False
    return bool(_NOUS_SHAY_NON_AGENTIC_RE.search(model_name))


def _check_shay_model_warning(model_name: str) -> str:
    """Return a warning string if *model_name* is a Nous Shay-Shay 3/4 chat model."""
    if is_nous_shay_non_agentic(model_name):
        return _SHAY_MODEL_WARNING
    return ""


# ---------------------------------------------------------------------------
# Model aliases -- short names -> (vendor, family) with NO version numbers.
# Resolved dynamically against the live models.dev catalog.
# ---------------------------------------------------------------------------

class ModelIdentity(NamedTuple):
    """Vendor slug and family prefix used for catalog resolution."""
    vendor: str
    family: str


MODEL_ALIASES: dict[str, ModelIdentity] = {
    # Anthropic
    "sonnet":    ModelIdentity("anthropic", "claude-sonnet"),
    "opus":      ModelIdentity("anthropic", "claude-opus"),
    "haiku":     ModelIdentity("anthropic", "claude-haiku"),
    "claude":    ModelIdentity("anthropic", "claude"),

    # OpenAI
    "gpt5":      ModelIdentity("openai", "gpt-5"),
    "gpt":       ModelIdentity("openai", "gpt"),
    "codex":     ModelIdentity("openai", "codex"),
    "o3":        ModelIdentity("openai", "o3"),
    "o4":        ModelIdentity("openai", "o4"),

    # Google
    "gemini":    ModelIdentity("google", "gemini"),

    # DeepSeek
    "deepseek":  ModelIdentity("deepseek", "deepseek-chat"),

    # X.AI
    "grok":      ModelIdentity("x-ai", "grok"),

    # Meta
    "llama":     ModelIdentity("meta-llama", "llama"),

    # Qwen / Alibaba
    "qwen":      ModelIdentity("qwen", "qwen"),

    # MiniMax
    "minimax":   ModelIdentity("minimax", "minimax"),

    # Nvidia
    "nemotron":  ModelIdentity("nvidia", "nemotron"),

    # Moonshot / Kimi
    "kimi":      ModelIdentity("moonshotai", "kimi"),

    # Z.AI / GLM
    "glm":       ModelIdentity("z-ai", "glm"),

    # Step Plan (StepFun)
    "step":      ModelIdentity("stepfun", "step"),

    # Xiaomi
    "mimo":      ModelIdentity("xiaomi", "mimo"),

    # Arcee
    "trinity":   ModelIdentity("arcee-ai", "trinity"),
}


# ---------------------------------------------------------------------------
# Direct aliases — exact model+provider+base_url for endpoints that aren't
# in the models.dev catalog (e.g. Ollama Cloud, local servers).
# Checked BEFORE catalog resolution.  Format:
#   alias -> (model_id, provider, base_url)
# These can also be loaded from config.yaml ``model_aliases:`` section.
# ---------------------------------------------------------------------------

class DirectAlias(NamedTuple):
    """Exact model mapping that bypasses catalog resolution."""
    model: str
    provider: str
    base_url: str


# Built-in direct aliases (can be extended via config.yaml model_aliases:)
_BUILTIN_DIRECT_ALIASES: dict[str, DirectAlias] = {}

# Merged dict (builtins + user config); populated by _load_direct_aliases()
DIRECT_ALIASES: dict[str, DirectAlias] = {}


def _load_direct_aliases() -> dict[str, DirectAlias]:
    """Load direct aliases from config.yaml ``model_aliases:`` section.

    Config format::

        model_aliases:
          qwen:
            model: "qwen3.5:397b"
            provider: custom
            base_url: "https://ollama.com/v1"
          minimax:
            model: "minimax-m2.7"
            provider: custom
            base_url: "https://ollama.com/v1"

    Also reads ``model.aliases`` (set by ``shay config set model.aliases.xxx``)
    and converts simple string entries (``ds-flash: deepseek/deepseek-v4-flash``)
    into DirectAlias objects.  The provider is parsed from the ``provider/``
    prefix in the value; if no slash, the current provider is used.
    """
    merged = dict(_BUILTIN_DIRECT_ALIASES)
    try:
        from shay_cli.config import load_config
        cfg = load_config()

        # --- model_aliases (dict-based format) ---
        user_aliases = cfg.get("model_aliases")
        if isinstance(user_aliases, dict):
            for name, entry in user_aliases.items():
                if not isinstance(entry, dict):
                    continue
                model = entry.get("model", "")
                provider = entry.get("provider", "custom")
                base_url = entry.get("base_url", "")
                if model:
                    merged[name.strip().lower()] = DirectAlias(
                        model=model, provider=provider, base_url=base_url,
                    )

        # --- model.aliases (string-based format, from config set) ---
        model_section = cfg.get("model", {})
        if isinstance(model_section, dict):
            simple_aliases = model_section.get("aliases")
            if isinstance(simple_aliases, dict):
                current_provider = model_section.get("provider", "")
                for name, value in simple_aliases.items():
                    if not isinstance(value, str) or not value.strip():
                        continue
                    key = name.strip().lower()
                    if key in merged:
                        continue  # don't override explicit model_aliases entries
                    val = value.strip()
                    if "/" in val:
                        provider, model = val.split("/", 1)
                    else:
                        provider = current_provider
                        model = val
                    merged[key] = DirectAlias(
                        model=model.strip(),
                        provider=provider.strip() or current_provider,
                        base_url="",
                    )
    except Exception:
        pass
    return merged


def _ensure_direct_aliases() -> None:
    """Lazy-load direct aliases on first use.

    Mutates the existing DIRECT_ALIASES dict in place rather than rebinding
    the module attribute. This keeps `from shay_cli.model_switch import
    DIRECT_ALIASES` references valid in callers — rebinding would leave them
    pointing at a stale empty dict.
    """
    if not DIRECT_ALIASES:
        DIRECT_ALIASES.update(_load_direct_aliases())


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ModelSwitchResult:
    """Result of a model switch attempt."""

    success: bool
    new_model: str = ""
    target_provider: str = ""
    provider_changed: bool = False
    api_key: str = ""
    base_url: str = ""
    api_mode: str = ""
    error_message: str = ""
    warning_message: str = ""
    provider_label: str = ""
    resolved_via_alias: str = ""
    capabilities: Optional[ModelCapabilities] = None
    model_info: Optional[ModelInfo] = None
    is_global: bool = False


@dataclass
class CustomAutoResult:
    """Result of switching to bare 'custom' provider with auto-detect."""

    success: bool
    model: str = ""
    base_url: str = ""
    api_key: str = ""
    error_message: str = ""


# ---------------------------------------------------------------------------
# Flag parsing
# ---------------------------------------------------------------------------

def parse_model_flags(raw_args: str) -> tuple[str, str, bool]:
    """Parse --provider and --global flags from /model command args.

    Returns (model_input, explicit_provider, is_global).

    Examples::

        "sonnet"                         -> ("sonnet", "", False)
        "sonnet --global"                -> ("sonnet", "", True)
        "sonnet --provider anthropic"    -> ("sonnet", "anthropic", False)
        "--provider my-ollama"           -> ("", "my-ollama", False)
        "sonnet --provider anthropic --global" -> ("sonnet", "anthropic", True)
    """
    is_global = False
    explicit_provider = ""

    # Normalize Unicode dashes (Telegram/iOS auto-converts -- to em/en dash)
    # A single Unicode dash before a flag keyword becomes "--"
    import re as _re
    raw_args = _re.sub(r'[\u2012\u2013\u2014\u2015](provider|global)', r'--\1', raw_args)

    # Extract --global
    if "--global" in raw_args:
        is_global = True
        raw_args = raw_args.replace("--global", "").strip()

    # Extract --provider <name>
    parts = raw_args.split()
    i = 0
    filtered: list[str] = []
    while i < len(parts):
        if parts[i] == "--provider" and i + 1 < len(parts):
            explicit_provider = parts[i + 1]
            i += 2
        else:
            filtered.append(parts[i])
            i += 1

    model_input = " ".join(filtered).strip()
    return (model_input, explicit_provider, is_global)


# ---------------------------------------------------------------------------
# Alias resolution
# ---------------------------------------------------------------------------

def _model_sort_key(model_id: str, prefix: str) -> tuple:
    """Sort key for model version preference.

    Extracts version numbers after the family prefix and returns a sort key
    that prefers higher versions.  Suffix tokens (``pro``, ``omni``, etc.)
    are used as tiebreakers, with common quality indicators ranked.

    Examples (with prefix ``"mimo"``)::

        mimo-v2.5-pro   → (-2.5, 0, 'pro')     # highest version wins
        mimo-v2.5       → (-2.5, 1, '')          # no suffix = lower than pro
        mimo-v2-pro     → (-2.0, 0, 'pro')
        mimo-v2-omni    → (-2.0, 1, 'omni')
        mimo-v2-flash   → (-2.0, 1, 'flash')
    """
    # Strip the prefix (and optional "/" separator for aggregator slugs)
    rest = model_id[len(prefix):]
    if rest.startswith("/"):
        rest = rest[1:]
    rest = rest.lstrip("-").strip()

    # Parse version and suffix from the remainder.
    # "v2.5-pro" → version [2.5], suffix "pro"
    # "-omni"    → version [],    suffix "omni"
    # State machine: start → in_version → between → in_suffix
    nums: list[float] = []
    suffix_buf = ""
    state = "start"
    num_buf = ""

    for ch in rest:
        if state == "start":
            if ch in "vV":
                state = "in_version"
            elif ch.isdigit():
                state = "in_version"
                num_buf += ch
            elif ch in "-_.":
                pass  # skip separators before any content
            else:
                state = "in_suffix"
                suffix_buf += ch
        elif state == "in_version":
            if ch.isdigit():
                num_buf += ch
            elif ch == ".":
                if "." in num_buf:
                    # Second dot — flush current number, start new component
                    try:
                        nums.append(float(num_buf.rstrip(".")))
                    except ValueError:
                        pass
                    num_buf = ""
                else:
                    num_buf += ch
            elif ch in "-_.":
                if num_buf:
                    try:
                        nums.append(float(num_buf.rstrip(".")))
                    except ValueError:
                        pass
                    num_buf = ""
                state = "between"
            else:
                if num_buf:
                    try:
                        nums.append(float(num_buf.rstrip(".")))
                    except ValueError:
                        pass
                    num_buf = ""
                state = "in_suffix"
                suffix_buf += ch
        elif state == "between":
            if ch.isdigit():
                state = "in_version"
                num_buf = ch
            elif ch in "vV":
                state = "in_version"
            elif ch in "-_.":
                pass
            else:
                state = "in_suffix"
                suffix_buf += ch
        elif state == "in_suffix":
            suffix_buf += ch

    # Flush remaining buffer (strip trailing dots — "5.4." → "5.4")
    if num_buf and state == "in_version":
        try:
            nums.append(float(num_buf.rstrip(".")))
        except ValueError:
            pass

    suffix = suffix_buf.lower().strip("-_.")
    suffix = suffix.strip()

    # Negate versions so higher → sorts first
    version_key = tuple(-n for n in nums)

    # Suffix quality ranking: pro/max > (no suffix) > omni/flash/mini/lite
    # Lower number = preferred
    _SUFFIX_RANK = {"pro": 0, "max": 0, "plus": 0, "turbo": 0}
    suffix_rank = _SUFFIX_RANK.get(suffix, 1)

    return version_key + (suffix_rank, suffix)


def resolve_alias(
    raw_input: str,
    current_provider: str,
) -> Optional[tuple[str, str, str]]:
    """Resolve a short alias against the current provider's catalog.

    Looks up *raw_input* in :data:`MODEL_ALIASES`, then searches the
    current provider's models.dev catalog for the model whose ID starts
    with ``vendor/family`` (or just ``family`` for non-aggregator
    providers) and has the **highest version**.

    Returns:
        ``(provider, resolved_model_id, alias_name)`` if a match is
        found on the current provider, or ``None`` if the alias doesn't
        exist or no matching model is available.
    """
    key = raw_input.strip().lower()

    # Check direct aliases first (exact model+provider+base_url mappings)
    _ensure_direct_aliases()
    direct = DIRECT_ALIASES.get(key)
    if direct is not None:
        return (direct.provider, direct.model, key)

    # Reverse lookup: match by model ID so full names (e.g. "kimi-k2.5",
    # "glm-4.7") route through direct aliases instead of falling through
    # to the catalog/OpenRouter.
    for alias_name, da in DIRECT_ALIASES.items():
        if da.model.lower() == key:
            return (da.provider, da.model, alias_name)

    identity = MODEL_ALIASES.get(key)
    if identity is None:
        return None

    vendor, family = identity

    # Build catalog from models.dev, then merge in static _PROVIDER_MODELS
    # entries that models.dev may be missing (e.g. newly added models not
    # yet synced to the registry).
    catalog = list_provider_models(current_provider)
    try:
        from shay_cli.models import _PROVIDER_MODELS
        static = _PROVIDER_MODELS.get(current_provider, [])
        if static:
            seen = {m.lower() for m in catalog}
            for m in static:
                if m.lower() not in seen:
                    catalog.append(m)
    except Exception:
        pass

    matches: list[str] = []

    if is_aggregator(current_provider):
        # OpenRouter / etc: look for 'vendor/family' (e.g. 'anthropic/claude-sonnet')
        prefix = f"{vendor}/{family}"
        for m in catalog:
            if m.lower().startswith(prefix):
                matches.append(m)
    else:
        # Direct provider: just match 'family' (e.g. 'claude-sonnet')
        # Only check if vendor matches or if current_provider is custom
        if vendor == current_provider or current_provider == "custom":
            for m in catalog:
                if m.lower().startswith(family):
                    matches.append(m)

    if not matches:
        return None

    # Sort matches by version (descending) and return the best one
    matches.sort(key=lambda m: _model_sort_key(m.lower(), family))
    best_match = matches[0]

    return (current_provider, best_match, key)


def apply_variant_suffix(model_name: str, suffix: str) -> str:
    """Apply an OpenRouter variant suffix (``:free``, ``:extended``, ``:fast``).

    Safely handles models that already have a suffix, or non-OpenRouter models
    (where the suffix is stripped/ignored to prevent validation errors).
    """
    if not model_name or not suffix:
        return model_name

    clean_suffix = suffix.strip().lower().lstrip(":")

    # Suffixes are only valid for OpenRouter
    # (If we knew the provider here we could check is_aggregator, but we only
    # have the model ID. We rely on the caller or subsequent normalization to
    # clean this up if the provider ends up being non-OpenRouter).
    if not model_name.startswith(tuple(["openrouter/", "anthropic/", "openai/", "google/", "meta-llama/", "mistralai/"])):
         # If it's not a recognized vendor prefix, it might be a direct provider
         # model where colons are invalid.  Return as-is.
         pass

    # Remove any existing suffix
    base_model = model_name.split(":")[0]
    return f"{base_model}:{clean_suffix}"


# ---------------------------------------------------------------------------
# Core model-switching pipeline
# ---------------------------------------------------------------------------

def switch_model(
    raw_input: str,
    current_provider: str,
    current_model: str,
    current_base_url: str = "",
    current_api_key: str = "",
    is_global: bool = False,
    explicit_provider: str = "",
    user_providers: dict = None,
    custom_providers: list | None = None,
) -> ModelSwitchResult:
    """Core model-switching pipeline shared between CLI and gateway.

    Resolution chain:

      If --provider given:
        a. Resolve provider via resolve_provider_full()
        b. Resolve credentials
        c. If model given, resolve alias on target provider or use as-is
        d. If no model, auto-detect from endpoint

      If no --provider:
        a. Try alias resolution on current provider
        b. If alias exists but not on current provider -> fallback
        c. On aggregator, try vendor/model slug conversion
        d. Aggregator catalog search
        e. detect_provider_for_model() as last resort
        f. Resolve credentials
        g. Normalize model name for target provider

      Finally:
        h. Get full model metadata from models.dev
        i. Build result

    Args:
        raw_input: The model name (after flag parsing).
        current_provider: The currently active provider.
        current_model: The currently active model name.
        current_base_url: The currently active base URL.
        current_api_key: The currently active API key.
        is_global: Whether to persist the switch.
        explicit_provider: From --provider flag (empty = no explicit provider).
        user_providers: The ``providers:`` dict from config.yaml (for user endpoints).
        custom_providers: The ``custom_providers:`` list from config.yaml.

    Returns:
        ModelSwitchResult with all information the caller needs.
    """
    from shay_cli.models import (
        copilot_model_api_mode,
        detect_provider_for_model,
        validate_requested_model,
        opencode_model_api_mode,
    )
    from shay_cli.runtime_provider import resolve_runtime_provider

    resolved_alias = ""
    new_model = raw_input.strip()
    target_provider = current_provider

    # =================================================================
    # PATH A: Explicit --provider given
    # =================================================================
    if explicit_provider:
        # Resolve the provider
        pdef = resolve_provider_full(
            explicit_provider,
            user_providers,
            custom_providers,
        )
        if pdef is None:
            _switch_err = (
                f"Unknown provider '{explicit_provider}'. "
                f"Check 'shay model' for available providers, or define it "
                f"in config.yaml under 'providers:'."
            )
            # Check for common config issues that cause provider resolution failures
            try:
                from shay_cli.config import validate_config_structure
                _cfg_issues = validate_config_structure()
                if _cfg_issues:
                    _switch_err += "\n\nRun 'shay doctor' — config issues detected:"
                    for _ci in _cfg_issues[:3]:
                        _switch_err += f"\n  • {_ci.message}"
            except Exception:
                pass
            return ModelSwitchResult(success=False, error_message=_switch_err)
        target_provider = pdef.slug

        # Resolve credentials for the target provider
        runtime = resolve_runtime_provider(
            target_provider, user_providers=user_providers,
            custom_providers=custom_providers,
            api_key_env_var=pdef.api_key_env_var,
        )
        api_key = runtime.get("api_key", "")
        base_url = runtime.get("base_url", "")

        # Auto-detect model if none given (for custom endpoints)
        if not new_model:
            if base_url:
                try:
                    from shay_cli.models import fetch_api_models
                    live = fetch_api_models(api_key, base_url, timeout=3)
                    if live:
                        new_model = live[0]
                    else:
                        return ModelSwitchResult(
                            success=False,
                            error_message=f"No model specified, and could not auto-detect from {base_url}. "
                                          f"Please provide a model name.",
                        )
                except Exception as e:
                    return ModelSwitchResult(
                        success=False,
                        error_message=f"Failed to auto-detect model from {base_url}: {e}",
                    )
            else:
                # No model and no endpoint — need more info
                return ModelSwitchResult(
                    success=False,
                    error_message=f"No model specified for provider '{target_provider}'. "
                                  f"Please provide a model name.",
                )

        # Resolve alias on the TARGET provider
        alias_result = resolve_alias(new_model, target_provider)
        if alias_result is not None:
            _, new_model, resolved_alias = alias_result

    # =================================================================
    # PATH B: No explicit provider — resolve from model input
    # =================================================================
    else:
        # --- Step a: Try alias resolution on current provider ---
        alias_result = resolve_alias(raw_input, current_provider)

        if alias_result is not None:
            target_provider, new_model, resolved_alias = alias_result
            logger.debug(
                "Alias '%s' resolved to '%s' on provider '%s'",
                raw_input, new_model, target_provider
            )
        else:
            # --- Step c: On aggregator, try vendor/model slug conversion ---
            if is_aggregator(current_provider) and "/" in raw_input:
                new_model = raw_input
            else:
                # --- Step e: detect_provider_for_model() as last resort ---
                maybe_provider = detect_provider_for_model(raw_input, user_providers)
                if maybe_provider and maybe_provider != current_provider:
                    target_provider = maybe_provider
                    logger.debug(
                        "Model '%s' not found on '%s', trying provider '%s'",
                        raw_input, current_provider, target_provider,
                    )
                else:
                    new_model = raw_input

        # Resolve credentials for the target provider
        pdef = resolve_provider_full(target_provider, user_providers, custom_providers)
        runtime = resolve_runtime_provider(
            target_provider, user_providers=user_providers,
            custom_providers=custom_providers,
            api_key_env_var=pdef.api_key_env_var if pdef else None,
        )
        api_key = runtime.get("api_key", "")
        base_url = runtime.get("base_url", "")

    # =================================================================
    # Final normalization and metadata lookup
    # =================================================================

    # --- Step g: Normalize model name for target provider ---
    final_model = normalize_model_for_provider(new_model, target_provider)

    # --- Step h: Get full model metadata from models.dev ---
    model_info = get_model_info(final_model, target_provider)
    capabilities = get_model_capabilities(final_model, target_provider)

    # Resolve API mode
    api_mode = determine_api_mode(final_model, target_provider, base_url)
    if not api_mode:
        if target_provider == "openai-codex":
            api_mode = opencode_model_api_mode(final_model)
        elif target_provider == "copilot" or target_provider == "copilot-acp":
            api_mode = copilot_model_api_mode(final_model)

    # Validate the final requested model against the provider's known models.
    # This catches cases where an alias resolves correctly, but the user is
    # trying to call a model their account/key can't access (e.g. a free-tier
    # key trying to call a paid model).
    # Skip for custom endpoints (base_url given) since we don't know what they serve.
    if not base_url:
        validation_error = validate_requested_model(
            final_model, target_provider, api_key=api_key,
        )
        if validation_error:
            return ModelSwitchResult(success=False, error_message=validation_error)

    # Non-agentic model warning
    warning = _check_shay_model_warning(final_model)

    # --- Step i: Build result ---
    return ModelSwitchResult(
        success=True,
        new_model=final_model,
        target_provider=target_provider,
        provider_changed=(target_provider != current_provider),
        api_key=api_key,
        base_url=base_url,
        api_mode=api_mode,
        warning_message=warning,
        provider_label=get_label(target_provider),
        resolved_via_alias=resolved_alias,
        capabilities=capabilities,
        model_info=model_info,
        is_global=is_global,
    )


def get_context_length(
    model_info: ModelInfo | None,
    capabilities: ModelCapabilities | None,
    config_context_length: int | None = None,
) -> int | None:
    """Return the effective context length, preferring live data over config."""
    try:
        from shay_cli.models import get_live_context_window
        ctx = get_live_context_window(
            model_info=model_info,
            capabilities=capabilities,
            config_context_length=config_context_length,
        )
        if ctx:
            return int(ctx)
    except Exception:
        pass
    if model_info is not None and model_info.context_window:
        return int(model_info.context_window)
    return None


# ---------------------------------------------------------------------------
# Core model-switching pipeline
# ---------------------------------------------------------------------------

def switch_model(
    raw_input: str,
    current_provider: str,
    current_model: str,
    current_base_url: str = "",
    current_api_key: str = "",
    is_global: bool = False,
    explicit_provider: str = "",
    user_providers: dict = None,
    custom_providers: list | None = None,
) -> ModelSwitchResult:
    """Core model-switching pipeline shared between CLI and gateway.

    Resolution chain:

      If --provider given:
        a. Resolve provider via resolve_provider_full()
        b. Resolve credentials
        c. If model given, resolve alias on target provider or use as-is
        d. If no model, auto-detect from endpoint

      If no --provider:
        a. Try alias resolution on current provider
        b. If alias exists but not on current provider -> fallback
        c. On aggregator, try vendor/model slug conversion
        d. Aggregator catalog search
        e. detect_provider_for_model() as last resort
        f. Resolve credentials
        g. Normalize model name for target provider

      Finally:
        h. Get full model metadata from models.dev
        i. Build result

    Args:
        raw_input: The model name (after flag parsing).
        current_provider: The currently active provider.
        current_model: The currently active model name.
        current_base_url: The currently active base URL.
        current_api_key: The currently active API key.
        is_global: Whether to persist the switch.
        explicit_provider: From --provider flag (empty = no explicit provider).
        user_providers: The ``providers:`` dict from config.yaml (for user endpoints).
        custom_providers: The ``custom_providers:`` list from config.yaml.

    Returns:
        ModelSwitchResult with all information the caller needs.
    """
    from shay_cli.models import (
        copilot_model_api_mode,
        detect_provider_for_model,
        validate_requested_model,
        opencode_model_api_mode,
    )
    from shay_cli.runtime_provider import resolve_runtime_provider

    resolved_alias = ""
    new_model = raw_input.strip()
    target_provider = current_provider

    # =================================================================
    # PATH A: Explicit --provider given
    # =================================================================
    if explicit_provider:
        # Resolve the provider
        pdef = resolve_provider_full(
            explicit_provider,
            user_providers,
            custom_providers,
        )
        if pdef is None:
            _switch_err = (
                f"Unknown provider '{explicit_provider}'. "
                f"Check 'shay model' for available providers, or define it "
                f"in config.yaml under 'providers:'."
            )
            # Check for common config issues that cause provider resolution failures
            try:
                from shay_cli.config import validate_config_structure
                _cfg_issues = validate_config_structure()
                if _cfg_issues:
                    _switch_err += "\n\nRun 'shay doctor' — config issues detected:"
                    for _ci in _cfg_issues[:3]:
                        _switch_err += f"\n  • {_ci.message}"
            except Exception:
                pass
            return ModelSwitchResult(success=False, error_message=_switch_err)
        target_provider = pdef.slug

        # Resolve credentials for the target provider
        runtime = resolve_runtime_provider(
            target_provider, user_providers=user_providers,
            custom_providers=custom_providers,
            api_key_env_var=pdef.api_key_env_var,
        )
        api_key = runtime.get("api_key", "")
        base_url = runtime.get("base_url", "")

        # Auto-detect model if none given (for custom endpoints)
        if not new_model:
            if base_url:
                try:
                    from shay_cli.models import fetch_api_models
                    live = fetch_api_models(api_key, base_url, timeout=3)
                    if live:
                        new_model = live[0]
                    else:
                        return ModelSwitchResult(
                            success=False,
                            error_message=f"No model specified, and could not auto-detect from {base_url}. "
                                          f"Please provide a model name.",
                        )
                except Exception as e:
                    return ModelSwitchResult(
                        success=False,
                        error_message=f"Failed to auto-detect model from {base_url}: {e}",
                    )
            else:
                # No model and no endpoint — need more info
                return ModelSwitchResult(
                    success=False,
                    error_message=f"No model specified for provider '{target_provider}'. "
                                  f"Please provide a model name.",
                )

        # Resolve alias on the TARGET provider
        alias_result = resolve_alias(new_model, target_provider)
        if alias_result is not None:
            _, new_model, resolved_alias = alias_result

    # =================================================================
    # PATH B: No explicit provider — resolve from model input
    # =================================================================
    else:
        # --- Step a: Try alias resolution on current provider ---
        alias_result = resolve_alias(raw_input, current_provider)

        if alias_result is not None:
            target_provider, new_model, resolved_alias = alias_result
            logger.debug(
                "Alias '%s' resolved to '%s' on provider '%s'",
                raw_input, new_model, target_provider
            )
        else:
            # --- Step c: On aggregator, try vendor/model slug conversion ---
            if is_aggregator(current_provider) and "/" in raw_input:
                new_model = raw_input
            else:
                # --- Step e: detect_provider_for_model() as last resort ---
                maybe_provider = detect_provider_for_model(raw_input, user_providers)
                if maybe_provider and maybe_provider != current_provider:
                    target_provider = maybe_provider
                    logger.debug(
                        "Model '%s' not found on '%s', trying provider '%s'",
                        raw_input, current_provider, target_provider,
                    )
                else:
                    new_model = raw_input

        # Resolve credentials for the target provider
        pdef = resolve_provider_full(target_provider, user_providers, custom_providers)
        runtime = resolve_runtime_provider(
            target_provider, user_providers=user_providers,
            custom_providers=custom_providers,
            api_key_env_var=pdef.api_key_env_var if pdef else None,
        )
        api_key = runtime.get("api_key", "")
        base_url = runtime.get("base_url", "")

    # =================================================================
    # Final normalization and metadata lookup
    # =================================================================

    # --- Step g: Normalize model name for target provider ---
    final_model = normalize_model_for_provider(new_model, target_provider)

    # --- Step h: Get full model metadata from models.dev ---
    model_info = get_model_info(final_model, target_provider)
    capabilities = get_model_capabilities(final_model, target_provider)

    # Resolve API mode
    api_mode = determine_api_mode(final_model, target_provider, base_url)
    if not api_mode:
        if target_provider == "openai-codex":
            api_mode = opencode_model_api_mode(final_model)
        elif target_provider == "copilot" or target_provider == "copilot-acp":
            api_mode = copilot_model_api_mode(final_model)

    # Validate the final requested model against the provider's known models.
    # This catches cases where an alias resolves correctly, but the user is
    # trying to call a model their account/key can't access (e.g. a free-tier
    # key trying to call a paid model).
    # Skip for custom endpoints (base_url given) since we don't know what they serve.
    if not base_url:
        validation_error = validate_requested_model(
            final_model, target_provider, api_key=api_key,
        )
        if validation_error:
            return ModelSwitchResult(success=False, error_message=validation_error)

    # Non-agentic model warning
    warning = _check_shay_model_warning(final_model)

    # --- Step i: Build result ---
    return ModelSwitchResult(
        success=True,
        new_model=final_model,
        target_provider=target_provider,
        provider_changed=(target_provider != current_provider),
        api_key=api_key,
        base_url=base_url,
        api_mode=api_mode,
        warning_message=warning,
        provider_label=get_label(target_provider),
        resolved_via_alias=resolved_alias,
        capabilities=capabilities,
        model_info=model_info,
        is_global=is_global,
    )


def get_context_length(
    model_info: ModelInfo | None,
    capabilities: ModelCapabilities | None,
    config_context_length: int | None = None,
) -> int | None:
    """Return the effective context length, preferring live data over config."""
    try:
        from shay_cli.models import get_live_context_window
        ctx = get_live_context_window(
            model_info=model_info,
            capabilities=capabilities,
            config_context_length=config_context_length,
        )
        if ctx:
            return int(ctx)
    except Exception:
        pass
    if model_info is not None and model_info.context_window:
        return int(model_info.context_window)
    return None


# ---------------------------------------------------------------------------
# Authenticated providers listing (for /model no-args display)
# ---------------------------------------------------------------------------

def list_authenticated_providers(
    current_provider: str = "",
    current_base_url: str = "",
    user_providers: dict = None,
    custom_providers: list | None = None,
    max_models: int = 8,
    current_model: str = "",
) -> List[dict]:
    """Detect which providers have credentials and list their curated models.

    Uses the curated model lists from shay_cli/models.py (OPENROUTER_MODELS,
    _PROVIDER_MODELS) — NOT the full models.dev catalog.  These are hand-picked
    agentic models that work well as agent backends.

    Returns a list of dicts, each with:
      - slug: str — the --provider value to use
      - name: str — display name
      - is_current: bool
      - is_user_defined: bool
      - models: list[str] — curated model IDs (up to max_models)
      - total_models: int — total curated count
      - source: str — "built-in", "models.dev", "user-config"

    Only includes providers that have API keys set or are user-defined endpoints.
    """
    import os
    from shay_cli.config import load_config
    from agent.models_dev import (
        PROVIDER_TO_MODELS_DEV,
        fetch_models_dev,
        get_provider_info as _mdev_pinfo,
    )
    from shay_cli.auth import PROVIDER_REGISTRY
    from shay_cli.models import (
        OPENROUTER_MODELS, _PROVIDER_MODELS,
        _MODELS_DEV_PREFERRED, _merge_with_models_dev, provider_model_ids,
        get_curated_nous_model_ids,
    )

    config = load_config()
    config_providers = set()
    
    # Add default provider from config
    model_cfg = config.get("model", {})
    if isinstance(model_cfg, dict):
        default_provider = model_cfg.get("provider")
        if default_provider:
            config_providers.add(default_provider)
        
    # Add fallback providers from config
    fallback_providers = config.get("fallback_providers", [])
    if isinstance(fallback_providers, list):
        for fp in fallback_providers:
            if isinstance(fp, dict) and fp.get("provider"):
                # For OpenAI/Anthropic etc., the provider is simple (e.g. 'anthropic')
                # For 'custom' providers, they usually just fall through to the custom handlers later
                # But we add them all so the standard detection considers them
                prov = fp.get("provider")
                # Handle cases where config has "openai-codex" but code expects "openai-codex"
                if prov:
                    config_providers.add(prov)

    results: List[dict] = []
    seen_slugs: set = set()  # lowercase-normalized to catch case variants (#9545)
    seen_mdev_ids: set = set()  # prevent duplicate entries for aliases (e.g. kimi-coding + kimi-coding-cn)
    # Effective base URLs of every built-in row we emit (normalized lower+rstrip).
    # Section 4 uses this to hide ``custom_providers`` entries that point at the
    # same endpoint as a built-in (e.g. a user-defined "my-dashscope" on
    # https://coding-intl.dashscope.aliyuncs.com/v1 collides with the built-in
    # alibaba-coding-plan row when DASHSCOPE_API_KEY is present). Fixes #16970.
    _builtin_endpoints: set = set()

    def _norm_url(url: str) -> str:
        return str(url or "").strip().rstrip("/").lower()

    def _record_builtin_endpoint(slug: str) -> None:
        """Record the effective base URL for a built-in provider row.

        Prefers the live env-override (e.g. DASHSCOPE_BASE_URL) over the
        static inference_base_url so the dedup matches what a user typing
        that URL into custom_providers would actually hit."""
        try:
            from shay_cli.auth import PROVIDER_REGISTRY as _reg
        except Exception:
            return
        pcfg = _reg.get(slug)
        if not pcfg:
            return
        url = ""
        if getattr(pcfg, "base_url_env_var", ""):
            url = os.environ.get(pcfg.base_url_env_var, "") or ""
        if not url:
            url = getattr(pcfg, "inference_base_url", "") or ""
        normed = _norm_url(url)
        if normed:
            _builtin_endpoints.add(normed)

    def _has_fast_aws_sdk_signal() -> bool:
        """Return True when explicit AWS auth config is present.

        This intentionally avoids botocore's full credential chain. Provider
        picker/model-switch discovery can run for non-Bedrock providers, and
        botocore may otherwise probe EC2 IMDS (169.254.169.254) on local
        machines before returning no credentials.
        """
        if os.environ.get("AWS_BEARER_TOKEN_BEDROCK", "").strip():
            return True
        if (
            os.environ.get("AWS_ACCESS_KEY_ID", "").strip()
            and os.environ.get("AWS_SECRET_ACCESS_KEY", "").strip()
        ):
            return True
        return any(
            os.environ.get(name, "").strip()
            for name in (
                "AWS_PROFILE",
                "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
                "AWS_CONTAINER_CREDENTIALS_FULL_URI",
                "AWS_WEB_IDENTITY_TOKEN_FILE",
            )
        )

    def _has_aws_sdk_creds_for_listing(slug: str) -> bool:
        """Credential check for AWS SDK providers in non-runtime discovery."""
        slug_norm = str(slug or "").strip().lower()
        current_norm = str(current_provider or "").strip().lower()
        if _has_fast_aws_sdk_signal():
            return True
        if slug_norm != current_norm:
            return False
        try:
            from agent.bedrock_adapter import has_aws_credentials
            return bool(has_aws_credentials())
        except Exception:
            return False

    data = fetch_models_dev()

    # Build curated model lists keyed by shay provider ID
    curated: dict[str, list[str]] = dict(_PROVIDER_MODELS)
    curated["openrouter"] = [mid for mid, _ in OPENROUTER_MODELS]
    # "nous" pulls from the remote model-catalog manifest published at
    # https://shay-shay.nousresearch.com/docs/api/model-catalog.json so
    # newly added Portal models surface in the /model picker without
    # requiring a Shay-Shay release. Falls back to the in-repo
    # _PROVIDER_MODELS["nous"] snapshot when the manifest is unreachable.
    curated["nous"] = get_curated_nous_model_ids()
    # Ollama Cloud uses dynamic discovery (no static curated list)
    if "ollama-cloud" not in curated:
        from shay_cli.models import fetch_ollama_cloud_models
        curated["ollama-cloud"] = fetch_ollama_cloud_models()
    # LM Studio has no static catalog — probe its native /api/v1/models
    # endpoint live so the picker reflects whatever the user has loaded.
    # Base URL precedence: LM_BASE_URL env var > active config's base_url
    # (when current provider is lmstudio) > 127.0.0.1 default.
    # On auth rejection or unreachable server, fall back to the caller-supplied
    # current model so the picker still shows something when offline / mis-keyed.
    if "lmstudio" not in curated and (
        os.environ.get("LM_API_KEY") or os.environ.get("LM_BASE_URL") or current_provider.strip().lower() == "lmstudio"
    ):
        from shay_cli.models import fetch_lmstudio_models
        from shay_cli.auth import AuthError
        is_current_lmstudio = current_provider.strip().lower() == "lmstudio"
        lm_base = (
            os.environ.get("LM_BASE_URL")
            or (current_base_url if is_current_lmstudio and current_base_url else None)
            or "http://127.0.0.1:1234/v1"
        )
        try:
            live = fetch_lmstudio_models(
                api_key=os.environ.get("LM_API_KEY", ""),
                base_url=lm_base,
                timeout=1.5, # Smaller timeout for picker
            )
        except AuthError:
            live = []
        if not live and is_current_lmstudio and current_model:
            live = [current_model]
        curated["lmstudio"] = live

    # --- 1. Check Shay-Shay-mapped providers ---
    for shay_id, mdev_id in PROVIDER_TO_MODELS_DEV.items():
        # Skip aliases that map to the same models.dev provider (e.g.
        # kimi-coding and kimi-coding-cn both → kimi-for-coding).
        # The first one with valid credentials wins (#10526).
        if mdev_id in seen_mdev_ids:
            continue
        pdata = data.get(mdev_id)
        if not isinstance(pdata, dict):
            continue

        # Prefer auth.py PROVIDER_REGISTRY for env var names — it's our
        # source of truth.  models.dev can have wrong mappings (e.g.
        # minimax-cn → MINIMAX_API_KEY instead of MINIMAX_CN_API_KEY).
        pconfig = PROVIDER_REGISTRY.get(shay_id)
        # Skip non-API-key auth providers here — they are handled in
        # section 2 (SHAY_OVERLAYS) with proper auth store checking.
        if pconfig and pconfig.auth_type != "api_key":
            continue
        if pconfig and pconfig.api_key_env_vars:
            env_vars = list(pconfig.api_key_env_vars)
        else:
            env_vars = pdata.get("env", [])
            if not isinstance(env_vars, list):
                continue

        # Treat as having credentials if explicitly configured in config.yaml
        has_creds = shay_id in config_providers

        # Check if any env var is set
        if not has_creds:
            has_creds = any(os.environ.get(ev) for ev in env_vars)
        if not has_creds:
            try:
                from shay_cli.auth import _load_auth_store
                store = _load_auth_store()
                if store and shay_id in store.get("credential_pool", {}):
                    has_creds = True
            except Exception:
                pass
        if not has_creds:
            continue

        # Use curated list, falling back to models.dev if no curated list.
        # For preferred providers, merge models.dev entries into the curated
        # catalog so newly released models (e.g. mimo-v2.5-pro on opencode-go)
        # show up in the picker without requiring a Shay-Shay release.
        model_ids = curated.get(shay_id, [])
        if shay_id in _MODELS_DEV_PREFERRED:
            model_ids = _merge_with_models_dev(shay_id, model_ids)
        total = len(model_ids)
        top = model_ids[:max_models]

        slug = shay_id
        pinfo = _mdev_pinfo(mdev_id)
        display_name = pinfo.name if pinfo else mdev_id

        results.append({
            "slug": slug,
            "name": display_name,
            "is_current": slug == current_provider or mdev_id == current_provider,
            "is_user_defined": False,
            "models": top,
            "total_models": total,
            "source": "built-in",
        })
        seen_slugs.add(slug.lower())
        seen_mdev_ids.add(mdev_id)
        _record_builtin_endpoint(slug)

    # --- 2. Check Shay-Shay-only providers (nous, openai-codex, copilot, opencode-go) ---
    from shay_cli.providers import SHAY_OVERLAYS
    from shay_cli.auth import PROVIDER_REGISTRY as _auth_registry

    # Build reverse mapping: models.dev ID → Shay-Shay provider ID.
    # SHAY_OVERLAYS keys may be models.dev IDs (e.g. "github-copilot")
    # while _PROVIDER_MODELS and config.yaml use Shay-Shay IDs ("copilot").
    _mdev_to_shay = {v: k for k, v in PROVIDER_TO_MODELS_DEV.items()}

    for pid, overlay in SHAY_OVERLAYS.items():
        if pid.lower() in seen_slugs:
            continue

        # Resolve Shay-Shay slug — e.g. "github-copilot" → "copilot"
        shay_slug = _mdev_to_shay.get(pid, pid)
        if shay_slug.lower() in seen_slugs:
            continue

        # Check if credentials exist
        has_creds = shay_slug in config_providers or pid in config_providers
        
        if overlay.auth_type == "aws_sdk":
            if not has_creds:
                has_creds = _has_aws_sdk_creds_for_listing(shay_slug)
        elif overlay.extra_env_vars:
            has_creds = any(os.environ.get(ev) for ev in overlay.extra_env_vars)
        # Also check api_key_env_vars from PROVIDER_REGISTRY for api_key auth_type
        if not has_creds and overlay.auth_type == "api_key":
            for _key in (pid, shay_slug):
                pcfg = _auth_registry.get(_key)
                if pcfg and pcfg.api_key_env_vars:
                    if any(os.environ.get(ev) for ev in pcfg.api_key_env_vars):
                        has_creds = True
                        break
        # Check auth store and credential pool for non-env-var credentials.
        # This applies to OAuth providers AND api_key providers that also
        # support OAuth (e.g. anthropic supports both API key and Claude Code
        # OAuth via external credential files).
        if not has_creds:
            try:
                from shay_cli.auth import _load_auth_store
                store = _load_auth_store()
                providers_store = store.get("providers", {})
                if store and (pid in providers_store or shay_slug in providers_store):
                    has_creds = True
            except Exception as exc:
                logger.debug("Auth store check failed for %s: %s", pid, exc)
        # Fallback: check the credential pool with full auto-seeding.
        # This catches credentials that exist in external stores (e.g.
        # Codex CLI ~/.codex/auth.json) which _seed_from_singletons()
        # imports on demand but aren't in the raw auth.json yet.
        if not has_creds:
            try:
                from agent.credential_pool import load_pool
                pool = load_pool(shay_slug)
                if pool.has_credentials():
                    has_creds = True
            except Exception as exc:
                logger.debug("Credential pool check failed for %s: %s", shay_slug, exc)
        # Fallback: check external credential files directly.
        # The credential pool gates anthropic behind
        # is_provider_explicitly_configured() to prevent auxiliary tasks
        # from silently consuming Claude Code tokens (PR #4210).
        # But the /model picker is discovery-oriented — we WANT to show
        # providers the user can switch to, even if they aren't currently
        # configured.
        if not has_creds and shay_slug == "anthropic":
            try:
                from agent.anthropic_adapter import (
                    read_claude_code_credentials,
                    read_shay_oauth_credentials,
                )
                shay_creds = read_shay_oauth_credentials()
                cc_creds = read_claude_code_credentials()
                if (shay_creds and shay_creds.get("accessToken")) or \
                   (cc_creds and cc_creds.get("accessToken")):
                    has_creds = True
            except Exception as exc:
                logger.debug("Anthropic external creds check failed: %s", exc)
        if not has_creds:
            continue

        if shay_slug in {"openai-codex", "copilot", "copilot-acp"}:
            # Use live OAuth-backed discovery so the gateway /model picker
            # matches what the user's authenticated Codex/Copilot backend
            # actually serves — including ChatGPT-Pro-only Codex slugs
            # (e.g. gpt-5.3-codex-spark) that aren't in the static curated
            # catalog. ``provider_model_ids()`` falls back to the curated
            # list when the live endpoint is unreachable, so this is safe
            # for unauthenticated and offline cases too.
            model_ids = provider_model_ids(shay_slug)
        # For aws_sdk providers (bedrock), use live discovery so the list
        # reflects the active region (eu.*, us.*, ap.*) not the hardcoded us.* static list.
        elif overlay.auth_type == "aws_sdk":
            try:
                from agent.bedrock_adapter import bedrock_model_ids_or_none
                _ids = bedrock_model_ids_or_none()
                model_ids = _ids if _ids is not None else (curated.get(shay_slug, []) or curated.get(pid, []))
            except Exception:
                model_ids = curated.get(shay_slug, []) or curated.get(pid, [])
        else:
            # Use curated list — look up by Shay-Shay slug, fall back to overlay key
            model_ids = curated.get(shay_slug, []) or curated.get(pid, [])
            # Merge with models.dev for preferred providers (same rationale as above).
            if shay_slug in _MODELS_DEV_PREFERRED:
                model_ids = _merge_with_models_dev(shay_slug, model_ids)
        total = len(model_ids)
        top = model_ids[:max_models]

        results.append({
            "slug": shay_slug,
            "name": get_label(shay_slug),
            "is_current": shay_slug == current_provider or pid == current_provider,
            "is_user_defined": False,
            "models": top,
            "total_models": total,
            "source": "shay",
        })
        seen_slugs.add(pid.lower())
        seen_slugs.add(shay_slug.lower())
        _record_builtin_endpoint(shay_slug)

    # --- 2b. Cross-check canonical provider list ---
    # Catches providers that are in CANONICAL_PROVIDERS but weren't found
    # in PROVIDER_TO_MODELS_DEV or SHAY_OVERLAYS (keeps /model in sync
    # with `shay model`).
    try:
        from shay_cli.models import CANONICAL_PROVIDERS as _canon_provs
    except ImportError:
        _canon_provs = []

    for _cp in _canon_provs:
        if _cp.slug.lower() in seen_slugs:
            continue

        # Check credentials via PROVIDER_REGISTRY (auth.py)
        _cp_config = _auth_registry.get(_cp.slug)
        _cp_has_creds = False
        if _cp_config and _cp_config.api_key_env_vars:
            _cp_has_creds = any(os.environ.get(ev) for ev in _cp_config.api_key_env_vars)
        # Also check auth store and credential pool
        if not _cp_has_creds:
            try:
                from shay_cli.auth import _load_auth_store
                _cp_store = _load_auth_store()
                _cp_providers_store = _cp_store.get("providers", {})
                if _cp_store and _cp.slug in _cp_providers_store:
                    _cp_has_creds = True
            except Exception:
                pass
        if not _cp_has_creds:
            try:
                from agent.credential_pool import load_pool
                _cp_pool = load_pool(_cp.slug)
                if _cp_pool.has_credentials():
                    _cp_has_creds = True
            except Exception:
                pass

        # Special case: aws_sdk auth (bedrock) — no API key env vars,
        # credentials come from the boto3 credential chain (env vars,
        # ~/.aws/credentials, instance roles, etc.)
        if not _cp_has_creds and _cp_config and getattr(_cp_config, "auth_type", "") == "aws_sdk":
            _cp_has_creds = _has_aws_sdk_creds_for_listing(_cp.slug)

        if not _cp_has_creds:
            continue

        # For bedrock, use live discovery so the list reflects the active
        # region (eu.*, us.*, ap.*) instead of the hardcoded us.* static list.
        if _cp_config and getattr(_cp_config, "auth_type", "") == "aws_sdk":
            try:
                from agent.bedrock_adapter import bedrock_model_ids_or_none
                _ids = bedrock_model_ids_or_none()
                _cp_model_ids = _ids if _ids is not None else curated.get(_cp.slug, [])
            except Exception:
                _cp_model_ids = curated.get(_cp.slug, [])
        else:
            _cp_model_ids = curated.get(_cp.slug, [])
        _cp_total = len(_cp_model_ids)
        _cp_top = _cp_model_ids[:max_models]

        results.append({
            "slug": _cp.slug,
            "name": _cp.label,
            "is_current": _cp.slug == current_provider,
            "is_user_defined": False,
            "models": _cp_top,
            "total_models": _cp_total,
            "source": "canonical",
        })
        seen_slugs.add(_cp.slug.lower())
        _record_builtin_endpoint(_cp.slug)

    # --- 3. User-defined endpoints from config ---
    # Track (name, base_url) of what section 3 emits so section 4 can skip
    # any overlapping ``custom_providers:`` entries.  Callers typically pass
    # both (gateway/CLI invoke ``get_compatible_custom_providers()`` which
    # merges ``providers:`` into the list) — without this, the same endpoint
    # produces two picker rows: one bare-slug ("openrouter") from section 3
    # and one "custom:openrouter" from section 4, both labelled identically.
    _section3_emitted_pairs: set = set()
    if user_providers and isinstance(user_providers, dict):
        for ep_name, ep_cfg in user_providers.items():
            if not isinstance(ep_cfg, dict):
                continue
            # Skip if this slug was already emitted (e.g. canonical provider
            # with the same name) or will be picked up by section 4.
            if ep_name.lower() in seen_slugs:
                continue
            display_name = ep_cfg.get("name", "") or ep_name
            # ``base_url`` is Shay-Shay's canonical write key (matches
            # custom_providers and _save_custom_provider); ``api`` / ``url``
            # remain as fallbacks for hand-edited / legacy configs.
            api_url = (
                ep_cfg.get("base_url", "")
                or ep_cfg.get("api", "")
                or ep_cfg.get("url", "")
                or ""
            )
            # ``default_model`` is the legacy key; ``model`` matches what
            # custom_providers entries use, so accept either.
            default_model = ep_cfg.get("default_model", "") or ep_cfg.get("model", "")

            # Build models list from both default_model and full models array
            models_list = []
            if default_model:
                models_list.append(default_model)
            # Also include the full models list from config.
            # Shay-Shay writes ``models:`` as a dict keyed by model id
            # (see shay_cli/main.py::_save_custom_provider); older
            # configs or hand-edited files may still use a list.
            cfg_models = ep_cfg.get("models", [])
            if isinstance(cfg_models, dict):
                for m in cfg_models:
                    if m and m not in models_list:
                        models_list.append(m)
            elif isinstance(cfg_models, list):
                for m in cfg_models:
                    if m and m not in models_list:
                        models_list.append(m)

            # Official OpenAI API rows in providers: often have base_url but no
            # explicit models: dict — avoid a misleading zero count in /model.
            if not models_list:
                url_lower = str(api_url).strip().lower()
                if "api.openai.com" in url_lower:
                    fb = curated.get("openai") or []
                    if fb:
                        models_list = list(fb)

            # Prefer the endpoint's live /models list when credentials are
            # available, unless the provider explicitly opts out via
            # discover_models: false (e.g. dedicated endpoints that expose
            # the entire aggregator catalog via /models).
            api_key = str(ep_cfg.get("api_key", "") or "").strip()
            if not api_key:
                key_env = str(ep_cfg.get("key_env", "") or "").strip()
                api_key = os.environ.get(key_env, "").strip() if key_env else ""
            discover = ep_cfg.get("discover_models", True)
            if isinstance(discover, str):
                discover = discover.lower() not in {"false", "no", "0"}
            if api_url and api_key and discover:
                try:
                    from shay_cli.models import fetch_api_models
                    live_models = fetch_api_models(api_key, api_url)
                    if live_models:
                        models_list = live_models
                except Exception:
                    pass

            results.append({
                "slug": ep_name,
                "name": display_name,
                "is_current": ep_name == current_provider,
                "is_user_defined": True,
                "models": models_list[:max_models],
                "total_models": len(models_list),
                "source": "user-config",
                "api_url": api_url,
            })
            _section3_emitted_pairs.add((ep_name, _norm_url(api_url)))

    # --- 4. User-defined endpoints from custom_providers array ---
    # Merge endpoints specified via the flat ``custom_providers`` list (often
    # sourced from CLI env or gateway platforms with list-based configurations).
    if custom_providers and isinstance(custom_providers, list):
        for cp in custom_providers:
            if not isinstance(cp, dict):
                continue
            ep_name = str(cp.get("name", "")).strip()
            if not ep_name:
                continue

            slug = f"custom:{ep_name}"
            # Check for name/url collision with a section 3 emission
            api_url = str(cp.get("base_url", "")).strip()
            normed_url = _norm_url(api_url)

            # Dedup 1: Same name and URL as a section 3 emission
            if (ep_name, normed_url) in _section3_emitted_pairs:
                continue
            # Dedup 2: Same URL as a built-in provider that we already emitted.
            # E.g. ALIBABA_API_KEY is set (so section 1 emitted alibaba-coding-plan
            # pointing to dashscope.aliyuncs.com) AND the user has a custom_providers
            # entry pointing to that exact same URL. We drop the custom one to avoid
            # duplicate rows in the picker.
            if normed_url and normed_url in _builtin_endpoints:
                continue

            # Build models list
            models_list = []
            if cp.get("model"):
                models_list.append(str(cp["model"]))

            # Like section 3, prefer live /models discovery if possible
            api_key = str(cp.get("api_key", "")).strip()
            discover = cp.get("discover_models", True)
            if isinstance(discover, str):
                discover = discover.lower() not in {"false", "no", "0"}
            if api_url and api_key and discover:
                try:
                    from shay_cli.models import fetch_api_models
                    live_models = fetch_api_models(api_key, api_url)
                    if live_models:
                        models_list = live_models
                except Exception:
                    pass

            results.append({
                "slug": slug,
                "name": ep_name,
                "is_current": slug == current_provider or ep_name == current_provider,
                "is_user_defined": True,
                "models": models_list[:max_models],
                "total_models": len(models_list),
                "source": "custom_providers",
                "api_url": api_url,
            })

    # Sort results for display:
    # 1. Built-in (curated)
    # 2. User-defined endpoints
    # 3. Canonical providers without explicit mappings
    def _sort_key(r: dict) -> tuple:
        src = r.get("source", "")
        # Priorities: shay/built-in > user-config > custom_providers > models.dev
        if src in ("shay", "built-in"):
            rank = 0
        elif src == "user-config":
            rank = 1
        elif src == "custom_providers":
            rank = 2
        else:
            rank = 3
        return (rank, r.get("name", "").lower())

    results.sort(key=_sort_key)
    return results


def get_interactive_picker_providers(
    current_provider: str = "",
    current_base_url: str = "",
    user_providers: dict = None,
    custom_providers: list | None = None,
    max_models: int = 8,
    current_model: str = "",
) -> List[dict]:
    """Interactive-picker variant of :func:`list_authenticated_providers`.

    Used by the inline keyboard picker in the gateway and the arrow-key menu
    in the CLI.

    Filters and post-processes the base list so the ``/model`` picker (Telegram/Discord
    inline keyboards) only surfaces models that are actually callable in the
    current install:

    - OpenRouter's model list is replaced with the output of
      :func:`shay_cli.models.fetch_openrouter_models`, which filters the
      curated ``OPENROUTER_MODELS`` snapshot against the live OpenRouter
      catalog.  IDs the live catalog no longer carries drop out, so the
      picker never offers a model the user can't call.
    - Provider rows whose model list ends up empty are dropped, except
      custom endpoints (``is_user_defined=True`` with an ``api_url``) where
      the user may supply their own model set through config.

    All other providers and metadata fields are passed through unchanged.
    The typed ``/model <name>`` path is unaffected -- only the interactive
    picker payload is narrowed.
    """
    from shay_cli.models import fetch_openrouter_models

    providers = list_authenticated_providers(
        current_provider=current_provider,
        current_base_url=current_base_url,
        user_providers=user_providers,
        custom_providers=custom_providers,
        max_models=max_models,
        current_model=current_model,
    )

    filtered: List[dict] = []
    for p in providers:
        slug = str(p.get("slug", "")).lower()
        if slug == "openrouter":
            try:
                live = fetch_openrouter_models()
                live_ids = [mid for mid, _ in live]
            except Exception:
                live_ids = list(p.get("models", []))
            p = dict(p)
            p["models"] = live_ids[:max_models]
            p["total_models"] = len(live_ids)

        has_models = bool(p.get("models"))
        is_custom_endpoint = bool(p.get("is_user_defined")) and bool(p.get("api_url"))
        if not has_models and not is_custom_endpoint:
            continue
        filtered.append(p)

    return filtered
