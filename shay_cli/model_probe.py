from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from agent.models_dev import get_model_capabilities, get_model_info
from shay_constants import get_shay_home
from shay_cli.auth import PROVIDER_REGISTRY, resolve_api_key_provider_credentials
from utils import atomic_json_write

_OPENAI_COMPAT_PATH = "/chat/completions"
_ONE_PIXEL_PNG_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9p2nXn0AAAAASUVORK5CYII="
)

_SUBSCRIPTION_PROVIDERS = {"openai-codex", "nous", "opencode-go"}
_METERED_PROVIDERS = {
    "anthropic",
    "openai",
    "openrouter",
    "zai",
    "gemini",
    "google",
    "kimi-coding",
    "kimi-coding-cn",
    "stepfun",
    "minimax",
    "minimax-oauth",
    "groq",
    "mistral",
    "cohere",
    "perplexity",
    "fireworks",
    "togetherai",
}
_FREE_TIER_PROVIDERS = {"lmstudio", "ollama", "ollama-cloud"}


@dataclass
class ProbeCheck:
    name: str
    status: str
    detail: str
    response_excerpt: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProbeResult:
    provider: str
    model: str
    probed_at: str
    auth_mode: str
    transport: str
    claim_layers: dict[str, Any]
    effective_capabilities: dict[str, Any]
    checks: list[ProbeCheck]
    overall_status: str
    source_order: list[str]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["checks"] = [check.to_dict() for check in self.checks]
        return data


@dataclass
class RouteScore:
    route_id: str
    provider_id: str
    model_id: str
    score: float
    reasons: list[str]
    effective_capabilities: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _runtime_dir() -> Path:
    path = get_shay_home() / "runtime"
    path.mkdir(parents=True, exist_ok=True)
    return path


def registry_path() -> Path:
    return _runtime_dir() / "model_capability_registry.json"


def load_probe_registry() -> dict[str, Any]:
    path = registry_path()
    if not path.exists():
        return {"version": 1, "models": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "models": {}}
    if not isinstance(data, dict):
        return {"version": 1, "models": {}}
    models = data.get("models")
    if not isinstance(models, dict):
        data["models"] = {}
    data.setdefault("version", 1)
    return data


def save_probe_registry(data: dict[str, Any]) -> Path:
    path = registry_path()
    atomic_json_write(path, data, indent=2)
    return path


def _model_key(provider: str, model: str) -> str:
    return f"{str(provider or '').strip().lower()}::{str(model or '').strip()}"


def billing_type_for_provider(provider: str) -> str:
    provider = str(provider or "").strip().lower()
    if provider in _SUBSCRIPTION_PROVIDERS:
        return "subscription"
    if provider in _FREE_TIER_PROVIDERS:
        return "free-tier"
    if provider in _METERED_PROVIDERS:
        return "metered"
    return "unknown"


def _catalog_claims(provider: str, model: str) -> dict[str, Any]:
    info = get_model_info(provider, model)
    caps = get_model_capabilities(provider, model)
    return {
        "provider": provider,
        "model": model,
        "model_family": getattr(info, "family", "") or getattr(caps, "model_family", ""),
        "supports_tools": bool(getattr(caps, "supports_tools", False)),
        "supports_vision": bool(getattr(caps, "supports_vision", False)),
        "supports_reasoning": bool(getattr(caps, "supports_reasoning", False)),
        "supports_structured_output": bool(getattr(info, "structured_output", False)),
        "supports_attachments": bool(getattr(info, "attachment", False)),
        "context_window": int(getattr(info, "context_window", 0) or getattr(caps, "context_window", 0) or 0),
        "max_output_tokens": int(getattr(info, "max_output", 0) or getattr(caps, "max_output_tokens", 0) or 0),
        "source": "models.dev + local capability overrides",
        "billing_type": billing_type_for_provider(provider),
    }


def _existing_live_probe(provider: str, model: str) -> dict[str, Any] | None:
    registry = load_probe_registry()
    models = registry.get("models") or {}
    entry = models.get(_model_key(provider, model))
    return entry if isinstance(entry, dict) else None


def build_effective_capability_record(provider: str, model: str) -> dict[str, Any]:
    catalog = _catalog_claims(provider, model)
    live = _existing_live_probe(provider, model) or {}
    live_caps = live.get("effective_capabilities") if isinstance(live, dict) else {}
    checks = live.get("checks") if isinstance(live, dict) else []
    result = dict(catalog)
    if isinstance(live_caps, dict):
        for key in (
            "supports_tools",
            "supports_vision",
            "supports_reasoning",
            "supports_structured_output",
            "context_window",
            "max_output_tokens",
        ):
            if key in live_caps and live_caps[key] is not None:
                result[key] = live_caps[key]
    result["live_probe_status"] = str(live.get("overall_status") or "unverified")
    result["last_probed_at"] = live.get("probed_at")
    result["probe_checks"] = checks if isinstance(checks, list) else []
    result["truth_precedence"] = [
        "live_probe",
        "local_override",
        "catalog_claim",
        "provider_docs",
    ]
    return result


def _excerpt(payload: Any) -> str:
    text = json.dumps(payload, sort_keys=True) if isinstance(payload, (dict, list)) else str(payload or "")
    text = text.replace("\n", " ").strip()
    return text[:240]


def _openai_compat_client(provider: str) -> tuple[httpx.Client | None, str, str]:
    provider_cfg = PROVIDER_REGISTRY.get(provider)
    if provider_cfg is None or provider_cfg.auth_type != "api_key":
        return None, "unsupported", "provider is not configured as an API-key OpenAI-compatible lane"
    creds = resolve_api_key_provider_credentials(provider)
    api_key = str(creds.get("api_key") or "").strip()
    base_url = str(creds.get("base_url") or provider_cfg.inference_base_url or "").strip().rstrip("/")
    if not api_key:
        return None, "missing_auth", "no API key resolved for provider"
    if not base_url.startswith("http"):
        return None, "unsupported", f"non-http base URL: {base_url}"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    client = httpx.Client(base_url=base_url, headers=headers, timeout=30.0)
    return client, "api_key", base_url


def _post_chat_completion(client: httpx.Client, payload: dict[str, Any]) -> tuple[bool, str, Any]:
    try:
        response = client.post(_OPENAI_COMPAT_PATH, json=payload)
        body: Any
        try:
            body = response.json()
        except Exception:
            body = response.text
        if response.status_code >= 400:
            return False, f"http_{response.status_code}", body
        return True, "ok", body
    except Exception as exc:
        return False, exc.__class__.__name__.lower(), str(exc)


def _probe_text(client: httpx.Client, model: str) -> ProbeCheck:
    ok, status, body = _post_chat_completion(client, {
        "model": model,
        "messages": [{"role": "user", "content": "reply with the single word ok"}],
        "max_tokens": 4,
        "temperature": 0,
    })
    return ProbeCheck("text", "pass" if ok else "fail", status if ok else f"text probe failed: {status}", _excerpt(body))


def _probe_tools(client: httpx.Client, model: str) -> ProbeCheck:
    ok, status, body = _post_chat_completion(client, {
        "model": model,
        "messages": [{"role": "user", "content": "Call the ping tool with value set to pong."}],
        "tools": [{
            "type": "function",
            "function": {
                "name": "ping",
                "description": "Echo probe",
                "parameters": {
                    "type": "object",
                    "properties": {"value": {"type": "string"}},
                    "required": ["value"],
                    "additionalProperties": False,
                },
            },
        }],
        "tool_choice": "required",
        "max_tokens": 32,
        "temperature": 0,
    })
    if ok:
        choices = body.get("choices") if isinstance(body, dict) else None
        message = choices[0].get("message") if isinstance(choices, list) and choices else {}
        tool_calls = message.get("tool_calls") if isinstance(message, dict) else None
        if isinstance(tool_calls, list) and tool_calls:
            return ProbeCheck("tools", "pass", "tool call returned", _excerpt(tool_calls[0]))
        return ProbeCheck("tools", "fail", "response succeeded but no tool_calls returned", _excerpt(body))
    return ProbeCheck("tools", "fail", f"tool probe failed: {status}", _excerpt(body))


def _probe_structured_output(client: httpx.Client, model: str) -> ProbeCheck:
    ok, status, body = _post_chat_completion(client, {
        "model": model,
        "messages": [{"role": "user", "content": "Return a JSON object with status='ok' and code=7."}],
        "response_format": {"type": "json_object"},
        "max_tokens": 40,
        "temperature": 0,
    })
    return ProbeCheck("structured_output", "pass" if ok else "fail", status if ok else f"structured output probe failed: {status}", _excerpt(body))


def _probe_vision(client: httpx.Client, model: str) -> ProbeCheck:
    ok, status, body = _post_chat_completion(client, {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "What color is this test image? Reply with one word."},
                {"type": "image_url", "image_url": {"url": _ONE_PIXEL_PNG_DATA_URL}},
            ],
        }],
        "max_tokens": 8,
        "temperature": 0,
    })
    return ProbeCheck("vision", "pass" if ok else "fail", status if ok else f"vision probe failed: {status}", _excerpt(body))


def _probe_long_context(client: httpx.Client, model: str) -> ProbeCheck:
    filler = "abcd " * 3000
    ok, status, body = _post_chat_completion(client, {
        "model": model,
        "messages": [{"role": "user", "content": f"Read this payload and answer done.\n\n{filler}"}],
        "max_tokens": 8,
        "temperature": 0,
    })
    return ProbeCheck("long_context", "pass" if ok else "fail", status if ok else f"long-context probe failed: {status}", _excerpt(body))


def probe_model(provider: str, model: str, *, force: bool = False) -> dict[str, Any]:
    provider = str(provider or "").strip().lower()
    model = str(model or "").strip()
    existing = _existing_live_probe(provider, model)
    if existing and not force:
        return existing

    catalog = _catalog_claims(provider, model)
    client, auth_mode, transport_detail = _openai_compat_client(provider)
    checks: list[ProbeCheck] = []
    if client is None:
        checks.append(ProbeCheck("text", "skipped", transport_detail))
        checks.append(ProbeCheck("tools", "skipped", transport_detail))
        checks.append(ProbeCheck("structured_output", "skipped", transport_detail))
        checks.append(ProbeCheck("vision", "skipped", transport_detail))
        checks.append(ProbeCheck("long_context", "skipped", transport_detail))
        overall_status = "skipped"
    else:
        try:
            checks.append(_probe_text(client, model))
            checks.append(_probe_tools(client, model))
            checks.append(_probe_structured_output(client, model))
            if catalog.get("supports_vision"):
                checks.append(_probe_vision(client, model))
            else:
                checks.append(ProbeCheck("vision", "skipped", "catalog/local truth says vision is unavailable"))
            checks.append(_probe_long_context(client, model))
        finally:
            client.close()
        statuses = [check.status for check in checks]
        overall_status = "pass" if statuses and all(status in {"pass", "skipped"} for status in statuses) else "fail"

    effective = dict(catalog)
    for check in checks:
        if check.name == "tools" and check.status in {"pass", "fail"}:
            effective["supports_tools"] = check.status == "pass"
        if check.name == "vision" and check.status in {"pass", "fail"}:
            effective["supports_vision"] = check.status == "pass"
        if check.name == "structured_output" and check.status in {"pass", "fail"}:
            effective["supports_structured_output"] = check.status == "pass"

    result = ProbeResult(
        provider=provider,
        model=model,
        probed_at=_utc_now(),
        auth_mode=auth_mode,
        transport=transport_detail,
        claim_layers={
            "catalog": catalog,
            "local_override_applied": catalog.get("source") == "models.dev + local capability overrides",
            "previous_live_probe": existing,
        },
        effective_capabilities=effective,
        checks=checks,
        overall_status=overall_status,
        source_order=["live_probe", "local_override", "catalog_claim", "provider_docs"],
    ).to_dict()

    registry = load_probe_registry()
    registry.setdefault("models", {})[_model_key(provider, model)] = result
    registry["last_updated"] = result["probed_at"]
    save_probe_registry(registry)
    return result


def list_probe_registry(provider: str | None = None) -> list[dict[str, Any]]:
    models = load_probe_registry().get("models") or {}
    rows = [value for value in models.values() if isinstance(value, dict)]
    if provider:
        provider = str(provider).strip().lower()
        rows = [row for row in rows if str(row.get("provider") or "").strip().lower() == provider]
    return sorted(rows, key=lambda row: (str(row.get("provider") or ""), str(row.get("model") or "")))


def score_routes_for_task(task: str, routes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    task_text = str(task or "").strip().lower()
    needs_tools = any(token in task_text for token in ("build", "implement", "fix", "code", "tool", "agent"))
    needs_vision = any(token in task_text for token in ("image", "vision", "screenshot", "design", "visual"))
    needs_reasoning = any(token in task_text for token in ("plan", "orchestrate", "review", "reason", "analyze"))
    scored: list[RouteScore] = []
    for route in routes:
        provider = str(route.get("provider_id") or "").strip().lower()
        model = str(route.get("model_id") or "").strip()
        effective = build_effective_capability_record(provider, model)
        score = 0.0
        reasons: list[str] = []
        if needs_tools:
            if effective.get("supports_tools"):
                score += 3.0
                reasons.append("tools matched")
            else:
                score -= 4.0
                reasons.append("tools missing")
        if needs_vision:
            if effective.get("supports_vision"):
                score += 3.0
                reasons.append("vision matched")
            else:
                score -= 4.0
                reasons.append("vision missing")
        if needs_reasoning and effective.get("supports_reasoning"):
            score += 2.0
            reasons.append("reasoning matched")
        if str(effective.get("billing_type") or "") == "subscription":
            score += 0.5
            reasons.append("subscription lane")
        probe_status = str(effective.get("live_probe_status") or "")
        if probe_status == "pass":
            score += 2.0
            reasons.append("live probe passed")
        elif probe_status == "fail":
            score -= 3.0
            reasons.append("live probe failed")
        scored.append(RouteScore(
            route_id=str(route.get("route_id") or ""),
            provider_id=provider,
            model_id=model,
            score=round(score, 3),
            reasons=reasons,
            effective_capabilities=effective,
        ))
    return [item.to_dict() for item in sorted(scored, key=lambda row: (-row.score, row.route_id))]


__all__ = [
    "billing_type_for_provider",
    "build_effective_capability_record",
    "list_probe_registry",
    "load_probe_registry",
    "probe_model",
    "registry_path",
    "save_probe_registry",
    "score_routes_for_task",
]
