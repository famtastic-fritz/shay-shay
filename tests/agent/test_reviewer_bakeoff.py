import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from agent.reviewer_bakeoff import (
    BenchmarkPacket,
    ReviewerCandidate,
    build_reviewer_messages,
    load_scores,
    parse_candidate,
    reduce_scores,
    run_live_bakeoff,
    run_simulated_bakeoff,
    score_output,
    write_default_packets,
)
from agent.swarm_telemetry import LaneRecord, SwarmRunLedger


def test_reviewer_score_marks_unconsumed_packet_quality_failed():
    packet = BenchmarkPacket(
        packet_id="p1",
        task_family="plan_review",
        artifact_name="plan.md",
        artifact_content="rollback is missing",
        rubric=["check rollback"],
        expected_issue_markers=["rollback"],
    )
    candidate = ReviewerCandidate(provider="custom", model="gemma4:latest", budget_class="cheap")

    score = score_output(
        run_id="r1",
        lane_id="l1",
        candidate=candidate,
        packet=packet,
        output="Please provide the plan so I can review it.",
    )

    assert score.status == "quality_failed"
    assert score.consumed_artifact is False
    assert score.fabricated_claims is True
    assert "adversarial_review" in score.demoted_for_roles


def test_reviewer_score_promotes_grounded_candidate_for_task_family():
    packet = BenchmarkPacket(
        packet_id="p2",
        task_family="telemetry_schema",
        artifact_name="lanes.jsonl",
        artifact_content="bad timestamp order",
        rubric=["check timestamp"],
        expected_issue_markers=["timestamp"],
        min_citations=1,
    )
    candidate = ReviewerCandidate(provider="custom", model="glm-5.1", budget_class="cheap", tool_capable=True)

    output = (
        "Reviewed artifact `lanes.jsonl` for packet p2.\n"
        "- severity: medium; source: `lanes.jsonl` line 1; issue: timestamp is wrong; "
        "fix: validate timestamp ordering."
    )
    score = score_output(run_id="r1", lane_id="l2", candidate=candidate, packet=packet, output=output)

    assert score.status == "pass"
    assert score.consumed_artifact is True
    assert score.cited_sources is True
    assert "telemetry_schema" in score.promoted_for_roles


def test_simulated_bakeoff_writes_scorecard_and_reducer_recommends_routes(tmp_path: Path):
    packets_path = tmp_path / "packets.json"
    scorecard = tmp_path / "scorecard.jsonl"
    write_default_packets(packets_path)
    packets = json.loads(packets_path.read_text())["packets"]
    assert len(packets) == 5

    run_simulated_bakeoff("proof-run", [BenchmarkPacket(**packet) for packet in packets], scorecard)
    scores = load_scores(scorecard)
    summary = reduce_scores(scores)

    assert len(scores) == 10
    assert summary["models"]["custom/gemma4:latest"]["recommendation"] == "demote_from_review; clerk_only_until_probe_passes"
    assert summary["models"]["custom/glm-5.1"]["recommendation"] == "promote_for_passed_task_families"
    assert summary["models"]["custom/glm-5.1"]["pass_rate"] == 1.0


def test_build_reviewer_messages_embeds_artifact_and_grounding_shape():
    packet = BenchmarkPacket(
        packet_id="p3",
        task_family="doc_consistency",
        artifact_name="docs.md",
        artifact_content="Gemma is default. Gemma is not approved.",
        rubric=["find contradiction"],
        expected_issue_markers=["contradiction"],
    )

    messages = build_reviewer_messages(packet)
    prompt = messages[1]["content"]

    assert messages[0]["role"] == "system"
    assert "docs.md" in prompt
    assert "Gemma is default" in prompt
    assert "severity: blocker|high|medium|low" in prompt
    assert "contradiction" in prompt


def test_live_bakeoff_invokes_llm_and_writes_raw_outputs(tmp_path: Path):
    packet = BenchmarkPacket(
        packet_id="p4",
        task_family="telemetry_schema",
        artifact_name="lanes.jsonl",
        artifact_content="end_time before start_time",
        rubric=["check timestamp"],
        expected_issue_markers=["timestamp"],
        min_citations=1,
    )
    candidate = ReviewerCandidate(provider="custom", model="glm-5.1", budget_class="cheap", tool_capable=True)
    calls = []

    def fake_llm_call(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=(
                            "Reviewed artifact `lanes.jsonl` for packet p4.\n"
                            "- severity: high; source: `lanes.jsonl` line 1; issue: timestamp order is invalid; "
                            "fix: validate end_time after start_time."
                        )
                    )
                )
            ]
        )

    scorecard = tmp_path / "scorecard.jsonl"
    scores = run_live_bakeoff(
        "live-proof",
        [packet],
        scorecard,
        [candidate],
        llm_call=fake_llm_call,
        output_dir=tmp_path / "raw",
    )

    assert calls[0]["provider"] == "custom"
    assert calls[0]["model"] == "glm-5.1"
    assert calls[0]["task"] == "reviewer_bakeoff"
    assert scores[0].status == "pass"
    assert scores[0].artifact_path
    assert Path(scores[0].artifact_path).exists()
    assert "lanes.jsonl" in Path(scores[0].artifact_path).read_text()
    assert load_scores(scorecard)[0].status == "pass"


def test_live_bakeoff_provider_error_is_scored_quality_failed(tmp_path: Path):
    packet = BenchmarkPacket(
        packet_id="p5",
        task_family="plan_review",
        artifact_name="plan.md",
        artifact_content="rollback missing",
        rubric=["check rollback"],
        expected_issue_markers=["rollback"],
    )
    candidate = ReviewerCandidate(provider="custom", model="broken")

    def boom(**kwargs):
        raise RuntimeError("provider unavailable")

    scores = run_live_bakeoff("live-error", [packet], tmp_path / "scorecard.jsonl", [candidate], llm_call=boom)

    assert scores[0].status == "quality_failed"
    assert scores[0].fabricated_claims is True
    assert "adversarial_review" in scores[0].demoted_for_roles


def test_parse_candidate_accepts_budget_and_tool_flag():
    candidate = parse_candidate("custom/glm-5.1,cheap,true")

    assert candidate.provider == "custom"
    assert candidate.model == "glm-5.1"
    assert candidate.budget_class == "cheap"
    assert candidate.tool_capable is True


def test_swarm_telemetry_flags_invalid_timestamp_order(tmp_path: Path):
    ledger = SwarmRunLedger("timestamp-proof", tmp_path)
    record = LaneRecord(
        run_id="timestamp-proof",
        lane_id="bad-time",
        role="reviewer",
        task="timestamp validation",
        start_time="2026-07-02T15:50:28+00:00",
        end_time="2026-07-02T15:46:00+00:00",
        duration_seconds=25.06,
        status="quality_failed",
    )
    ledger.write_lane(record)
    row = json.loads((tmp_path / "timestamp-proof" / "lanes.jsonl").read_text().strip())

    assert row["telemetry_invalid_time"] is True
    assert row["observed_duration_seconds"] < 0
    assert row["logged_duration_seconds"] == 25.06
    assert row["duration_seconds"] == 25.06
