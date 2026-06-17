from types import SimpleNamespace

from shay_cli.capabilities_cmd import (
    _configured_local_routes,
    _local_model_lane_capability,
    build_decision,
    build_gate_report,
    cmd_capabilities,
    collect_capabilities,
    format_capability_list,
    format_capability_show,
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


def test_format_capability_show_includes_observed_proof_line():
    capability = _sample_registry()["provider-routing"]
    capability["details"] = {
        **capability["details"],
        "observation_overlay": {
            "observed_successes": 2,
            "observed_failures": 1,
            "suggested_reality_class": "implemented_unverified",
            "promotion_policy": "mixed-evidence-review-required",
        },
    }

    output = format_capability_show(capability)

    assert "Observed proof: 2 success / 1 failure event(s)" in output
    assert "suggested reality class=implemented_unverified" in output
    assert "promotion policy=mixed-evidence-review-required" in output


def test_collect_capabilities_applies_process_intelligence_observation_overlay(monkeypatch):
    monkeypatch.setattr("shay_cli.capabilities_cmd._safe_load_config", lambda: {})
    monkeypatch.setattr("shay_cli.capabilities_cmd._skill_inventory", lambda: {"enabled": []})
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._provider_routing_capability",
        lambda config: type("Record", (), {"id": "provider-routing", "to_dict": lambda self: _sample_registry()["provider-routing"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._toolset_resolution_capability",
        lambda config: type("Record", (), {"id": "toolset-resolution", "to_dict": lambda self: _sample_registry()["toolset-resolution"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._gateway_runtime_capability",
        lambda: type("Record", (), {"id": "gateway-runtime", "to_dict": lambda self: _sample_registry()["gateway-runtime"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._mcp_substrate_capability",
        lambda config: type("Record", (), {
            "id": "mcp-substrate",
            "details": {"enabled_servers": []},
            "to_dict": lambda self: _sample_registry()["mcp-substrate"],
        })(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._skill_plugin_inventory_capability",
        lambda inventory: type("Record", (), {"id": "skill/plugin-inventory", "to_dict": lambda self: _sample_registry()["skill/plugin-inventory"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._memory_provenance_capability",
        lambda enabled: type("Record", (), {"id": "memory/provenance-substrate", "to_dict": lambda self: _sample_registry()["memory/provenance-substrate"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._process_intelligence_capability",
        lambda: type("Record", (), {"id": "process-intelligence-substrate", "to_dict": lambda self: _sample_registry()["process-intelligence-substrate"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._local_model_lane_capability",
        lambda config, provider: type("Record", (), {"id": "local-model-lane", "to_dict": lambda self: _sample_registry()["local-model-lane"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._fallback_chain_capability",
        lambda config: type("Record", (), {"id": "fallback-chain", "to_dict": lambda self: _sample_registry()["fallback-chain"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._hyperswarm_doctrine_capability",
        lambda inventory: type("Record", (), {"id": "hyperswarm-doctrine", "to_dict": lambda self: _sample_registry()["hyperswarm-doctrine"]})(),
    )
    monkeypatch.setattr("shay_cli.capabilities_cmd._merge_intelligence_capability_matrix", lambda registry: registry)
    monkeypatch.setattr(
        "agent.process_intelligence.list_run_records",
        lambda limit=50: [
            {
                "run_id": "run-1",
                "ended_at": "2026-06-17T12:00:00Z",
                "outcome": "success",
                "lane": "capability-truth-layer",
                "task_name": "verify provider routing",
                "validation_results": [
                    {
                        "check": "provider-routing",
                        "status": "passed",
                        "summary": "provider route verified",
                        "verifier": "pytest",
                    }
                ],
            }
        ],
    )

    registry = collect_capabilities()

    observed = registry["provider-routing"]["details"]["observation_overlay"]
    assert observed["observed_successes"] == 1
    assert observed["last_run_id"] == "run-1"
    assert observed["verifier_backed_successes"] == 1
    assert observed["promotion_policy"] == "collect-more-verifier-proof"
    assert any(
        "promotion still needs verifier-backed proof across repeated runs" in warning
        for warning in registry["provider-routing"]["warnings"]
    )


def test_collect_capabilities_marks_multi_run_verifier_backed_success_as_promotion_eligible(monkeypatch):
    monkeypatch.setattr("shay_cli.capabilities_cmd._safe_load_config", lambda: {})
    monkeypatch.setattr("shay_cli.capabilities_cmd._skill_inventory", lambda: {"enabled": []})
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._provider_routing_capability",
        lambda config: type("Record", (), {"id": "provider-routing", "to_dict": lambda self: _sample_registry()["provider-routing"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._toolset_resolution_capability",
        lambda config: type("Record", (), {"id": "toolset-resolution", "to_dict": lambda self: _sample_registry()["toolset-resolution"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._gateway_runtime_capability",
        lambda: type("Record", (), {"id": "gateway-runtime", "to_dict": lambda self: _sample_registry()["gateway-runtime"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._mcp_substrate_capability",
        lambda config: type("Record", (), {
            "id": "mcp-substrate",
            "details": {"enabled_servers": []},
            "to_dict": lambda self: _sample_registry()["mcp-substrate"],
        })(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._skill_plugin_inventory_capability",
        lambda inventory: type("Record", (), {"id": "skill/plugin-inventory", "to_dict": lambda self: _sample_registry()["skill/plugin-inventory"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._memory_provenance_capability",
        lambda enabled: type("Record", (), {"id": "memory/provenance-substrate", "to_dict": lambda self: _sample_registry()["memory/provenance-substrate"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._process_intelligence_capability",
        lambda: type("Record", (), {"id": "process-intelligence-substrate", "to_dict": lambda self: _sample_registry()["process-intelligence-substrate"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._local_model_lane_capability",
        lambda config, provider: type("Record", (), {"id": "local-model-lane", "to_dict": lambda self: _sample_registry()["local-model-lane"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._fallback_chain_capability",
        lambda config: type("Record", (), {"id": "fallback-chain", "to_dict": lambda self: _sample_registry()["fallback-chain"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._hyperswarm_doctrine_capability",
        lambda inventory: type("Record", (), {"id": "hyperswarm-doctrine", "to_dict": lambda self: _sample_registry()["hyperswarm-doctrine"]})(),
    )
    monkeypatch.setattr("shay_cli.capabilities_cmd._merge_intelligence_capability_matrix", lambda registry: registry)
    monkeypatch.setattr(
        "agent.process_intelligence.list_run_records",
        lambda limit=50: [
            {
                "run_id": "run-2",
                "ended_at": "2026-06-17T12:05:00Z",
                "outcome": "success",
                "lane": "capability-truth-layer",
                "task_name": "verify provider routing again",
                "validation_results": [
                    {
                        "check": "provider-routing",
                        "status": "passed",
                        "summary": "provider route verified again",
                        "verifier": "pytest",
                    }
                ],
            },
            {
                "run_id": "run-1",
                "ended_at": "2026-06-17T12:00:00Z",
                "outcome": "success",
                "lane": "capability-truth-layer",
                "task_name": "verify provider routing",
                "validation_results": [
                    {
                        "check": "provider-routing",
                        "status": "passed",
                        "summary": "provider route verified",
                        "verifier": "pytest",
                    }
                ],
            },
        ],
    )

    registry = collect_capabilities()

    observed = registry["provider-routing"]["details"]["observation_overlay"]
    assert observed["observed_successes"] == 2
    assert observed["verifier_backed_successes"] == 2
    assert observed["suggested_reality_class"] == "proven_live"
    assert observed["promotion_policy"] == "eligible-for-curated-promotion"


def test_collect_capabilities_marks_mixed_evidence_as_partial(monkeypatch):
    monkeypatch.setattr("shay_cli.capabilities_cmd._safe_load_config", lambda: {})
    monkeypatch.setattr("shay_cli.capabilities_cmd._skill_inventory", lambda: {"enabled": []})
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._provider_routing_capability",
        lambda config: type("Record", (), {"id": "provider-routing", "to_dict": lambda self: _sample_registry()["provider-routing"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._toolset_resolution_capability",
        lambda config: type("Record", (), {"id": "toolset-resolution", "to_dict": lambda self: _sample_registry()["toolset-resolution"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._gateway_runtime_capability",
        lambda: type("Record", (), {"id": "gateway-runtime", "to_dict": lambda self: _sample_registry()["gateway-runtime"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._mcp_substrate_capability",
        lambda config: type("Record", (), {
            "id": "mcp-substrate",
            "details": {"enabled_servers": []},
            "to_dict": lambda self: _sample_registry()["mcp-substrate"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._skill_plugin_inventory_capability",
        lambda inventory: type("Record", (), {"id": "skill/plugin-inventory", "to_dict": lambda self: _sample_registry()["skill/plugin-inventory"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._memory_provenance_capability",
        lambda enabled: type("Record", (), {"id": "memory/provenance-substrate", "to_dict": lambda self: _sample_registry()["memory/provenance-substrate"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._process_intelligence_capability",
        lambda: type("Record", (), {"id": "process-intelligence-substrate", "to_dict": lambda self: _sample_registry()["process-intelligence-substrate"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._local_model_lane_capability",
        lambda config, provider: type("Record", (), {"id": "local-model-lane", "to_dict": lambda self: _sample_registry()["local-model-lane"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._fallback_chain_capability",
        lambda config: type("Record", (), {"id": "fallback-chain", "to_dict": lambda self: _sample_registry()["fallback-chain"]})(),
    )
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd._hyperswarm_doctrine_capability",
        lambda inventory: type("Record", (), {"id": "hyperswarm-doctrine", "to_dict": lambda self: _sample_registry()["hyperswarm-doctrine"]})(),
    )
    monkeypatch.setattr("shay_cli.capabilities_cmd._merge_intelligence_capability_matrix", lambda registry: registry)
    monkeypatch.setattr(
        "agent.process_intelligence.list_run_records",
        lambda limit=50: [
            {
                "run_id": "run-1",
                "ended_at": "2026-06-17T12:00:00Z",
                "outcome": "success",
                "lane": "capability-truth-layer",
                "task_name": "verify provider routing",
                "validation_results": [
                    {
                        "check": "provider-routing",
                        "status": "passed",
                        "summary": "provider route verified",
                        "verifier": "pytest",
                    },
                    {
                        "check": "provider-routing",
                        "status": "failed",
                        "summary": "fallback route failed under load",
                        "verifier": "pytest",
                    },
                ],
            }
        ],
    )

    registry = collect_capabilities()

    observed = registry["provider-routing"]["details"]["observation_overlay"]
    assert observed["suggested_reality_class"] == "partial"
    assert observed["promotion_policy"] == "mixed-evidence-review-required"


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


def test_build_gate_report_fails_when_prerequisites_are_missing():
    report = build_gate_report(
        "send Gmail outreach",
        gate="preflight",
        registry=_sample_registry(),
    )

    assert report["status"] == "fail"
    assert any(
        item["id"] == "provider-routing" for item in report["matched_capabilities"]
    )
    assert any(
        "Gmail delivery substrate" in item for item in report["missing_prerequisites"]
    )


def test_build_gate_report_requires_research_artifact_for_memory_work():
    report = build_gate_report(
        "ingest GitHub repo into Obsidian",
        gate="closeout",
        registry=_sample_registry(),
    )

    assert report["status"] == "pass"
    assert "durable research artifact" in report["required_proof_surfaces"]
    assert any(
        "Agent-Capability-Matrix" in item for item in report["required_closeout_actions"]
    )


def test_cmd_capabilities_preflight_returns_blocked_exit_when_gate_fails(monkeypatch, capsys):
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
            capabilities_command="preflight",
            task=["send", "Gmail", "outreach"],
        )
    )

    captured = capsys.readouterr()
    assert rc == 2
    assert "Gate: preflight" in captured.out
    assert "Status: fail" in captured.out
    assert len(logs) == 1
    assert logs[0]["action"] == "preflight"
    assert logs[0]["outcome"] == "blocked"


def test_cmd_capabilities_closeout_returns_success_when_gate_passes(monkeypatch, capsys):
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
            capabilities_command="closeout",
            task=["run", "local", "model", "classification"],
        )
    )

    captured = capsys.readouterr()
    assert rc == 0
    assert "Gate: closeout" in captured.out
    assert "Required proof surfaces:" in captured.out
    assert len(logs) == 1
    assert logs[0]["action"] == "closeout"
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


def test_decide_operating_brief_routes_through_delivery_and_briefs():
    decision = build_decision("deliver morning brief via today hub report", registry=_sample_registry())
    assert "operating-briefs" in decision["matched_capabilities"]
    assert "delivery-router" in decision["matched_capabilities"]
    assert decision["recommended_toolsets"] == ["file"]
    assert decision["minimum_context_level"] == 2


def test_cmd_capabilities_show_supports_compatibility_matrix_alias(monkeypatch, capsys):
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd.collect_capabilities", lambda: _sample_registry()
    )

    rc = cmd_capabilities(
        SimpleNamespace(
            capabilities_command="show",
            capability_id="compatibility-matrix",
        )
    )

    captured = capsys.readouterr()
    assert rc == 0
    assert "Compatibility Matrix" in captured.out
    assert "context-compression-memory-continuity" in captured.out


def test_cmd_capabilities_show_supports_intelligence_layer_alias(monkeypatch, capsys):
    monkeypatch.setattr(
        "shay_cli.capabilities_cmd.collect_capabilities", lambda: _sample_registry()
    )

    rc = cmd_capabilities(
        SimpleNamespace(
            capabilities_command="show",
            capability_id="intelligence-layer",
        )
    )

    captured = capsys.readouterr()
    assert rc == 0
    assert "Shay Intelligence Layer" in captured.out
    assert "verified delivery path" in captured.out
