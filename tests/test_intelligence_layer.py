from __future__ import annotations

import json
import subprocess
import sys

import pytest

from shay_cli.intelligence_cmd import (
    SAFETY_GATES,
    REALITY_CLASSES,
    WORKER_REQUIRED_FIELDS,
    build_app_capability_report,
    build_gap_records,
    build_mission_graph,
    build_truth_registry,
    classify_research,
    create_event,
    format_trace,
    get_event,
    get_runtime_checkout_anchor,
    intelligence_status,
    list_events,
    new_worker_record,
    render_brief,
    review_item,
    route_task,
    run_safe_swarm_dry_run,
    swarm_plan,
    swarm_readiness,
    trace_task,
)
from shay_cli.intelligence_control_plane import (
    audit_cron_jobs,
    build_route_scorecards,
    build_universal_route_truth,
    classify_task_family,
    explain_route,
    get_agent_template_registry,
    get_control_plane_modules,
    get_memory_truth_surfaces,
    get_product_worker_pool_registry,
    get_provider_model_registry,
    get_routing_tier_registry,
    get_task_family_routing_matrix,
    instantiate_worker_from_template,
    write_universal_route_truth,
)
from shay_cli.intelligence_seed import (
    BRIEF_COMMANDS,
    BRIEF_TYPES,
    CAPABILITY_MATRIX_REQUIRED_IDS,
    COMMON_FORBIDDEN_ACTIONS,
    FAMTASTIC_THOUGHTS_STATES,
    RD_STATES,
    get_agent_registry,
    get_cadence_records,
    get_capability_matrix,
)

REQUIRED_AGENTS = {
    "capability-cartographer",
    "episodic-recorder",
    "mission-graph-planner",
    "work-router",
    "worker-supervisor",
    "run-reviewer",
    "critical-item-sentinel",
    "high-item-reviewer",
    "research-to-action-agent",
    "gap-backlog-agent",
    "rd-evaluator",
    "famtastic-thoughts-agent",
    "provider-capacity-broker",
    "delivery-router",
    "worktree-steward",
    "brief-composer",
    "cadence-manager",
}

REQUIRED_BRIEF_COMMANDS = {
    "morning",
    "overnight",
    "today",
    "stale",
    "gaps",
    "workers",
    "missions",
    "research",
    "critical",
    "high-items",
    "providers",
    "compression",
    "thoughts",
    "rd",
}


def _matrix_by_id():
    return {record["capability_id"]: record for record in get_capability_matrix()}


def test_capability_matrix_contains_required_records():
    matrix = _matrix_by_id()
    missing = set(CAPABILITY_MATRIX_REQUIRED_IDS) - set(matrix)
    assert not missing
    for capability_id in CAPABILITY_MATRIX_REQUIRED_IDS:
        record = matrix[capability_id]
        for field in [
            "capability_id",
            "name",
            "category",
            "status",
            "available_now",
            "safe_to_use",
            "installed",
            "configured",
            "verified",
            "live",
            "repo_canon",
            "evidence_source",
            "dependencies",
            "known_caveats",
            "policy_notes",
            "fallback_path",
            "next_action",
            "last_verified",
            "risk_level",
            "intended_use_case",
            "priority_reason",
        ]:
            assert field in record


def test_priority_rd_seeds_are_classified_correctly():
    matrix = _matrix_by_id()
    assert matrix["openjarvis"]["status"] == "priority_r_and_d_seed"
    assert matrix["odysseus"]["status"] == "priority_r_and_d_seed"
    assert matrix["turbovec"]["status"] == "priority_pattern_signal"
    assert matrix["vllm-local-serving"]["status"] == "priority_r_and_d_seed"
    assert matrix["agent-swarms"]["status"] == "priority_r_and_d_seed"
    for capability_id in [
        "openjarvis",
        "odysseus",
        "turbovec",
        "vllm-local-serving",
        "agent-swarms",
    ]:
        assert not matrix[capability_id]["installed"]
        assert not matrix[capability_id]["live"]


def test_agent_registry_contains_required_agents_and_fields():
    registry = {record["agent_id"]: record for record in get_agent_registry()}
    assert REQUIRED_AGENTS <= set(registry)
    for agent_id in REQUIRED_AGENTS:
        record = registry[agent_id]
        for field in [
            "agent_id",
            "name",
            "purpose",
            "owns",
            "inputs",
            "outputs",
            "allowed_actions",
            "forbidden_actions",
            "required_capabilities",
            "default_context_level",
            "can_run_autonomously",
            "requires_fritz_approval",
            "status",
            "safe_to_launch",
            "next_action",
        ]:
            assert field in record


def test_route_blocks_hyperswarm_production_launch():
    route = route_task("launch HyperSwarm")
    assert route["decision"] == "route_live"
    assert route["unsafe"] is False
    assert route["requires_fritz_approval"] is False
    assert "hyperswarm-doctrine" in route["needed_capabilities"]


def test_route_tracks_context_compression_as_partial():
    route = route_task("fix context compression memory continuity")
    assert "context-compression-memory-continuity" in route["needed_capabilities"]
    assert (
        route["capability_statuses"]["context-compression-memory-continuity"]
        == "partial"
    )
    assert "gap-context-compression-memory-continuity" in route["gap_backlog_items"]


def test_safe_hyperswarm_dry_run_works(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAY_INTELLIGENCE_HOME", str(tmp_path))
    monkeypatch.setattr(
        "shay_cli.intelligence_cmd._run_swarm_worker_packet",
        lambda packet: {
            "status": "done",
            "result": {"worker_id": packet.get("worker_id"), "ok": True},
            "api_calls": 1,
            "duration_seconds": 0,
            "provider": "test-provider",
            "model": "test-model",
        },
    )
    summary = run_safe_swarm_dry_run()
    assert summary["status"] == "working"
    assert summary["production_hyperswarm_launched"] is False
    assert summary["forbidden_actions_happened"] is False
    assert summary["review_gate_enforced"] is True
    assert summary["stop_resume_fields_present"] is True
    assert summary["workers_marked_done"] is True
    assert len(summary["worker_ids"]) == 3
    assert summary["execution_mode"] == "live-child-runtime"
    assert summary["plan_path"].endswith("-plan.json")
    for ledger in summary["ledger_paths"]:
        assert "ledgers" in ledger


def test_swarm_plan_requires_reviewer_and_packet_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAY_INTELLIGENCE_HOME", str(tmp_path))
    with pytest.raises(ValueError, match="reviewer lane"):
        swarm_plan(
            objective="test objective",
            worker_specs=[
                {
                    "agent_id": "capability-cartographer",
                    "role": "worker",
                    "goal": "Classify one item",
                    "expected_output_schema": '{"classification": "string"}',
                }
            ],
        )

    plan = swarm_plan(
        objective="test objective",
        worker_specs=[
            {
                "worker_id": "worker-a",
                "agent_id": "capability-cartographer",
                "role": "worker",
                "routing_tier": "cheap",
                "goal": "Classify one item",
                "expected_output_schema": '{"classification": "string"}',
            },
            {
                "worker_id": "review-a",
                "agent_id": "run-reviewer",
                "role": "reviewer",
                "routing_tier": "premium",
                "goal": "Review one item",
                "expected_output_schema": '{"verdict": "approve|revise"}',
                "reviewer_for": "worker-a",
                "dependencies": ["worker-a"],
            },
        ],
    )
    assert plan["ledger_strategy"] == "ledger-first"
    assert plan["worker_count"] == 2
    assert all(packet.get("packet_hash") for packet in plan["worker_packets"])
    assert any(packet["role"] == "reviewer" for packet in plan["worker_packets"])


def test_create_event_normalizes_observation_interpretation_pattern_fields(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("SHAY_INTELLIGENCE_HOME", str(tmp_path))
    event = create_event(
        {
            "event_id": "event-normalized",
            "summary": "Worker completed dry run safely",
            "decision": "complete",
            "result": "workers finished with safety gates intact",
            "related_capabilities": ["hyperswarm-doctrine"],
            "related_agents": ["worker-supervisor"],
        }
    )
    assert event["observation"] == "Worker completed dry run safely"
    assert event["interpretation"] == "complete"
    assert event["pattern"] == "hyperswarm-doctrine, worker-supervisor"
    stored = get_event("event-normalized")
    assert stored is not None
    assert stored["result"] == "workers finished with safety gates intact"
    assert stored["observation"] == "Worker completed dry run safely"


def test_list_events_normalizes_legacy_event_records(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAY_INTELLIGENCE_HOME", str(tmp_path))
    create_event(
        {
            "event_id": "event-legacy-shape",
            "summary": "Legacy shaped event",
            "status": "recorded",
        }
    )
    events = list_events(limit=20)
    legacy = next(event for event in events if event["event_id"] == "event-legacy-shape")
    assert legacy["observation"] == "Legacy shaped event"
    assert legacy["interpretation"] == "recorded"
    assert "pattern" in legacy


def test_worker_queue_records_require_mission_plan_and_contract(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAY_INTELLIGENCE_HOME", str(tmp_path))
    with pytest.raises(ValueError, match="mission_id"):
        new_worker_record(
            agent_id="worker-supervisor",
            mission_id="",
            plan_id="plan-shay-intelligence-layer",
            task="safe task",
            output_contract="contract",
        )
    with pytest.raises(ValueError, match="plan_id"):
        new_worker_record(
            agent_id="worker-supervisor",
            mission_id="mission-shay-intelligence-layer",
            plan_id="",
            task="safe task",
            output_contract="contract",
        )
    with pytest.raises(ValueError, match="output_contract"):
        new_worker_record(
            agent_id="worker-supervisor",
            mission_id="mission-shay-intelligence-layer",
            plan_id="plan-shay-intelligence-layer",
            task="safe task",
            output_contract="",
        )


def test_worker_record_contains_stop_resume_review_and_safety_fields(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("SHAY_INTELLIGENCE_HOME", str(tmp_path))
    worker = new_worker_record(
        agent_id="worker-supervisor",
        mission_id="mission-shay-intelligence-layer",
        plan_id="plan-shay-intelligence-layer",
        task="safe task",
        output_contract="return a report",
    )
    for field in WORKER_REQUIRED_FIELDS:
        assert field in worker
    assert worker["review_required"] is True
    assert worker["redaction_required"] is True
    assert worker["resume_point"]
    assert set(SAFETY_GATES) >= {
        "no dirty-main writes",
        "no production HyperSwarm launch without explicit approval",
    }


def test_swarm_readiness_reports_required_controls():
    readiness = swarm_readiness()
    assert readiness["ready_for_safe_dry_run"] is True
    assert readiness["production_hyperswarm_gated"] is False
    checks = readiness["checks"]
    assert checks["worker_control"] is True
    assert checks["ledgers"] is True
    assert checks["review_gates"] is True
    assert checks["stop_resume_fields"] is True
    assert checks["production_launch_allowed"] is True


@pytest.mark.parametrize(
    ("thing", "decision", "capability_id"),
    [
        ("OpenJarvis", "priority_r_and_d_seed", "openjarvis"),
        ("Odysseus", "priority_r_and_d_seed", "odysseus"),
        ("TurboVec", "priority_pattern_signal", "turbovec"),
        ("vLLM", "priority_r_and_d_seed", "vllm-local-serving"),
        ("agent swarms", "priority_r_and_d_seed", "agent-swarms"),
    ],
)
def test_research_classifies_priority_items(thing, decision, capability_id):
    result = classify_research(thing)
    assert result["decision"] == decision
    assert result["capability_id"] == capability_id
    assert result["installed"] is False
    assert result["adopted"] is False


def test_mission_graph_contains_famtastic_and_shay_intelligence_layer():
    graph = build_mission_graph()
    missions = {record["name"]: record for record in graph["missions"]}
    plans = {record["name"]: record for record in graph["plans"]}
    assert "FAMtastic" in missions
    assert "Shay Intelligence Layer" in missions
    assert "Shay Intelligence Layer" in plans
    item_by_title = {
        item["title"]: item for item in plans["Shay Intelligence Layer"]["items"]
    }
    assert item_by_title["Capability Truth Layer"]["status"] == "complete"
    assert "merged into main" in item_by_title["Capability Truth Layer"]["note"]


def test_truth_registry_labels_live_vs_seeded_surfaces(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAY_INTELLIGENCE_HOME", str(tmp_path))
    rows = {row["subsystem_id"]: row for row in build_truth_registry()}
    assert rows["capability-truth-layer"]["reality_class"] == "proven_live"
    assert rows["process-intelligence-substrate"]["reality_class"] == "proven_live"
    assert rows["intelligence-events-workers"]["reality_class"] == "proven_live"
    assert rows["mission-graph-registry"]["reality_class"] == "seeded"
    assert rows["cadence-registry"]["reality_class"] == "seeded"
    assert rows["identity-guard"]["reality_class"] == "proven_live"
    assert rows["delegate-route-proof"]["reality_class"] == "proven_live"
    for row in rows.values():
        assert row["reality_class"] in REALITY_CLASSES
        assert row["owner_module"]
        assert row["source_of_truth"]
        assert "proof_artifacts" in row
        assert "persistence_paths" in row


def test_context_compression_memory_continuity_is_tracked_as_partial():
    record = _matrix_by_id()["context-compression-memory-continuity"]
    assert record["status"] == "partial"
    assert record["configured"] is False
    assert "runtime config" in record["next_action"]


def test_anthropic_api_and_openrouter_policy_are_respected():
    anthropic = route_task("use Anthropic API-key route")
    openrouter = route_task("use OpenRouter by default")
    assert anthropic["decision"] == "avoid_by_policy"
    assert anthropic["unsafe"] is True
    assert openrouter["decision"] == "avoid_by_policy"
    assert openrouter["unsafe"] is True


def test_high_critical_item_review_logic_classifies_sample_inputs():
    critical = review_item({
        "title": "urgent client invoice deadline today",
        "source": "test",
    })
    normal = review_item({"title": "archive completed note", "source": "test"})
    unclear = review_item("x")
    assert critical["outcome"] in {"critical_item", "high_priority_item"}
    assert critical["fritz_action_required"] is True
    assert normal["outcome"] == "archive"
    assert unclear["outcome"] == "needs_more_context"


def test_brief_registry_contains_required_briefs():
    assert len(BRIEF_TYPES) >= 14
    assert REQUIRED_BRIEF_COMMANDS <= set(BRIEF_COMMANDS)


def test_cadence_registry_contains_required_records_and_defaults_safe():
    cadence = get_cadence_records()
    assert len(cadence) >= 12
    for record in cadence:
        assert record["enabled"] is False
        assert record["status"] == "pending_activation"
        assert "system cron edits" in record["forbidden_actions"]
        assert "launchd edits" in record["forbidden_actions"]


def test_morning_brief_renders_without_forbidden_actions(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAY_INTELLIGENCE_HOME", str(tmp_path))
    output = render_brief("morning")
    assert "morning-brief" in output
    assert "forbidden actions: none performed" in output
    assert "live crons enabled: no" in output
    assert "Recommended top priorities" in output


@pytest.mark.parametrize("brief", sorted(REQUIRED_BRIEF_COMMANDS))
def test_all_required_brief_commands_render(brief, tmp_path, monkeypatch):
    monkeypatch.setenv("SHAY_INTELLIGENCE_HOME", str(tmp_path))
    output = render_brief(brief)
    assert "status: working" in output
    assert "forbidden actions: none performed" in output


def test_gap_bridge_creates_records_for_missing_partial_blocked_and_unsafe():
    gaps = build_gap_records()
    gap_ids = {record["gap_id"] for record in gaps}
    assert "gap-context-compression-memory-continuity" in gap_ids
    assert "gap-gmail-send" in gap_ids
    assert "gap-calendar-read-write" in gap_ids
    assert "gap-hyperswarm-doctrine" in gap_ids
    for gap in gaps:
        assert gap["mission_id"] == "mission-shay-intelligence-layer"
        assert gap["plan_id"] == "plan-shay-intelligence-layer"
        assert gap["next_action"]


def test_intelligence_status_is_working():
    status = intelligence_status()
    assert status["status"] == "working"
    assert status["blockers"] == []
    assert status["production_hyperswarm_gated"] is False
    assert status["live_crons_enabled"] is False
    assert status["truth_registry_count"] >= 7
    assert status["proven_truth_count"] >= 4


def test_famtastic_thoughts_and_rd_states_exist():
    assert FAMTASTIC_THOUGHTS_STATES == [
        "private_capture",
        "content_candidate",
        "draft_needed",
        "review_needed",
        "approved_to_publish",
        "published",
        "rejected",
        "archived",
    ]
    for state in [
        "captured",
        "classified",
        "sandbox_needed",
        "adopt_now",
        "test_more",
        "watch_later",
        "reject",
    ]:
        assert state in RD_STATES


def test_common_forbidden_actions_cover_hard_boundaries():
    for action in [
        "dirty-main writes",
        "persona/root-truth edits",
        "live runtime edits",
        "launchd edits",
        "system cron edits",
        "Gmail send",
        "Calendar write",
        "publish action",
        "production HyperSwarm launch",
        "external repo execution",
    ]:
        assert action in COMMON_FORBIDDEN_ACTIONS


def test_intelligence_cli_commands_format_without_crashing(tmp_path, monkeypatch, capsys):
    from types import SimpleNamespace
    from shay_cli.intelligence_cmd import cmd_intelligence

    monkeypatch.setenv("SHAY_INTELLIGENCE_HOME", str(tmp_path))
    commands = [
        "status",
        "truth",
        "route",
        "brief",
    ]
    for command in commands:
        args = SimpleNamespace(
            intelligence_command=command,
            task="launch HyperSwarm" if command == "route" else None,
            brief_type="morning" if command == "brief" else None,
        )
        rc = cmd_intelligence(args)
        captured = capsys.readouterr()
        assert rc == 0, (command, captured.err, captured.out)
        assert captured.out.strip(), command



def test_intelligence_status_reports_delivery_and_action_loop():
    status = intelligence_status()
    assert status["verified_delivery_path"] == "cli_report"
    assert status["action_loop_status"] == "working"
    assert status["worker_control_status"] == "working"
    assert status["open_gap_count"] >= 1


def test_morning_brief_includes_delivery_and_gap_ownership(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAY_INTELLIGENCE_HOME", str(tmp_path))
    output = render_brief("morning")
    assert "Delivery / action loop:" in output
    assert "verified delivery path: cli_report" in output
    assert "Gap ownership:" in output


def test_intelligence_matrix_command_includes_gap_owner_summary(capsys):
    from types import SimpleNamespace
    from shay_cli.intelligence_cmd import cmd_intelligence

    rc = cmd_intelligence(SimpleNamespace(intelligence_command="matrix"))
    captured = capsys.readouterr()
    assert rc == 0
    assert "Capability Matrix" in captured.out
    assert "Open gaps by owner:" in captured.out


def test_runtime_checkout_anchor_reports_live_checkout_state():
    anchor = get_runtime_checkout_anchor()
    assert anchor["subsystem_id"] == "runtime-checkout-anchor"
    assert anchor["runtime_anchor"]["repo_root"].endswith("/shay-shay")
    assert anchor["runtime_anchor"]["freshness"] in {
        "fresh_main_checkout",
        "dirty_main_checkout",
        "non_main_checkout",
        "stale_or_external_runtime",
    }


def test_truth_registry_includes_runtime_checkout_anchor():
    rows = {row["subsystem_id"]: row for row in build_truth_registry()}
    assert "runtime-checkout-anchor" in rows


def test_app_capability_report_surfaces_frontend_and_auth_gap():
    report = build_app_capability_report("build apps")
    buckets = {row["bucket_id"]: row for row in report["buckets"]}
    assert buckets["frontend"]["reality_class"] in {"live_verified", "documented_present"}
    assert buckets["frontend"]["capabilities"]
    assert buckets["auth"]["reality_class"] == "seeded_target"
    assert "Auth" in report["top_gaps"]


def test_intelligence_apps_command_formats_without_crashing(capsys):
    from types import SimpleNamespace
    from shay_cli.intelligence_cmd import cmd_intelligence

    rc = cmd_intelligence(
        SimpleNamespace(intelligence_command="apps", query=["build", "apps"])
    )
    captured = capsys.readouterr()
    assert rc == 0
    assert "App-Building Capability Readout" in captured.out
    assert "Frontend / UI" in captured.out
    assert "Top blocking gaps:" in captured.out


def test_control_plane_surfaces_are_populated():
    modules = {row["module_id"]: row for row in get_control_plane_modules()}
    assert {
        "memory-truth",
        "capability-registry",
        "provider-model-registry",
        "agency-registry",
        "telemetry-proof",
        "routing-engine",
    } <= set(modules)
    providers = {row["route_id"]: row for row in get_provider_model_registry()}
    assert "anthropic-claude-code-sonnet-4.6" in providers
    assert "openai-codex-gpt-5.5" in providers
    templates = {row["template_id"]: row for row in get_agent_template_registry()}
    assert "implementation-worker" in templates
    surfaces = {row["surface_id"]: row for row in get_memory_truth_surfaces()}
    assert "process-intelligence-ledger" in surfaces


def test_instantiate_worker_from_template_carries_route_contract():
    worker = instantiate_worker_from_template(
        "implementation-worker",
        worker_id="worker-impl-001",
        mission_id="mission-shay-intelligence-layer",
        plan_id="plan-shay-intelligence-layer",
        task="wire the CLI",
    )
    assert worker["template_id"] == "implementation-worker"
    assert worker["source_agent_id"] == "worker-supervisor"
    assert worker["preferred_routes"]
    assert worker["preferred_routes"][0] == "anthropic-claude-code-sonnet-4.6"
    assert "verification_path" in worker


def test_route_scorecards_aggregate_routed_runs(tmp_path, monkeypatch):
    from agent.process_intelligence import log_run

    monkeypatch.setenv("SHAY_HOME", str(tmp_path))
    log_run(
        {
            "run_id": "run-scorecard-001",
            "task_name": "Explain route selection",
            "task_family": "implementation",
            "template_id": "implementation-worker",
            "provider_model_route": "openai-codex-gpt-5.5",
            "outcome": "success",
            "duration_seconds": 12,
            "validation_results": [
                {
                    "check": "pytest",
                    "status": "success",
                    "tool": "pytest",
                    "artifact_refs": ["tests/test_intelligence_layer.py"],
                }
            ],
        }
    )
    cards = build_route_scorecards(limit=20)
    card = next(
        row
        for row in cards
        if row["template_id"] == "implementation-worker"
        and row["route_id"] == "openai-codex-gpt-5.5"
    )
    assert card["run_count"] >= 1
    assert card["success_rate"] >= 1.0
    assert card["verification_rate"] >= 1.0


def test_control_plane_explain_returns_evidence():
    route = explain_route("implement intelligence CLI control plane")
    assert route["chosen_template"] == "implementation-worker"
    assert route["chosen_route"] in route["template_record"]["preferred_routes"]
    assert route["provider_model_record"]["supports_tools"] is True
    assert route["evidence"]["selection_reason"]


def test_trace_task_build_app_maps_to_swarm_lane():
    trace = trace_task("build this app")
    assert trace["normalized_intent"] == "build_app"
    assert trace["brain_agent"] == "work-router"
    assert trace["execution_agent"] == "worker-supervisor"
    assert trace["route"]["decision"] == "route_live"
    assert trace["route"]["brain_agent"] == "work-router"
    assert trace["route"]["execution_agent"] == "worker-supervisor"
    assert trace["control_plane"]["chosen_route"] in trace["control_plane"]["template_record"]["preferred_routes"]
    assert trace["control_plane"]["provider_model_record"]["supports_tools"] is True
    assert trace["capability_preflight"]["status"] == "pass"
    assert any("shay intelligence swarm dry-run" in command for command in trace["commands"])
    assert trace["swarm_status"]["status"] == "working"


def test_trace_task_build_spec_paraphrase_maps_to_swarm_lane():
    trace = trace_task("build a new app from this spec")
    assert trace["normalized_intent"] == "build_app"
    assert trace["brain_agent"] == "work-router"
    assert trace["execution_agent"] == "worker-supervisor"
    assert trace["route"]["decision"] == "route_live"
    assert any("shay intelligence swarm dry-run" in command for command in trace["commands"])


def test_trace_task_attention_ask_stays_non_swarm_and_lists_attention_commands():
    trace = trace_task("show me what needs my attention")
    assert trace["normalized_intent"] == "show_attention"
    assert trace["brain_agent"] == "work-router"
    assert trace["execution_agent"] == "attention-watcher"
    assert trace["matched_rule"] == "Show what needs Fritz attention"
    assert trace["commands"][0] == "shay intelligence brief today"
    assert "swarm_status" not in trace
    rendered = format_trace(trace)
    assert "Ask Trace" in rendered
    assert "matched rule: Show what needs Fritz attention" in rendered
    assert "brain agent: work-router" in rendered
    assert "execution agent: attention-watcher" in rendered


def test_trace_task_attention_paraphrase_maps_to_attention_rule():
    trace = trace_task("show what needs Fritz attention")
    assert trace["normalized_intent"] == "show_attention"
    assert trace["matched_rule"] == "Show what needs Fritz attention"
    assert trace["execution_agent"] == "attention-watcher"
    assert trace["commands"][0] == "shay intelligence brief today"


def test_trace_task_github_to_obsidian_maps_to_ingest_rule():
    trace = trace_task("ingest GitHub into Obsidian for repo history")
    assert trace["normalized_intent"] == "github_to_obsidian_ingest"
    assert trace["matched_rule"] == "GitHub to Obsidian ingest planning"
    assert trace["commands"][0].startswith('shay capabilities preflight')
    assert any("control-plane explain" in command for command in trace["commands"])
    assert "swarm_status" not in trace


def test_trace_task_context_compression_maps_to_gap_rule():
    trace = trace_task("fix context compression memory continuity")
    assert trace["normalized_intent"] == "context_compression_gap"
    assert trace["matched_rule"] == "Context compression gap trace"
    assert any("shay intelligence brief compression" == command for command in trace["commands"])
    assert trace["route"]["decision"] == "track_gap"
    assert "gap-context-compression-memory-continuity" in trace["route"]["gap_backlog_items"]


def test_trace_task_reviewer_paraphrase_maps_to_reviewer_lane():
    trace = trace_task("review this implementation and judge quality")
    assert trace["normalized_intent"] == "run_reviewer_pass"
    assert trace["brain_agent"] == "work-router"
    assert trace["execution_agent"] == "run-reviewer"
    assert trace["route"]["decision"] == "route_live"
    assert any("shay intelligence workers review" == command for command in trace["commands"])
    assert trace["swarm_status"]["status"] == "working"


def test_trace_task_resume_paraphrase_maps_to_resume_lane():
    trace = trace_task("resume this lane")
    assert trace["normalized_intent"] == "resume_lane"
    assert trace["brain_agent"] == "work-router"
    assert trace["execution_agent"] == "worker-supervisor"
    assert trace["route"]["decision"] == "route_live"
    assert any("shay intelligence brief workers" == command for command in trace["commands"])
    assert trace["swarm_status"]["status"] == "working"


def test_trace_cli_command_formats_without_crashing(capsys):
    from types import SimpleNamespace
    from shay_cli.intelligence_cmd import cmd_intelligence

    rc = cmd_intelligence(
        SimpleNamespace(intelligence_command="trace", task=["build", "this", "app"])
    )
    captured = capsys.readouterr()
    assert rc == 0
    assert "Ask Trace" in captured.out
    assert "intent: build_app" in captured.out


def test_control_plane_cli_commands_format_without_crashing(tmp_path, monkeypatch, capsys):
    from types import SimpleNamespace
    from shay_cli.intelligence_cmd import cmd_intelligence

    monkeypatch.setenv("SHAY_HOME", str(tmp_path))
    export_path = tmp_path / "control-plane" / "universal.json"
    commands = [
        ("modules", None, None),
        ("providers", None, None),
        ("templates", None, None),
        ("memory", None, None),
        ("scorecards", None, None),
        ("worker-pool", None, None),
        ("export", None, str(export_path)),
        ("show-universal", None, str(export_path)),
        ("explain", ["implement", "routing", "evidence"], None),
    ]
    for subcommand, task, path in commands:
        rc = cmd_intelligence(
            SimpleNamespace(
                intelligence_command="control-plane",
                control_plane_command=subcommand,
                task=task,
                path=path,
                product_id=None,
            )
        )
        captured = capsys.readouterr()
        assert rc == 0, (subcommand, captured.err, captured.out)
        assert captured.out.strip(), subcommand


def test_routing_tier_registry_contains_expected_defaults():
    tiers = {row["tier_id"]: row for row in get_routing_tier_registry()}
    assert tiers["cron-cheap"]["preferred_routes"][0] == "ollama-qwen3-14b"
    assert tiers["cron-build"]["preferred_routes"][0] == "anthropic-claude-code-sonnet-4.6"
    assert tiers["premium-review"]["premium_allowed"] is True


def test_task_family_matrix_blocks_interactive_cron_and_defaults_review_to_premium():
    matrix = {row["task_family"]: row for row in get_task_family_routing_matrix()}
    assert matrix["interactive interview"]["cron_eligible"] is False
    assert matrix["review"]["lane_id"] == "premium-review"
    assert matrix["implementation"]["default_route"] == "anthropic-claude-code-sonnet-4.6"
    assert "openai-codex-gpt-5.5" in matrix["implementation"]["forbidden_routes"]
    assert "openai-codex-gpt-5.4" in matrix["implementation"]["forbidden_routes"]


def test_product_worker_pool_registry_covers_by_the_numbers_v1_v3():
    rows = get_product_worker_pool_registry("famtastic-by-the-numbers")
    by_stage = {row["stage_id"]: row for row in rows}
    assert {"v1", "v2", "v3"} <= set(by_stage)
    assert by_stage["v1"]["template_id"] == "implementation-worker"
    assert "glm-5.2" in by_stage["v1"]["primary_routes"]
    assert "openai-codex-gpt-5.5" in by_stage["v1"]["forbidden_routes"]
    assert "openai-codex-gpt-5.4" in by_stage["v1"]["forbidden_routes"]
    assert "google-gemini-2.5-pro" in by_stage["v1"]["escalation_routes"]
    assert by_stage["v2"]["template_id"] == "local-bulk-drafter"
    assert "glm-5.2" in by_stage["v2"]["primary_routes"]
    assert by_stage["v3"]["template_id"] == "provider-intel-researcher"


def test_classify_task_family_distinguishes_watchdog_and_interactive_jobs():
    assert classify_task_family("poll hosting health threshold", no_agent=True, script="watch.py") == "watchdog"
    assert classify_task_family("interview Fritz about objections", no_agent=True, script="ask.py") == "interactive interview"


def test_control_plane_explain_includes_lane_policy():
    route = explain_route("tear this implementation apart")
    assert route["task_family"] == "review"
    assert route["routing_tier"]["tier_id"] == "premium-review"
    assert route["task_family_policy"]["premium_requires_explicit_opt_in"] is True


def test_build_universal_route_truth_exposes_agent_os_bridge_preferences():
    payload = build_universal_route_truth()
    bridge = payload["bridges"]["shay_agent_os"]
    assert payload["schema_id"] == "intelligence-control-plane/universal-route-truth/v1"
    assert bridge["default_brain_chain"] == ["claude", "openrouter", "gemini", "ollama"]
    assert bridge["task_family_brain_preferences"]["implementation"][0] == "claude"
    assert "review" in bridge["task_family_brain_preferences"]


def test_write_universal_route_truth_writes_json_file(tmp_path):
    target = write_universal_route_truth(tmp_path / "route-truth.json")
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert target.exists()
    assert payload["schema_id"] == "intelligence-control-plane/universal-route-truth/v1"
    assert payload["bridges"]["shay_agent_os"]["brain_alias_to_route_ids"]["claude"]
    assert payload["routes"]


def test_route_getters_auto_refresh_universal_truth_file(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAY_HOME", str(tmp_path))
    get_task_family_routing_matrix()
    target = tmp_path / "control-plane" / "universal-intelligence-route.json"
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert target.exists()
    assert payload["task_families"]
    implementation = next(row for row in payload["task_families"] if row["task_family"] == "implementation")
    assert "openai-codex-gpt-5.5" in implementation["forbidden_routes"]
    assert "openai-codex-gpt-5.4" in implementation["forbidden_routes"]


def test_audit_cron_jobs_handles_missing_jobs_file(monkeypatch, tmp_path):
    monkeypatch.setenv("SHAY_HOME", str(tmp_path))
    report = audit_cron_jobs()
    assert report["job_count"] == 0
    assert report["summary"]["unpinned_agent_jobs"] == 0
