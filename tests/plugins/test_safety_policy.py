"""Focused tests for the bundled typed safety policy."""

import json

from plugins.safety_policy.ledger import DecisionLedger
from plugins.safety_policy.policy import SafetyPolicy, classify_effect


def test_policy_classifies_reads_and_writes(tmp_path):
    ledger = DecisionLedger(tmp_path / "effects.jsonl")
    policy = SafetyPolicy(ledger)

    read = policy.pre_tool_call(tool_name="read_file", args={"path": "notes.txt"}, tool_call_id="tc-read")
    write = policy.pre_tool_call(tool_name="write_file", args={"path": "notes.txt"}, tool_call_id="tc-write")

    assert read["action"] == "allow"
    assert read["effect_class"] == "read"
    assert write["action"] == "request_approval"
    assert write["effect_class"] == "local_reversible_write"


def test_policy_rejects_escape_and_irreversible_effects(tmp_path):
    policy = SafetyPolicy(DecisionLedger(tmp_path / "effects.jsonl"))
    escaped = policy.pre_tool_call(
        tool_name="write_file",
        args={"path": str(tmp_path / "outside" / "x"), "allowed_roots": [str(tmp_path / "inside")]},
        task_id="task-1",
    )
    destructive = policy.pre_tool_call(tool_name="terminal", args={"command": "rm -rf data"})

    assert escaped["action"] == "block"
    assert escaped["reason"] == "path_outside_allowed_root"
    assert destructive["action"] == "block"
    assert destructive["effect_class"] == "destructive_local_write"


def test_policy_ledger_is_redacted_and_replayable(tmp_path):
    path = tmp_path / "effects.jsonl"
    policy = SafetyPolicy(DecisionLedger(path))
    policy.pre_tool_call(
        tool_name="send_message",
        args={"token": "do-not-log"},
        session_id="session-1",
        task_id="task-1",
        tool_call_id="tc-1",
    )

    row = json.loads(path.read_text().splitlines()[0])
    assert row["schema_version"] == 1
    assert row["outcome"] == "denied"
    assert "do-not-log" not in path.read_text()


def test_classify_effect_unknown_tools_as_non_spend_reads():
    assert classify_effect("status", {}) == "read"


def test_payment_without_provider_enforced_ceiling_is_unknown_cost(tmp_path):
    policy = SafetyPolicy(DecisionLedger(tmp_path / "effects.jsonl"))
    decision = policy.pre_tool_call(
        tool_name="charge_customer",
        args={"effect_class": "payment_spend", "max_cost_usd": 1},
    )
    assert decision["action"] == "block"
    assert decision["reason"] == "cost_unknown"
