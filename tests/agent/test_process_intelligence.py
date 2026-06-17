from __future__ import annotations

import json

from agent import process_intelligence


REQUIRED_FIELDS = set(process_intelligence.REQUIRED_FIELDS)


def test_log_run_creates_required_fields_and_redacts_sensitive_values(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAY_HOME", str(tmp_path / ".shay"))

    payload = {
        "plan_id": "plan-title6",
        "job_id": "job-capability-awareness",
        "task_id": "task-process-intelligence-mvp",
        "parent_job_id": "parent-title6",
        "lane": "process-intelligence",
        "task_name": "Implement process-intelligence MVP",
        "started_at": "2026-06-13T20:15:00Z",
        "ended_at": "2026-06-13T20:18:30Z",
        "instruction_summary": "Capture enough execution metadata to answer what happened and what is still missing.",
        "instruction_text": "Use OPENAI_API_KEY=sk-1234567890abcdefghijklmnop and do not store raw transcripts.",
        "tools_used": ["read_file", "patch", "pytest"],
        "commands_run": [
            "export OPENAI_API_KEY=sk-1234567890abcdefghijklmnop",
            {"command": "pytest tests/shay_cli/test_process.py", "env": {"OPENAI_API_KEY": "sk-1234567890abcdefghijklmnop"}},
        ],
        "files_inspected": ["shay_cli/main.py", "agent/redact.py"],
        "files_changed": ["shay_cli/process.py", "agent/process_intelligence.py"],
        "artifacts_created": ["docs/process-intelligence-mvp.md"],
        "commits_created": [],
        "decisions_made": ["Use JSONL index plus per-run JSON files for the MVP."],
        "assumptions_made": ["Manual JSON ingestion is enough for the first cut."],
        "gaps_opened": ["Automatic runtime capture is not wired yet."],
        "gaps_closed": ["Process run records can now be stored and queried."],
        "validation_results": [
            {"check": "targeted tests", "status": "passed", "message": "relevant process ledger tests green"},
            {"check": "secret handling", "status": "passed", "message": "raw API key not persisted"},
            {"check": "transcript capture", "status": "blocked", "message": "private transcripts remain intentionally out of scope for MVP"},
        ],
        "safety_events": [
            {"type": "redaction", "message": "Sensitive env values were masked before persistence."}
        ],
        "blockers": ["Need future auto-instrumentation from runtime entry points."],
        "outcome": "success",
        "next_actions": ["Wire automatic run emission into live runtime paths."],
        "lessons_learned": ["Redaction must happen before persistence, not after."],
    }

    record = process_intelligence.log_run(payload)

    assert REQUIRED_FIELDS.issubset(record.keys())
    assert record["full_instruction_stored"] is False
    assert record["instruction_hash"]
    assert record["duration_seconds"] == 210.0
    assert record["run_id"].startswith("run-")
    assert any("instruction_text observed for hashing only" in note for note in record["redactions"])
    assert any("commands_run[0]: sensitive text redacted" in note for note in record["redactions"])

    saved_path = process_intelligence.run_record_path(record["run_id"])
    saved_text = saved_path.read_text(encoding="utf-8")
    assert "sk-1234567890abcdefghijklmnop" not in saved_text
    assert "OPENAI_API_KEY=sk-1234567890abcdefghijklmnop" not in saved_text
    assert "[redacted:env:values-not-captured]" in saved_text

    saved_record = json.loads(saved_text)
    assert saved_record["task_name"] == "Implement process-intelligence MVP"
    assert saved_record["commands_run"][1]["env"] == "[redacted:env:values-not-captured]"

    index_text = process_intelligence.ledger_index_path().read_text(encoding="utf-8")
    assert record["run_id"] in index_text
    assert "sk-1234567890abcdefghijklmnop" not in index_text


def test_list_get_latest_and_summary_helpers_work_with_minimal_payload(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAY_HOME", str(tmp_path / ".shay"))

    first = process_intelligence.log_run(
        {
            "run_id": "run-alpha",
            "task_name": "First task",
            "instruction_summary": "first instruction",
            "started_at": "2026-06-13T10:00:00Z",
            "ended_at": "2026-06-13T10:00:05Z",
            "outcome": "success",
            "next_actions": ["Do the second thing."],
        }
    )
    second = process_intelligence.log_run(
        {
            "run_id": "run-bravo",
            "task_name": "Second task",
            "instruction_summary": "second instruction",
            "started_at": "2026-06-13T10:05:00Z",
            "ended_at": "2026-06-13T10:05:12Z",
            "outcome": "blocked",
            "blockers": ["Waiting on runtime integration."],
        }
    )

    records = process_intelligence.list_run_records(limit=10)
    assert [record["run_id"] for record in records] == [second["run_id"], first["run_id"]]
    assert process_intelligence.get_run_record("run-alpha")["task_name"] == "First task"
    assert process_intelligence.latest_run_record()["run_id"] == "run-bravo"

    summary = process_intelligence.render_after_action_report(second)
    assert "what happened:" in summary
    assert "what worked:" in summary
    assert "what failed:" in summary
    assert "next action:" in summary
    assert "improvement recommendation:" in summary


def test_normalized_validation_results_produces_stable_evidence_shape():
    normalized = process_intelligence.normalized_validation_results(
        {
            "outcome": "success",
            "validation_results": [
                {
                    "check": "provider-routing",
                    "status": "passed",
                    "message": "provider route verified",
                    "verifier": "pytest",
                    "artifact_refs": ["tests/test_capabilities_cmd.py"],
                },
                "fallback outcome text",
            ],
        }
    )

    assert normalized[0]["capability_id"] == "provider-routing"
    assert normalized[0]["result_class"] == "success"
    assert normalized[0]["is_verifier_backed"] is True
    assert normalized[0]["artifact_refs"] == ["tests/test_capabilities_cmd.py"]
    assert normalized[1]["summary"] == "fallback outcome text"
    assert normalized[1]["status"] == "success"


def test_run_id_path_traversal_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAY_HOME", str(tmp_path / ".shay"))

    try:
        process_intelligence.log_run(
            {
                "run_id": "../../outside-test",
                "task_name": "Traversal attempt",
                "instruction_summary": "Should fail",
            }
        )
        assert False, "expected traversal run_id to raise ValueError"
    except ValueError as exc:
        assert "run_id" in str(exc)

    assert not (tmp_path / ".shay" / "outside-test.json").exists()

    try:
        process_intelligence.get_run_record("../../outside-test")
        assert False, "expected traversal run_id to raise ValueError"
    except ValueError as exc:
        assert "run_id" in str(exc)
