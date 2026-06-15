from types import SimpleNamespace

from shay_cli.capabilities_cmd import (
    _configured_local_routes,
    _local_model_lane_capability,
    build_decision,
    cmd_capabilities,
    format_capability_list,
)


def _sample_registry():
    return {
        "provider-routing": {
            "id": "provider-routing",
            "title": "Provider routing",
            "status": "ready",
            "summary": "Resolved provider: openai",
            "details": {
                "resolved_provider": "openai",
                "config_provider": "openai",
                "active_provider": "openai",
            },
            "warnings": [],
        },
        "toolset-resolution": {
            "id": "toolset-resolution",
            "title": "Toolset resolution",
            "status": "ready",
            "summary": "4 CLI toolsets enabled",
            "details": {"toolsets": ["browser", "file", "terminal", "web"], "count": 4},
            "warnings": [],
        },
        "gateway-runtime": {
            "id": "gateway-runtime",
            "title": "Gateway runtime",
            "status": "partial",
            "summary": "Gateway status file exists but no live PID was confirmed",
            "details": {},
            "warnings": [],
        },
        "mcp-substrate": {
            "id": "mcp-substrate",
            "title": "MCP substrate",
            "status": "ready",
            "summary": "2 enabled MCP server(s) configured",
            "details": {
                "enabled_servers": ["basic-memory", "vault-search"],
                "disabled_servers": [],
            },
            "warnings": [],
        },
        "skill/plugin-inventory": {
            "id": "skill/plugin-inventory",
            "title": "Skill and plugin inventory",
            "status": "ready",
            "summary": "3/3 skills enabled; 1 plugin toolset(s)",
            "details": {
                "skill_names": ["github-to-obsidian", "hyperswarm", "shay-shay"],
                "skill_count_total": 3,
                "skill_count_enabled": 3,
                "plugin_toolsets": [
                    {"key": "mcp", "label": "MCP", "description": "Test plugin"}
                ],
            },
            "warnings": [],
        },
        "memory/provenance-substrate": {
            "id": "memory/provenance-substrate",
            "title": "Memory and provenance substrate",
            "status": "ready",
            "summary": "Memory servers enabled: basic-memory, vault-search",
            "details": {"enabled_memory_servers": ["basic-memory", "vault-search"]},
            "warnings": [],
        },
        "process-intelligence-substrate": {
            "id": "process-intelligence-substrate",
            "title": "Process intelligence substrate",
            "status": "ready",
            "summary": "Process-intelligence logging available",
            "details": {},
            "warnings": [],
        },
        "local-model-lane": {
            "id": "local-model-lane",
            "title": "Local model lane",
            "status": "ready",
            "summary": "Active local model lane detected",
            "details": {
                "configured_local_routes": [
                    {
                        "source": "model",
                        "provider": "custom(local)",
                        "model": "phi4-mini-64k:latest",
                        "base_url": "http://localhost:11434/v1",
                    }
                ]
            },
            "warnings": [],
        },
        "fallback-chain": {
            "id": "fallback-chain",
            "title": "Fallback chain",
            "status": "ready",
            "summary": "1 fallback route(s) configured",
            "details": {
                "entries": [
                    {
                        "provider": "openai",
                        "model": "gpt-5.4-mini",
                        "base_url": "",
                        "label": "openai:gpt-5.4-mini",
                    }
                ]
            },
            "warnings": [],
        },
        "hyperswarm-doctrine": {
            "id": "hyperswarm-doctrine",
            "title": "HyperSwarm doctrine",
            "status": "unsafe",
            "summary": "HyperSwarm doctrine is present, but runtime launch remains intentionally blocked",
            "details": {
                "installed_skill_names": ["hyperswarm"],
                "launch_safe": False,
                "blockers": ["Worker control plane is not implemented yet."],
            },
            "warnings": [
                "Treat HyperSwarm as doctrine/skill material only until the runtime control plane exists."
            ],
        },
    }


def _live_style_local_config():
    return {
        "model": {
            "provider": "openai-codex",
            "default": "gpt-5.4",
            "base_url": "https://chatgpt.com/backend-api/codex",
        },
        "custom_providers": [
            {
                "name": "Poe",
                "base_url": "https://api.poe.com/v1",
                "model": "gpt-5.4",
            },
            {
                "name": "ollama-local",
                "base_url": "http://localhost:11434/v1",
                "models": {"qwen3:14b": {}},
            },
        ],
        "fallback_providers": [
            {
                "provider": "ollama",
                "model": "phi4-mini-64k",
                "base_url": "http://localhost:11434/v1",
            }
        ],
    }


def test_format_capability_list_includes_core_registry_rows():
    output = format_capability_list(_sample_registry())
    assert "Capability Truth Layer" in output
    assert "provider-routing [ready]" in output
    assert "hyperswarm-doctrine [unsafe]" in output


def test_decide_github_to_obsidian_uses_memory_and_skills():
    decision = build_decision(
        "ingest GitHub repo into Obsidian", registry=_sample_registry()
    )
    assert "skill/plugin-inventory" in decision["matched_capabilities"]
    assert "mcp-substrate" in decision["matched_capabilities"]
    assert decision["minimum_context_level"] == 2
    assert decision["recommended_toolsets"] == ["file", "web", "skills"]
    assert decision["missing_prerequisites"] == []


def test_decide_hyperswarm_marks_launch_unsafe():
    decision = build_decision("launch HyperSwarm", registry=_sample_registry())
    assert decision["provider_route"]["status"] == "unsafe"
    assert decision["provider_route"]["primary"] == "blocked"
    assert any("Do not launch HyperSwarm" in item for item in decision["warnings_gaps"])
    assert any(
        "Worker control plane" in item for item in decision["missing_prerequisites"]
    )


def test_decide_gmail_outreach_requires_delivery_surface():
    decision = build_decision("send Gmail outreach", registry=_sample_registry())
    assert "provider-routing" in decision["matched_capabilities"]
    assert any(
        "Gmail delivery substrate" in item for item in decision["missing_prerequisites"]
    )
    assert decision["minimum_context_level"] == 3


def test_decide_local_model_classification_prefers_local_lane():
    decision = build_decision(
        "run local model classification", registry=_sample_registry()
    )
    assert decision["provider_route"]["primary"].startswith("custom(local)")
    assert decision["provider_route"]["status"] == "ready"
    assert decision["recommended_toolsets"] == ["file", "terminal"]


def test_decide_anthropic_api_is_avoid_by_policy():
    decision = build_decision(
        "use Anthropic API for reasoning", registry=_sample_registry()
    )
    assert decision["provider_route"]["primary"] == "anthropic"
    assert decision["provider_route"]["status"] == "avoid_by_policy"
    assert "claude-subscription/claude-code" in decision["fallback_route"]


def test_cmd_capabilities_list_does_not_log_success(monkeypatch, capsys):
    logs = []
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd.collect_capabilities", lambda: _sample_registry()
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._log_capability_run",
        lambda **kwargs: logs.append(kwargs),
    )

    rc = cmd_capabilities(SimpleNamespace(capabilities_command="list"))

    captured = capsys.readouterr()
    assert rc == 0
    assert "Capability Truth Layer" in captured.out
    assert logs == []


def test_cmd_capabilities_show_does_not_log_success(monkeypatch, capsys):
    logs = []
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd.collect_capabilities", lambda: _sample_registry()
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._log_capability_run",
        lambda **kwargs: logs.append(kwargs),
    )

    rc = cmd_capabilities(
        SimpleNamespace(
            capabilities_command="show",
            capability_id="provider-routing",
        )
    )

    captured = capsys.readouterr()
    assert rc == 0
    assert "provider-routing [ready]" in captured.out
    assert logs == []


def test_cmd_capabilities_decide_logs_success(monkeypatch, capsys):
    logs = []
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd.collect_capabilities", lambda: _sample_registry()
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._log_capability_run",
        lambda **kwargs: logs.append(kwargs),
    )

    rc = cmd_capabilities(
        SimpleNamespace(
            capabilities_command="decide",
            task=["run", "local", "model", "classification"],
        )
    )

    captured = capsys.readouterr()
    assert rc == 0
    assert "Task: run local model classification" in captured.out
    assert len(logs) == 1
    assert logs[0]["action"] == "decide"
    assert logs[0]["outcome"] == "success"


def test_configured_local_routes_detects_list_custom_providers_and_fallbacks():
    routes = _configured_local_routes(_live_style_local_config())

    assert routes == [
        {
            "source": "custom_providers[1]",
            "provider": "ollama-local",
            "model": "qwen3:14b",
            "base_url": "http://localhost:11434/v1",
        },
        {
            "source": "fallback_providers[0]",
            "provider": "ollama",
            "model": "phi4-mini-64k",
            "base_url": "http://localhost:11434/v1",
        },
    ]


def test_local_model_lane_marks_local_routes_partial_when_not_active():
    capability = _local_model_lane_capability(
        _live_style_local_config(),
        {"details": {"resolved_provider": "gemini"}},
    )

    assert capability.status == "partial"
    assert (
        capability.details["configured_local_routes"][0]["provider"] == "ollama-local"
    )
    assert capability.details["configured_local_routes"][1]["provider"] == "ollama"
    assert "configured, but none is active" in capability.summary


def test_decide_local_model_classification_prefers_partial_local_route():
    registry = _sample_registry()
    registry["provider-routing"]["details"] = {
        "resolved_provider": "gemini",
        "config_provider": "openai-codex",
        "active_provider": "gemini",
    }
    registry["local-model-lane"] = _local_model_lane_capability(
        _live_style_local_config(),
        {"details": {"resolved_provider": "gemini"}},
    ).to_dict()

    decision = build_decision("run local model classification", registry=registry)

    assert decision["provider_route"]["primary"].startswith("ollama-local:qwen3:14b")
    assert decision["provider_route"]["status"] == "partial"
