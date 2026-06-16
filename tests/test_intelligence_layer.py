from __future__ import annotations

import subprocess
import sys

import pytest

from shay_cli.intelligence_cmd import (
    SAFETY_GATES,
    WORKER_REQUIRED_FIELDS,
    build_gap_records,
    build_mission_graph,
    classify_research,
    intelligence_status,
    new_worker_record,
    render_brief,
    review_item,
    route_task,
    run_safe_swarm_dry_run,
    swarm_readiness,
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
    assert route["decision"] == "blocked_for_production"
    assert route["unsafe"] is True
    assert route["requires_fritz_approval"] is True
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
    summary = run_safe_swarm_dry_run()
    assert summary["status"] == "working"
    assert summary["production_hyperswarm_launched"] is False
    assert summary["forbidden_actions_happened"] is False
    assert summary["review_gate_enforced"] is True
    assert summary["stop_resume_fields_present"] is True
    assert summary["workers_marked_done"] is True
    assert len(summary["worker_ids"]) == 3
    for ledger in summary["ledger_paths"]:
        assert "ledgers" in ledger


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
    assert readiness["production_hyperswarm_gated"] is True
    checks = readiness["checks"]
    assert checks["worker_control"] is True
    assert checks["ledgers"] is True
    assert checks["review_gates"] is True
    assert checks["stop_resume_fields"] is True
    assert checks["production_launch_allowed"] is False


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
    assert status["production_hyperswarm_gated"] is True
    assert status["live_crons_enabled"] is False


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


def test_intelligence_cli_commands_format_without_crashing(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAY_INTELLIGENCE_HOME", str(tmp_path))
    commands = [
        ["intelligence", "status"],
        ["intelligence", "matrix"],
        ["intelligence", "agents"],
        ["intelligence", "events"],
        ["intelligence", "missions"],
        ["intelligence", "route", "launch HyperSwarm"],
        ["intelligence", "workers"],
        ["intelligence", "workers", "queue"],
        ["intelligence", "swarm", "status"],
        ["intelligence", "swarm", "readiness"],
        ["intelligence", "critical"],
        ["intelligence", "review-items"],
        ["intelligence", "research", "OpenJarvis"],
        ["intelligence", "brief", "morning"],
        ["intelligence", "brief", "gaps"],
        ["intelligence", "brief", "workers"],
        ["intelligence", "brief", "research"],
        ["intelligence", "brief", "critical"],
        ["intelligence", "brief", "high-items"],
        ["intelligence", "brief", "providers"],
        ["intelligence", "brief", "compression"],
        ["intelligence", "brief", "thoughts"],
        ["intelligence", "brief", "rd"],
        ["intelligence", "cadence", "list"],
    ]
    for command in commands:
        result = subprocess.run(
            [sys.executable, "-m", "shay_cli.main", *command],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (command, result.stderr, result.stdout)
        assert result.stdout.strip(), command



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
