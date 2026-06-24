from __future__ import annotations

from shay_cli import model_probe


def test_build_effective_capability_record_prefers_live_probe(monkeypatch):
    monkeypatch.setattr(model_probe, "_catalog_claims", lambda provider, model: {
        "provider": provider,
        "model": model,
        "supports_tools": True,
        "supports_vision": True,
        "supports_reasoning": False,
        "supports_structured_output": False,
        "context_window": 1000,
        "max_output_tokens": 100,
        "source": "models.dev + local capability overrides",
        "billing_type": "metered",
    })
    monkeypatch.setattr(model_probe, "_existing_live_probe", lambda provider, model: {
        "overall_status": "pass",
        "probed_at": "2026-06-24T00:00:00+00:00",
        "checks": [{"name": "tools", "status": "fail"}],
        "effective_capabilities": {
            "supports_tools": False,
            "supports_vision": False,
            "supports_structured_output": True,
        },
    })

    record = model_probe.build_effective_capability_record("zai", "glm-5.2")
    assert record["supports_tools"] is False
    assert record["supports_vision"] is False
    assert record["supports_structured_output"] is True
    assert record["live_probe_status"] == "pass"


def test_probe_model_skips_unsupported_transport(monkeypatch):
    monkeypatch.setattr(model_probe, "_catalog_claims", lambda provider, model: {
        "provider": provider,
        "model": model,
        "supports_tools": False,
        "supports_vision": False,
        "supports_reasoning": False,
        "supports_structured_output": False,
        "context_window": 1000,
        "max_output_tokens": 100,
        "source": "models.dev + local capability overrides",
        "billing_type": "subscription",
    })
    monkeypatch.setattr(model_probe, "_existing_live_probe", lambda provider, model: None)
    monkeypatch.setattr(model_probe, "save_probe_registry", lambda data: None)
    monkeypatch.setattr(model_probe, "load_probe_registry", lambda: {"version": 1, "models": {}})
    monkeypatch.setattr(model_probe, "_openai_compat_client", lambda provider: (None, "unsupported", "not probeable"))

    result = model_probe.probe_model("openai-codex", "gpt-5.5", force=True)
    assert result["overall_status"] == "skipped"
    assert all(check["status"] == "skipped" for check in result["checks"])


def test_score_routes_for_task_penalizes_failed_probe():
    routes = [
        {"route_id": "route-a", "provider_id": "zai", "model_id": "glm-5.2"},
        {"route_id": "route-b", "provider_id": "openai-codex", "model_id": "gpt-5.5"},
    ]

    original = model_probe.build_effective_capability_record
    try:
        model_probe.build_effective_capability_record = lambda provider, model: {
            "supports_tools": provider == "openai-codex",
            "supports_vision": False,
            "supports_reasoning": True,
            "billing_type": "subscription" if provider == "openai-codex" else "metered",
            "live_probe_status": "pass" if provider == "openai-codex" else "fail",
        }
        scores = model_probe.score_routes_for_task("build and fix this agent route", routes)
    finally:
        model_probe.build_effective_capability_record = original

    assert scores[0]["route_id"] == "route-b"
    assert scores[1]["route_id"] == "route-a"
