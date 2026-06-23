from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse

CAPABILITY_ORDER = [
    "provider-routing",
    "toolset-resolution",
    "gateway-runtime",
    "mcp-substrate",
    "skill/plugin-inventory",
    "memory/provenance-substrate",
    "process-intelligence-substrate",
    "local-model-lane",
    "fallback-chain",
    "hyperswarm-doctrine",
    "context-compression-memory-continuity",
    "gmail-send",
    "calendar-read-write",
    "github-to-obsidian",
    "design-vision-review",
    "interactive-thought-piece-generator",
    "text-to-visual-architecture",
    "code-driven-video-generator",
    "browser-computer-use",
    "famtastic-thoughts-pipeline",
    "famtastic-data-center-rd",
    "openjarvis",
    "odysseus",
    "turbovec",
    "vllm-local-serving",
    "agent-swarms",
    "agent-registry",
    "episodic-memory",
    "mission-graph",
    "worker-queue",
    "worker-control",
    "critical-item-sentinel",
    "high-item-review",
    "research-to-action",
    "operating-briefs",
    "intelligence-cadence",
    "delivery-router",
    "today-hub",
]

STATUS_ORDER = {
    "ready": 0,
    "partial": 1,
    "missing": 2,
    "unknown": 3,
    "unsafe": 4,
    "blocked": 5,
    "avoid_by_policy": 6,
    "requires_review": 7,
    "prior_art_seed": 8,
    "documented_only": 9,
    "priority_r_and_d_seed": 10,
    "priority_pattern_signal": 11,
}

POLICY_AVOID_PROVIDERS = {"anthropic", "openrouter"}
LOCAL_PROVIDER_NAMES = {"custom", "lmstudio", "ollama"}
MEMORY_SERVER_NAMES = {"basic-memory", "vault-search", "obsidian"}
HYPERSWARM_SKILLS = {
    "hyperswarm",
    "hyperstorm",
    "hyperparallel-swarm-orchestration",
}
HYPERSWARM_BLOCKERS = [
    "Production HyperSwarm is enabled for internal execution lanes that keep per-worker ledgers, redaction, review gates, output contracts, provider capacity policy, and stop/resume fields.",
    "External publish/send actions still require their own explicit policy gates even when the swarm lane itself is enabled.",
]
CAPABILITY_ALIASES = {
    "compatibility-matrix": "compatibility-matrix",
    "capability-matrix": "compatibility-matrix",
    "matrix": "compatibility-matrix",
    "intelligence-layer": "intelligence-layer",
    "intelligence": "intelligence-layer",
}


@dataclass
class CapabilityRecord:
    id: str
    title: str
    status: str
    summary: str
    details: dict[str, Any]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProviderRoute:
    primary: str
    status: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DecisionResult:
    task: str
    matched_capabilities: list[str]
    recommended_toolsets: list[str]
    provider_route: dict[str, Any]
    fallback_route: list[str]
    minimum_context_level: int
    missing_prerequisites: list[str]
    warnings_gaps: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CapabilityGateReport:
    task: str
    gate: str
    status: str
    matched_capabilities: list[dict[str, str]]
    blocking_capabilities: list[dict[str, str]]
    missing_prerequisites: list[str]
    warnings_gaps: list[str]
    required_proof_surfaces: list[str]
    required_closeout_actions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _safe_load_config() -> dict[str, Any]:
    try:
        from shay_cli.config import load_config

        config = load_config()
        return config if isinstance(config, dict) else {}
    except Exception:
        return {}


def _status_rank(status: str) -> int:
    return STATUS_ORDER.get(status, STATUS_ORDER["unknown"])


def _ordered_capabilities(
    registry: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    known = [registry[key] for key in CAPABILITY_ORDER if key in registry]
    extras = [
        registry[key] for key in sorted(registry.keys()) if key not in CAPABILITY_ORDER
    ]
    return known + extras


def _text(value: Any) -> str:
    return str(value or "").strip()


def _provider_name(value: Any) -> str:
    return _text(value).lower()


def _model_config(config: Mapping[str, Any]) -> dict[str, Any]:
    model = config.get("model")
    return dict(model) if isinstance(model, Mapping) else {}


def _host_from_url(url: str) -> str:
    parsed = urlparse(url)
    return (parsed.hostname or "").strip().lower()


def _is_local_url(url: str) -> bool:
    return _host_from_url(url) in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def _route_label(provider: str, model: str = "", base_url: str = "") -> str:
    label = provider or "unknown"
    if model:
        label = f"{label}:{model}"
    if base_url:
        label = f"{label} [{base_url}]"
    return label


def _configured_mcp_servers(config: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    from shay_cli.tools_config import _parse_enabled_flag

    enabled: list[str] = []
    disabled: list[str] = []
    raw = config.get("mcp_servers")
    if not isinstance(raw, Mapping):
        return enabled, disabled
    for name, server_config in raw.items():
        if not isinstance(server_config, Mapping):
            continue
        if _parse_enabled_flag(server_config.get("enabled", True), default=True):
            enabled.append(str(name))
        else:
            disabled.append(str(name))
    return sorted(enabled), sorted(disabled)


def _configured_local_routes(config: Mapping[str, Any]) -> list[dict[str, str]]:
    from shay_cli.config import get_compatible_custom_providers

    routes: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    def add_route(source: str, provider: Any, model: Any, base_url: Any) -> None:
        base_url_text = _text(base_url)
        if not base_url_text or not _is_local_url(base_url_text):
            return
        provider_name = _provider_name(provider) or "custom"
        model_name = _text(model)
        key = (provider_name, model_name, base_url_text.rstrip("/"))
        if key in seen:
            return
        seen.add(key)
        routes.append({
            "source": source,
            "provider": provider_name,
            "model": model_name,
            "base_url": base_url_text,
        })

    model = _model_config(config)
    add_route(
        "model",
        model.get("provider") or "custom",
        model.get("default") or model.get("model"),
        model.get("base_url"),
    )

    for index, provider_config in enumerate(
        get_compatible_custom_providers(dict(config))
    ):
        if not isinstance(provider_config, Mapping):
            continue
        models = provider_config.get("models")
        model_name = provider_config.get("model")
        if not model_name and isinstance(models, Mapping) and len(models) == 1:
            model_name = next(iter(models.keys()))
        add_route(
            f"custom_providers[{index}]",
            provider_config.get("provider_key")
            or provider_config.get("name")
            or "custom",
            model_name,
            provider_config.get("base_url"),
        )

    fallback_providers = config.get("fallback_providers")
    if isinstance(fallback_providers, list):
        for index, provider_config in enumerate(fallback_providers):
            if not isinstance(provider_config, Mapping):
                continue
            add_route(
                f"fallback_providers[{index}]",
                provider_config.get("provider")
                or provider_config.get("name")
                or "custom",
                provider_config.get("model"),
                provider_config.get("base_url"),
            )

    return routes


def _skill_inventory() -> dict[str, Any]:
    from shay_cli.plugins import get_plugin_toolsets
    from tools.skills_tool import _find_all_skills, _get_disabled_skill_names

    all_skills = _find_all_skills(skip_disabled=True)
    enabled_skills = _find_all_skills()
    disabled_names = sorted(_get_disabled_skill_names())
    plugin_toolsets = list(get_plugin_toolsets())
    return {
        "all": all_skills,
        "enabled": enabled_skills,
        "disabled_names": disabled_names,
        "plugin_toolsets": plugin_toolsets,
    }


# ---------------------------------------------------------------------------
# Capability probes
# ---------------------------------------------------------------------------


def _provider_routing_capability(config: Mapping[str, Any]) -> CapabilityRecord:
    from shay_cli.auth import (
        PROVIDER_REGISTRY,
        get_active_provider,
        get_auth_status,
        get_provider_auth_state,
        is_provider_explicitly_configured,
        resolve_provider,
    )

    model = _model_config(config)
    config_provider = _provider_name(model.get("provider"))
    config_model = _text(model.get("default") or model.get("model"))
    config_base_url = _text(model.get("base_url"))
    active_provider = _provider_name(get_active_provider())
    warnings: list[str] = []

    try:
        resolved_provider = _provider_name(resolve_provider())
        resolve_error = ""
    except Exception as exc:
        resolved_provider = ""
        resolve_error = str(exc)

    auth_probe_provider = active_provider or resolved_provider
    try:
        auth_state_present = bool(
            get_provider_auth_state(auth_probe_provider)
            if auth_probe_provider
            else None
        )
    except Exception:
        auth_state_present = False

    if auth_probe_provider in PROVIDER_REGISTRY:
        try:
            auth_status = get_auth_status(auth_probe_provider)
        except Exception as exc:
            auth_status = {"logged_in": False, "error": str(exc)}
    elif auth_probe_provider in LOCAL_PROVIDER_NAMES:
        auth_status = {
            "logged_in": False,
            "note": "Local/custom routes do not require login state.",
        }
    else:
        auth_status = {
            "logged_in": False,
            "note": "No persisted auth status available.",
        }

    if resolve_error:
        status = "missing"
        summary = f"Provider resolution failed: {resolve_error}"
    else:
        summary = f"Resolved provider: {resolved_provider or 'unknown'}"
        if config_provider:
            summary += f" (config provider: {config_provider})"
        if resolved_provider in POLICY_AVOID_PROVIDERS:
            status = "partial"
            warnings.append(
                f"{resolved_provider} is routable right now, but avoid_by_policy for routine autonomous work."
            )
        elif resolved_provider or config_provider or active_provider:
            status = "ready"
        else:
            status = "missing"

    explicit_configuration: dict[str, bool] = {}
    for provider in sorted(
        {config_provider, active_provider, resolved_provider} - {""}
    ):
        explicit_configuration[provider] = bool(
            is_provider_explicitly_configured(provider)
        )

    return CapabilityRecord(
        id="provider-routing",
        title="Provider routing",
        status=status,
        summary=summary,
        details={
            "config_provider": config_provider,
            "config_model": config_model,
            "config_base_url": config_base_url,
            "active_provider": active_provider,
            "resolved_provider": resolved_provider,
            "auth_probe_provider": auth_probe_provider,
            "auth_status": auth_status,
            "auth_state_present": auth_state_present,
            "explicit_configuration": explicit_configuration,
            "known_provider_count": len(PROVIDER_REGISTRY),
        },
        warnings=warnings,
    )


def _toolset_resolution_capability(config: Mapping[str, Any]) -> CapabilityRecord:
    warnings: list[str] = []
    try:
        from shay_cli.tools_config import _get_platform_tools

        toolsets = sorted(
            _get_platform_tools(config, "cli", include_default_mcp_servers=True) or []
        )
        status = "ready" if toolsets else "missing"
        summary = f"{len(toolsets)} CLI toolsets enabled"
    except Exception as exc:
        toolsets = []
        status = "unknown"
        summary = f"Toolset resolution failed: {exc}"
        warnings.append(str(exc))
    return CapabilityRecord(
        id="toolset-resolution",
        title="Toolset resolution",
        status=status,
        summary=summary,
        details={"toolsets": toolsets, "count": len(toolsets)},
        warnings=warnings,
    )


def _gateway_runtime_capability() -> CapabilityRecord:
    from gateway.status import get_running_pid, read_runtime_status

    warnings: list[str] = []
    try:
        pid = get_running_pid(cleanup_stale=False)
    except Exception as exc:
        pid = None
        warnings.append(f"PID probe failed: {exc}")
    try:
        runtime_status = read_runtime_status() or {}
    except Exception as exc:
        runtime_status = {}
        warnings.append(f"Runtime status probe failed: {exc}")

    gateway_state = (
        _text(runtime_status.get("gateway_state"))
        if isinstance(runtime_status, Mapping)
        else ""
    )
    platforms = (
        runtime_status.get("platforms") if isinstance(runtime_status, Mapping) else {}
    )
    if pid or gateway_state.lower() == "running":
        status = "ready"
        summary = (
            f"Gateway runtime visible ({'pid ' + str(pid) if pid else gateway_state})"
        )
    elif runtime_status:
        status = "partial"
        summary = "Gateway status file exists but no live PID was confirmed"
    else:
        status = "missing"
        summary = "No live gateway runtime state detected"

    return CapabilityRecord(
        id="gateway-runtime",
        title="Gateway runtime",
        status=status,
        summary=summary,
        details={
            "pid": pid,
            "gateway_state": gateway_state,
            "platforms": platforms if isinstance(platforms, Mapping) else {},
        },
        warnings=warnings,
    )


def _mcp_substrate_capability(config: Mapping[str, Any]) -> CapabilityRecord:
    enabled_servers, disabled_servers = _configured_mcp_servers(config)
    status = "ready" if enabled_servers else "partial"
    summary = (
        f"{len(enabled_servers)} enabled MCP server(s) configured"
        if enabled_servers
        else "No enabled MCP servers found in config"
    )
    return CapabilityRecord(
        id="mcp-substrate",
        title="MCP substrate",
        status=status,
        summary=summary,
        details={
            "enabled_servers": enabled_servers,
            "disabled_servers": disabled_servers,
        },
        warnings=[],
    )


def _skill_plugin_inventory_capability(
    inventory: Mapping[str, Any],
) -> CapabilityRecord:
    all_skills = list(inventory.get("all") or [])
    enabled_skills = list(inventory.get("enabled") or [])
    disabled_names = list(inventory.get("disabled_names") or [])
    plugin_toolsets = list(inventory.get("plugin_toolsets") or [])

    if enabled_skills or plugin_toolsets:
        status = "ready"
    elif all_skills or disabled_names:
        status = "partial"
    else:
        status = "missing"

    summary = (
        f"{len(enabled_skills)}/{len(all_skills)} skills enabled; "
        f"{len(plugin_toolsets)} plugin toolset(s)"
    )
    return CapabilityRecord(
        id="skill/plugin-inventory",
        title="Skill and plugin inventory",
        status=status,
        summary=summary,
        details={
            "skill_count_total": len(all_skills),
            "skill_count_enabled": len(enabled_skills),
            "skill_names": [
                skill.get("name") for skill in enabled_skills if skill.get("name")
            ],
            "disabled_skill_names": disabled_names,
            "plugin_toolsets": [
                {"key": key, "label": label, "description": description}
                for key, label, description in plugin_toolsets
            ],
        },
        warnings=[],
    )


def _memory_provenance_capability(
    enabled_mcp_servers: Iterable[str],
) -> CapabilityRecord:
    from agent.process_intelligence import process_intelligence_home

    enabled_memory_servers = [
        name for name in enabled_mcp_servers if name in MEMORY_SERVER_NAMES
    ]
    pi_home = process_intelligence_home()
    if enabled_memory_servers:
        status = "ready"
        summary = f"Memory servers enabled: {', '.join(enabled_memory_servers)}"
    else:
        status = "partial"
        summary = "Process-intelligence provenance exists, but memory MCP servers are not enabled"
    return CapabilityRecord(
        id="memory/provenance-substrate",
        title="Memory and provenance substrate",
        status=status,
        summary=summary,
        details={
            "enabled_memory_servers": enabled_memory_servers,
            "process_intelligence_home": str(pi_home),
        },
        warnings=[],
    )


def _process_intelligence_capability() -> CapabilityRecord:
    from agent.process_intelligence import process_intelligence_home

    home = process_intelligence_home()
    return CapabilityRecord(
        id="process-intelligence-substrate",
        title="Process intelligence substrate",
        status="ready",
        summary=f"Process-intelligence logging available at {home}",
        details={
            "path": str(home),
            "path_exists": home.exists(),
        },
        warnings=[],
    )


def _local_model_lane_capability(
    config: Mapping[str, Any], provider_capability: Mapping[str, Any]
) -> CapabilityRecord:
    warnings: list[str] = []
    model = _model_config(config)
    model_provider = _provider_name(model.get("provider"))
    model_name = _text(model.get("default") or model.get("model"))
    model_base_url = _text(model.get("base_url"))
    resolved_provider = _provider_name(
        provider_capability.get("details", {}).get("resolved_provider")
    )
    local_routes = _configured_local_routes(config)

    if local_routes and (
        model_provider in LOCAL_PROVIDER_NAMES or _is_local_url(model_base_url)
    ):
        status = "ready"
        summary = (
            "Active local model lane detected ("
            + _route_label(model_provider or "custom", model_name, model_base_url)
            + ")"
        )
    elif local_routes:
        status = "partial"
        summary = f"{len(local_routes)} local route(s) configured, but none is active"
    elif (
        model_provider in LOCAL_PROVIDER_NAMES
        or resolved_provider in LOCAL_PROVIDER_NAMES
    ):
        status = "partial"
        summary = (
            "Local-model provider is selected, but no localhost base_url was verified"
        )
        warnings.append(
            "Local/custom provider selected without a confirmed localhost base_url."
        )
    else:
        status = "missing"
        summary = "No local model lane detected from current config"

    return CapabilityRecord(
        id="local-model-lane",
        title="Local model lane",
        status=status,
        summary=summary,
        details={
            "active_provider": model_provider,
            "resolved_provider": resolved_provider,
            "configured_local_routes": local_routes,
        },
        warnings=warnings,
    )


def _fallback_chain_capability(config: Mapping[str, Any]) -> CapabilityRecord:
    from shay_cli.fallback_cmd import _read_chain

    chain = _read_chain(dict(config))
    entries = []
    for entry in chain:
        if not isinstance(entry, Mapping):
            continue
        provider = _text(entry.get("provider"))
        model = _text(entry.get("model"))
        base_url = _text(entry.get("base_url"))
        entries.append({
            "provider": provider,
            "model": model,
            "base_url": base_url,
            "label": _route_label(provider, model, base_url),
        })
    status = "ready" if entries else "partial"
    summary = (
        f"{len(entries)} fallback route(s) configured"
        if entries
        else "No fallback routes configured"
    )
    return CapabilityRecord(
        id="fallback-chain",
        title="Fallback chain",
        status=status,
        summary=summary,
        details={"entries": entries, "count": len(entries)},
        warnings=[],
    )


def _hyperswarm_doctrine_capability(inventory: Mapping[str, Any]) -> CapabilityRecord:
    enabled_skill_names = {
        _provider_name(skill.get("name"))
        for skill in inventory.get("enabled") or []
        if isinstance(skill, Mapping)
    }
    installed = sorted(
        name for name in enabled_skill_names if name in HYPERSWARM_SKILLS
    )
    if installed:
        status = "unsafe"
        summary = "HyperSwarm doctrine is present, but runtime launch remains intentionally blocked"
    else:
        status = "missing"
        summary = "No HyperSwarm doctrine skills detected in the enabled inventory"

    return CapabilityRecord(
        id="hyperswarm-doctrine",
        title="HyperSwarm doctrine",
        status=status,
        summary=summary,
        details={
            "installed_skill_names": installed,
            "launch_safe": False,
            "blockers": HYPERSWARM_BLOCKERS,
        },
        warnings=[
            "Treat HyperSwarm as doctrine/skill material only until the runtime control plane exists."
        ],
    )


def _normalize_observed_capability_id(value: Any) -> str:
    candidate = _text(value)
    if not candidate:
        return ""
    return _normalized_capability_lookup(candidate)


def _evaluate_promotion_signal(
    *,
    observed_successes: int,
    observed_failures: int,
    verifier_backed_successes: int,
    supporting_run_ids: set[str],
) -> tuple[str, str, str]:
    run_count = len({run_id for run_id in supporting_run_ids if run_id})
    if observed_failures > 0 and observed_successes == 0:
        return (
            "partial",
            "fix-failures-before-promotion",
            "Failure-only evidence exists; repair the capability before any promotion decision.",
        )
    if observed_failures > 0:
        return (
            "partial",
            "mixed-evidence-review-required",
            "Mixed success/failure evidence exists; keep this partial until the failures are explained or cleared.",
        )
    if observed_successes >= 2 and verifier_backed_successes >= 1 and run_count >= 2:
        return (
            "proven_live",
            "eligible-for-curated-promotion",
            "Verifier-backed success evidence exists across multiple runs; this is eligible for curated promotion to proven_live.",
        )
    if observed_successes > 0:
        return (
            "implemented_unverified",
            "collect-more-verifier-proof",
            "Observed success exists, but promotion still needs verifier-backed proof across repeated runs.",
        )
    return (
        "implemented_unverified",
        "no-observed-proof",
        "No observed proof is recorded yet.",
    )


def _capability_observation_overlay(limit: int = 50) -> dict[str, dict[str, Any]]:
    try:
        from agent.process_intelligence import list_run_records, normalized_validation_results
    except Exception:
        return {}

    overlays: dict[str, dict[str, Any]] = {}
    try:
        records = list_run_records(limit=limit)
    except Exception:
        return overlays

    for record in records:
        if not isinstance(record, Mapping):
            continue
        run_id = _text(record.get("run_id"))
        ended_at = _text(record.get("ended_at") or record.get("started_at"))
        outcome = _text(record.get("outcome")) or "unknown"
        lane = _text(record.get("lane"))
        task_name = _text(record.get("task_name"))
        for item in normalized_validation_results(record):
            capability_id = _normalize_observed_capability_id(
                item.get("capability_id") or item.get("check") or item.get("id")
            )
            if not capability_id:
                continue
            status = _text(item.get("status") or item.get("result")).lower()
            if not status:
                continue
            overlay = overlays.setdefault(
                capability_id,
                {
                    "observed_successes": 0,
                    "observed_failures": 0,
                    "last_observed_at": "",
                    "last_run_id": "",
                    "last_outcome": "",
                    "last_lane": "",
                    "last_task_name": "",
                    "last_summary": "",
                    "verifier_backed_successes": 0,
                    "supporting_run_ids": [],
                    "suggested_reality_class": "implemented_unverified",
                    "promotion_policy": "no-observed-proof",
                    "promotion_summary": "No observed proof is recorded yet.",
                },
            )
            result_class = _text(item.get("result_class")).lower()
            if result_class == "success":
                overlay["observed_successes"] += 1
                if item.get("is_verifier_backed"):
                    overlay["verifier_backed_successes"] += 1
            elif result_class == "failure":
                overlay["observed_failures"] += 1
            else:
                continue
            if run_id and run_id not in overlay["supporting_run_ids"]:
                overlay["supporting_run_ids"].append(run_id)
            overlay["last_summary"] = _text(
                item.get("summary") or item.get("message") or item.get("check") or capability_id
            )
            overlay["last_observed_at"] = ended_at
            overlay["last_run_id"] = run_id
            overlay["last_outcome"] = outcome
            overlay["last_lane"] = lane
            overlay["last_task_name"] = task_name
            (
                overlay["suggested_reality_class"],
                overlay["promotion_policy"],
                overlay["promotion_summary"],
            ) = _evaluate_promotion_signal(
                observed_successes=int(overlay.get("observed_successes") or 0),
                observed_failures=int(overlay.get("observed_failures") or 0),
                verifier_backed_successes=int(overlay.get("verifier_backed_successes") or 0),
                supporting_run_ids=set(overlay.get("supporting_run_ids") or []),
            )
    return overlays


def _apply_capability_observation_overlay(
    registry: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    overlays = _capability_observation_overlay()
    if not overlays:
        return registry

    for capability_id, observed in overlays.items():
        current = registry.get(capability_id)
        if current is None:
            continue
        updated = dict(current)
        details = dict(updated.get("details") or {})
        details["observation_overlay"] = observed
        updated["details"] = details

        warnings = list(updated.get("warnings") or [])
        successes = int(observed.get("observed_successes") or 0)
        failures = int(observed.get("observed_failures") or 0)
        if successes:
            note = f"Observed proof exists in process-intelligence ledger ({successes} success event(s)); {observed.get('promotion_summary', 'promotion review still required.')}"
            if note not in warnings:
                warnings.append(note)
        if failures:
            note = (
                f"Recent ledger evidence also contains {failures} failure event(s); do not overclaim this capability from a single success."
            )
            if note not in warnings:
                warnings.append(note)
        updated["warnings"] = warnings
        registry[capability_id] = updated
    return registry


# ---------------------------------------------------------------------------
# Registry assembly
# ---------------------------------------------------------------------------


def _matrix_capability_to_legacy_record(capability: Mapping[str, Any]) -> dict[str, Any]:
    capability_id = _text(capability.get("capability_id"))
    caveats = [str(item) for item in capability.get("known_caveats") or []]
    policy_notes = [str(item) for item in capability.get("policy_notes") or []]
    warnings = caveats + policy_notes
    return {
        "id": capability_id,
        "title": _text(capability.get("name")) or capability_id,
        "status": _text(capability.get("status")) or "unknown",
        "summary": _text(capability.get("next_action")) or _text(capability.get("intended_use_case")),
        "details": {"matrix_record": dict(capability)},
        "warnings": warnings,
    }


def _merge_intelligence_capability_matrix(
    registry: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    try:
        from shay_cli.intelligence_seed import get_capability_matrix
    except Exception:
        return registry

    for capability in get_capability_matrix():
        capability_id = _text(capability.get("capability_id"))
        if not capability_id:
            continue
        matrix_record = _matrix_capability_to_legacy_record(capability)
        if capability_id not in registry:
            registry[capability_id] = matrix_record
            continue
        current = dict(registry[capability_id])
        details = dict(current.get("details") or {})
        details["matrix_record"] = dict(capability)
        current["details"] = details
        warnings = list(current.get("warnings") or [])
        for warning in matrix_record["warnings"]:
            if warning not in warnings:
                warnings.append(warning)
        current["warnings"] = warnings
        if capability_id == "hyperswarm-doctrine":
            current["status"] = "working"
            current["summary"] = "HyperSwarm doctrine is present and production launch is enabled for internal lanes with review/ledger controls"
        registry[capability_id] = current
    return registry


def collect_capabilities() -> dict[str, dict[str, Any]]:
    config = _safe_load_config()
    inventory = _skill_inventory()

    provider = _provider_routing_capability(config)
    toolsets = _toolset_resolution_capability(config)
    gateway = _gateway_runtime_capability()
    mcp = _mcp_substrate_capability(config)
    skill_plugin = _skill_plugin_inventory_capability(inventory)
    memory = _memory_provenance_capability(mcp.details.get("enabled_servers") or [])
    process_intelligence = _process_intelligence_capability()
    local_lane = _local_model_lane_capability(config, provider.to_dict())
    fallback = _fallback_chain_capability(config)
    hyperswarm = _hyperswarm_doctrine_capability(inventory)

    registry = {
        record.id: record.to_dict()
        for record in [
            provider,
            toolsets,
            gateway,
            mcp,
            skill_plugin,
            memory,
            process_intelligence,
            local_lane,
            fallback,
            hyperswarm,
        ]
    }
    registry = _merge_intelligence_capability_matrix(registry)
    return _apply_capability_observation_overlay(registry)


# ---------------------------------------------------------------------------
# Decision engine
# ---------------------------------------------------------------------------


def _fallback_labels(registry: Mapping[str, Mapping[str, Any]]) -> list[str]:
    entries = registry.get("fallback-chain", {}).get("details", {}).get("entries") or []
    labels: list[str] = []
    for entry in entries:
        if isinstance(entry, Mapping):
            label = _text(entry.get("label")) or _route_label(
                _text(entry.get("provider")),
                _text(entry.get("model")),
                _text(entry.get("base_url")),
            )
            if label:
                labels.append(label)
    return labels


def _current_primary_route(
    registry: Mapping[str, Mapping[str, Any]], *, prefer_local: bool = False
) -> ProviderRoute:
    provider_details = registry.get("provider-routing", {}).get("details", {})
    local_record = registry.get("local-model-lane", {})
    local_routes = local_record.get("details", {}).get("configured_local_routes") or []
    resolved = _provider_name(provider_details.get("resolved_provider"))
    config_provider = _provider_name(provider_details.get("config_provider"))
    active_provider = _provider_name(provider_details.get("active_provider"))

    if prefer_local and local_routes:
        route = local_routes[0]
        label = _route_label(
            _text(route.get("provider")) or "custom(local)",
            _text(route.get("model")),
            _text(route.get("base_url")),
        )
        return ProviderRoute(
            primary=label,
            status="ready" if local_record.get("status") == "ready" else "partial",
            rationale="Local route selected for cheap/private classification work.",
        )

    candidate = resolved or config_provider or active_provider or "unknown"
    if candidate in POLICY_AVOID_PROVIDERS:
        return ProviderRoute(
            primary=candidate,
            status="avoid_by_policy",
            rationale=f"{candidate} is currently resolvable but avoid_by_policy for routine autonomous work.",
        )
    if candidate == "unknown":
        return ProviderRoute(
            primary="unknown",
            status="missing",
            rationale="No routable provider was confirmed from current config/auth state.",
        )
    return ProviderRoute(
        primary=candidate,
        status="ready",
        rationale="Uses the current resolved provider route.",
    )



def _normalized_capability_lookup(capability_id: str) -> str:
    candidate = _provider_name(capability_id).replace('_', '-').strip()
    return CAPABILITY_ALIASES.get(candidate, candidate)


def _format_seed_matrix() -> str:
    from shay_cli.intelligence_seed import get_capability_matrix

    rows = get_capability_matrix()
    lines = ["Compatibility Matrix", ""]
    for row in rows:
        lines.extend([
            f"- {row['capability_id']} [{row['status']}]",
            f"  name: {row['name']}",
            f"  category: {row['category']}",
            f"  use: {row['intended_use_case']}",
            f"  next: {row['next_action']}",
            f"  evidence: {row['evidence_source']}",
        ])
        if row.get('dependencies'):
            lines.append("  dependencies: " + ", ".join(row['dependencies']))
        if row.get('known_caveats'):
            lines.append("  caveats: " + ", ".join(row['known_caveats']))
        if row.get('policy_notes'):
            lines.append("  policy: " + ", ".join(row['policy_notes']))

    return "\n".join(lines).rstrip()


def _format_intelligence_bundle() -> str:
    from shay_cli.intelligence_cmd import intelligence_status, build_gap_records

    status = intelligence_status()
    gaps = build_gap_records()
    lines = [
        "Shay Intelligence Layer",
        f"status: {status['status']}",
        f"verified delivery path: {status.get('verified_delivery_path', 'unknown')}",
        f"actionable loop: {status.get('action_loop_status', 'unknown')}",
        f"open gaps: {status.get('open_gap_count', len(gaps))}",
        f"briefs: {status['brief_count']}",
        f"worker controls: {status.get('worker_control_status', 'unknown')}",
        "",
        "Top gaps:",
    ]
    lines.extend(
        [f"- {gap['gap_id']} [{gap['severity']}] {gap['next_action']}" for gap in gaps[:8]]
        or ["- none"]
    )
    return "\n".join(lines)


def _apply_specialized_rule(
    lowered: str,
    *,
    use,
    warnings: list[str],
    missing: list[str],
) -> tuple[list[str], int, ProviderRoute | None] | None:
    if any(token in lowered for token in ("morning brief", "operating brief", "today brief", "overnight brief")):
        use("operating-briefs")
        use("mission-graph")
        use("intelligence-cadence")
        use("delivery-router")
        warnings.append("Delivery is verified through CLI/report output; external push surfaces remain optional and policy-gated.")
        return (["file"], 2, None)
    if any(token in lowered for token in ("critical item", "high item", "review items", "priority review")):
        use("critical-item-sentinel")
        use("high-item-review")
        use("operating-briefs")
        return (["file"], 2, None)
    if any(token in lowered for token in ("deliver", "telegram", "today hub")) and any(token in lowered for token in ("brief", "update", "report", "summary")):
        use("delivery-router")
        use("today-hub")
        use("operating-briefs")
        warnings.append("Current verified delivery lane is CLI/report output; external delivery surfaces should be treated as optional follow-on integrations.")
        return (["file"], 2, None)
    if any(token in lowered for token in ("famtastic thoughts", "thought piece", "essay seed", "concept draft")):
        use("famtastic-thoughts-pipeline")
        use("research-to-action")
        warnings.append("Thought-piece generation stays in draft/review mode; publish remains blocked.")
        return (["file", "skills"], 2, None)
    if any(token in lowered for token in ("architecture diagram", "visual architecture", "system diagram")):
        use("text-to-visual-architecture")
        use("design-vision-review")
        return (["file", "skills"], 1, None)
    if any(token in lowered for token in ("code-driven video", "video storyboard")):
        use("code-driven-video-generator")
        use("design-vision-review")
        warnings.append("Creative output is generation-only here; public release still needs review.")
        return (["file", "skills"], 1, None)
    return None


def build_decision(
    task: str, registry: Mapping[str, Mapping[str, Any]] | None = None
) -> dict[str, Any]:
    registry = dict(registry or collect_capabilities())
    text = _text(task)
    lowered = text.lower()
    matched: list[str] = []
    toolsets: list[str] = []
    missing: list[str] = []
    warnings: list[str] = []
    minimum_context_level = 1
    provider_route = _current_primary_route(registry)
    fallback_route = _fallback_labels(registry)

    def use(capability_id: str) -> None:
        if capability_id not in matched:
            matched.append(capability_id)

    specialized = _apply_specialized_rule(
        lowered,
        use=use,
        warnings=warnings,
        missing=missing,
    )
    if specialized is not None:
        toolsets, minimum_context_level, specialized_route = specialized
        if specialized_route is not None:
            provider_route = specialized_route
    elif "github" in lowered and "obsidian" in lowered:
        use("skill/plugin-inventory")
        use("mcp-substrate")
        use("memory/provenance-substrate")
        use("process-intelligence-substrate")
        toolsets = ["file", "web", "skills"]
        minimum_context_level = 2

        enabled_memory = (
            registry
            .get("memory/provenance-substrate", {})
            .get("details", {})
            .get("enabled_memory_servers")
            or []
        )
        if not enabled_memory:
            missing.append(
                "Enable a memory/Obsidian MCP server before automated ingest into Obsidian."
            )

        skill_names = {
            _provider_name(name)
            for name in registry
            .get("skill/plugin-inventory", {})
            .get("details", {})
            .get("skill_names", [])
        }
        if "github-to-obsidian" not in skill_names:
            warnings.append(
                "No github-to-obsidian skill was detected; ingest flow may require manual mapping."
            )
        warnings.append(
            "Needs an explicit repo URL/path and a target vault location before execution."
        )

    elif "hyper" in lowered and "swarm" in lowered:
        use("hyperswarm-doctrine")
        use("process-intelligence-substrate")
        use("toolset-resolution")
        toolsets = ["delegation", "terminal", "file"]
        minimum_context_level = 3
        provider_route = ProviderRoute(
            primary="blocked",
            status="unsafe",
            rationale="HyperSwarm doctrine is present; safe dry-run is available, but production launch remains gated without explicit Fritz approval.",
        )
        missing.extend(HYPERSWARM_BLOCKERS)
        warnings.append("Do not launch HyperSwarm production from this runtime yet.")

    elif "gmail" in lowered and ("outreach" in lowered or "send" in lowered):
        use("provider-routing")
        use("toolset-resolution")
        use("memory/provenance-substrate")
        toolsets = ["browser", "file", "web"]
        minimum_context_level = 3
        missing.append(
            "No Gmail delivery substrate is verified in the current capability map."
        )
        missing.append(
            "A Google OAuth-backed Gmail send surface is required before live outreach can be sent."
        )
        warnings.append(
            "Drafting is possible; live send should stay blocked until a Gmail tool surface exists."
        )

    elif "local model" in lowered and "classification" in lowered:
        use("local-model-lane")
        use("provider-routing")
        use("process-intelligence-substrate")
        toolsets = ["file", "terminal"]
        minimum_context_level = 1
        provider_route = _current_primary_route(registry, prefer_local=True)
        if provider_route.status not in {"ready", "partial"}:
            missing.append(
                "No verified local model lane is configured for classification work."
            )
        warnings.append(
            "Benchmark local quality and throughput before promoting this lane to always-on bulk work."
        )

    elif "anthropic api" in lowered:
        use("provider-routing")
        toolsets = ["terminal"]
        minimum_context_level = 1
        provider_route = ProviderRoute(
            primary="anthropic",
            status="avoid_by_policy",
            rationale="Anthropic API-key routing is avoid_by_policy for routine Shay autonomous work.",
        )
        warnings.append(
            "Prefer Claude subscription / Claude Code capacity instead of the Anthropic API-key route."
        )
        warnings.append(
            "Only use the Anthropic API path if Fritz explicitly chooses it for a specific task."
        )
        fallback_route = ["claude-subscription/claude-code"] + [
            route
            for route in fallback_route
            if route != "claude-subscription/claude-code"
        ]

    else:
        use("provider-routing")
        use("toolset-resolution")
        toolsets = ["file"]
        warnings.append(
            "No specialized rule matched this task yet; review manually before automating."
        )

    if provider_route.status == "avoid_by_policy" and not any(
        "avoid_by_policy" in item for item in warnings
    ):
        warnings.append(
            f"Primary route {provider_route.primary} is avoid_by_policy for default autonomous use."
        )

    result = DecisionResult(
        task=text,
        matched_capabilities=matched,
        recommended_toolsets=toolsets,
        provider_route=provider_route.to_dict(),
        fallback_route=fallback_route,
        minimum_context_level=minimum_context_level,
        missing_prerequisites=missing,
        warnings_gaps=warnings,
    )
    return result.to_dict()


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def format_capability_list(registry: Mapping[str, Mapping[str, Any]]) -> str:
    rows = _ordered_capabilities(registry)
    lines = ["Capability Truth Layer", ""]
    for row in rows:
        observation = (row.get("details") or {}).get("observation_overlay") or {}
        suffix = ""
        if observation.get("observed_successes"):
            suffix = f" | observed-proof={observation.get('observed_successes')}"
        lines.append(f"- {row['id']} [{row['status']}] {row['summary']}{suffix}")
    return "\n".join(lines)


def format_capability_show(capability: Mapping[str, Any]) -> str:
    observation = (capability.get("details") or {}).get("observation_overlay") or {}
    lines = [
        f"{capability['id']} [{capability['status']}]",
        capability.get("summary", ""),
        (
            "Observed proof: "
            + (
                f"{observation.get('observed_successes', 0)} success / {observation.get('observed_failures', 0)} failure event(s); suggested reality class={observation.get('suggested_reality_class', 'n/a')}; promotion policy={observation.get('promotion_policy', 'n/a')}"
                if observation
                else "none recorded"
            )
        ),
        "",
        "Details:",
        json.dumps(capability.get("details", {}), indent=2, sort_keys=True),
    ]
    warnings = capability.get("warnings") or []
    if warnings:
        lines.extend(["", "Warnings:"])
        lines.extend([f"- {warning}" for warning in warnings])
    return "\n".join(lines)


def format_doctor(registry: Mapping[str, Mapping[str, Any]]) -> str:
    rows = _ordered_capabilities(registry)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1

    lines = ["Capability Doctor", ""]
    if counts:
        lines.append(
            "Status counts: "
            + ", ".join(
                f"{status}={counts[status]}"
                for status in sorted(counts.keys(), key=_status_rank)
            )
        )
        lines.append("")

    for row in rows:
        lines.append(f"- {row['id']} [{row['status']}] {row['summary']}")
        for warning in row.get("warnings") or []:
            lines.append(f"    warning: {warning}")
    return "\n".join(lines)


def format_decision(decision: Mapping[str, Any]) -> str:
    provider_route = decision.get("provider_route") or {}
    lines = [
        f"Task: {decision.get('task', '')}",
        "",
        "Matched capabilities:",
    ]
    matched = decision.get("matched_capabilities") or []
    lines.extend([f"- {item}" for item in matched] or ["- (none)"])
    lines.extend(["", "Recommended toolsets:"])
    toolsets = decision.get("recommended_toolsets") or []
    lines.extend([f"- {item}" for item in toolsets] or ["- (none)"])
    lines.extend([
        "",
        "Provider route:",
        f"- primary: {provider_route.get('primary', 'unknown')}",
        f"- status: {provider_route.get('status', 'unknown')}",
        f"- rationale: {provider_route.get('rationale', '')}",
        "",
        "Fallback route:",
    ])
    fallback = decision.get("fallback_route") or []
    lines.extend([f"- {item}" for item in fallback] or ["- (none configured)"])
    lines.extend([
        "",
        f"Minimum context level: {decision.get('minimum_context_level', 0)}",
        "",
        "Missing prerequisites:",
    ])
    missing = decision.get("missing_prerequisites") or []
    lines.extend([f"- {item}" for item in missing] or ["- (none)"])
    lines.extend(["", "Warnings / gaps:"])
    warnings = decision.get("warnings_gaps") or []
    lines.extend([f"- {item}" for item in warnings] or ["- (none)"])
    return "\n".join(lines)


def _matched_capability_rows(
    decision: Mapping[str, Any], registry: Mapping[str, Mapping[str, Any]]
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for capability_id in decision.get("matched_capabilities") or []:
        capability = registry.get(capability_id) or {}
        rows.append({
            "id": capability_id,
            "status": _text(capability.get("status")) or "unknown",
            "summary": _text(capability.get("summary")),
        })
    return rows


def _required_proof_surfaces(task: str, matched_capabilities: list[str]) -> list[str]:
    lowered = task.lower()
    surfaces = [
        "process-intelligence ledger entry",
        "capability doctor pass",
    ]
    if any(
        capability_id in matched_capabilities
        for capability_id in {
            "memory/provenance-substrate",
            "research-to-action",
            "episodic-memory",
            "github-to-obsidian",
        }
    ) or any(keyword in lowered for keyword in {"research", "memory", "obsidian", "capability matrix"}):
        surfaces.append("durable research artifact")
    if any(
        capability_id in matched_capabilities
        for capability_id in {
            "provider-routing",
            "gateway-runtime",
            "mcp-substrate",
            "skill/plugin-inventory",
            "local-model-lane",
            "fallback-chain",
            "worker-control",
            "agent-registry",
        }
    ) or "capability" in lowered:
        surfaces.append("shared capability matrix update")
    return surfaces


def build_gate_report(
    task: str,
    *,
    gate: str,
    registry: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    registry = registry or collect_capabilities()
    decision = build_decision(task, registry=registry)
    matched_rows = _matched_capability_rows(decision, registry)
    blocking = [
        row for row in matched_rows if row["status"] in {"unsafe", "blocked", "missing", "unknown"}
    ]
    status = "pass"
    if blocking or (decision.get("missing_prerequisites") or []):
        status = "fail"
    proof_surfaces = _required_proof_surfaces(task, decision.get("matched_capabilities") or [])
    closeout_actions = [
        "Run `shay capabilities doctor` and capture the result with the work artifact.",
        "Log the run in the process-intelligence spine with matched capabilities, blockers, and validation results.",
    ]
    if "durable research artifact" in proof_surfaces:
        closeout_actions.append(
            "Capture a durable research artifact that keeps observations separate from interpretations."
        )
    if "shared capability matrix update" in proof_surfaces:
        closeout_actions.append(
            "Update the shared Agent-Capability-Matrix note if this task changes installed/active/proven capability truth."
        )
    return CapabilityGateReport(
        task=task,
        gate=gate,
        status=status,
        matched_capabilities=matched_rows,
        blocking_capabilities=blocking,
        missing_prerequisites=list(decision.get("missing_prerequisites") or []),
        warnings_gaps=list(decision.get("warnings_gaps") or []),
        required_proof_surfaces=proof_surfaces,
        required_closeout_actions=closeout_actions,
    ).to_dict()


def format_gate_report(report: Mapping[str, Any]) -> str:
    lines = [
        f"Task: {report.get('task', '')}",
        f"Gate: {report.get('gate', '')}",
        f"Status: {report.get('status', 'unknown')}",
        "",
        "Matched capability truth:",
    ]
    matched = report.get("matched_capabilities") or []
    lines.extend(
        [f"- {item['id']} [{item['status']}] {item['summary']}" for item in matched]
        or ["- (none)"]
    )
    lines.extend(["", "Blocking capability truth:"])
    blocking = report.get("blocking_capabilities") or []
    lines.extend(
        [f"- {item['id']} [{item['status']}] {item['summary']}" for item in blocking]
        or ["- (none)"]
    )
    lines.extend(["", "Missing prerequisites:"])
    missing = report.get("missing_prerequisites") or []
    lines.extend([f"- {item}" for item in missing] or ["- (none)"])
    lines.extend(["", "Warnings / gaps:"])
    warnings = report.get("warnings_gaps") or []
    lines.extend([f"- {item}" for item in warnings] or ["- (none)"])
    lines.extend(["", "Required proof surfaces:"])
    proof = report.get("required_proof_surfaces") or []
    lines.extend([f"- {item}" for item in proof] or ["- (none)"])
    lines.extend(["", "Required closeout actions:"])
    actions = report.get("required_closeout_actions") or []
    lines.extend([f"- {item}" for item in actions] or ["- (none)"])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entrypoint + safe process-intelligence hook
# ---------------------------------------------------------------------------


def _log_capability_run(
    *,
    action: str,
    outcome: str,
    instruction_summary: str,
    decision: Mapping[str, Any] | None = None,
    registry: Mapping[str, Mapping[str, Any]] | None = None,
) -> None:
    try:
        from agent.process_intelligence import log_run

        decisions_made = list((decision or {}).get("matched_capabilities") or [])
        gaps_opened = list((decision or {}).get("missing_prerequisites") or [])
        validation_results = []
        if registry:
            validation_results = [
                {
                    "check": capability_id,
                    "status": capability.get("status"),
                    "summary": capability.get("summary"),
                }
                for capability_id, capability in registry.items()
            ]
        log_run({
            "lane": "capability-truth-layer",
            "task_name": f"shay capabilities {action}",
            "instruction_summary": instruction_summary,
            "outcome": outcome,
            "tools_used": ["shay capabilities"],
            "commands_run": [f"shay capabilities {action}"],
            "decisions_made": decisions_made,
            "gaps_opened": gaps_opened,
            "validation_results": validation_results,
        })
    except Exception:
        pass


def cmd_capabilities(args) -> int:
    action = _text(getattr(args, "capabilities_command", "")) or "list"
    registry = collect_capabilities()

    if action in {"list", "ls"}:
        print(format_capability_list(registry))
        return 0

    if action == "show":
        requested_id = _text(getattr(args, "capability_id", ""))
        capability_id = _normalized_capability_lookup(requested_id)
        if capability_id == "compatibility-matrix":
            print(_format_seed_matrix())
            return 0
        if capability_id == "intelligence-layer":
            print(_format_intelligence_bundle())
            return 0
        capability = registry.get(capability_id)
        if capability is None:
            print(
                "Unknown capability '"
                + requested_id
                + "'. Available: "
                + ", ".join([row["id"] for row in _ordered_capabilities(registry)])
                + ", compatibility-matrix, intelligence-layer"
            )
            _log_capability_run(
                action="show",
                outcome="blocked",
                instruction_summary=f"Failed capability lookup for {requested_id}.",
                registry=registry,
            )
            return 1
        print(format_capability_show(capability))
        return 0

    if action == "doctor":
        print(format_doctor(registry))
        _log_capability_run(
            action="doctor",
            outcome="success",
            instruction_summary="Ran capability truth layer doctor.",
            registry=registry,
        )
        return 0

    if action in {"preflight", "closeout"}:
        task = getattr(args, "task", "")
        if isinstance(task, list):
            task = " ".join(_text(item) for item in task if _text(item))
        else:
            task = _text(task)
        if not task:
            print(f'Usage: shay capabilities {action} "<task>"')
            return 1
        report = build_gate_report(task, gate=action, registry=registry)
        print(format_gate_report(report))
        _log_capability_run(
            action=action,
            outcome="success" if report.get("status") == "pass" else "blocked",
            instruction_summary=f"{action} gate for: {task}",
            decision={
                "matched_capabilities": [
                    item.get("id") for item in (report.get("matched_capabilities") or [])
                ],
                "missing_prerequisites": report.get("missing_prerequisites") or [],
            },
            registry=registry,
        )
        return 0 if report.get("status") == "pass" else 2

    if action == "decide":
        task = getattr(args, "task", "")
        if isinstance(task, list):
            task = " ".join(_text(item) for item in task if _text(item))
        else:
            task = _text(task)
        if not task:
            print('Usage: shay capabilities decide "<task>"')
            return 1
        decision = build_decision(task, registry=registry)
        print(format_decision(decision))
        _log_capability_run(
            action="decide",
            outcome="success",
            instruction_summary=f"Built capability decision for: {task}",
            decision=decision,
            registry=registry,
        )
        return 0

    print(f"Unknown capabilities subcommand: {action}")
    return 1


__all__ = [
    "build_decision",
    "build_gate_report",
    "cmd_capabilities",
    "collect_capabilities",
    "format_capability_list",
    "format_capability_show",
    "format_decision",
    "format_doctor",
    "format_gate_report",
]
