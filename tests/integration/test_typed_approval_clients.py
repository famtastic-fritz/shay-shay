"""Client-neutral typed approval behavior and fail-closed defaults."""

import json

from shay_cli.plugins import PluginManager, resolve_pre_tool_call_decision
from tools.approval import resolve_typed_approval


def test_typed_hook_request_is_resolved_once_and_can_be_approved(monkeypatch):
    manager = PluginManager()
    calls = []

    def hook(**kwargs):
        calls.append(kwargs)
        return {
            "action": "request_approval",
            "effect_class": "local_reversible_write",
            "effect_id": "effect-1",
            "rule_id": "write.once",
        }

    manager._hooks["pre_tool_call"] = [hook]
    monkeypatch.setattr("shay_cli.plugins._plugin_manager", manager)
    decision = resolve_pre_tool_call_decision("write_file", {"path": "x"}, task_id="t", tool_call_id="tc")
    result = resolve_typed_approval(decision, approval_callback=lambda request: "approve", session_key="s")

    assert len(calls) == 1
    assert calls[0]["tool_call_id"] == "tc"
    assert decision["action"] == "request_approval"
    assert result["approved"] is True


def test_typed_hook_errors_and_unknown_decisions_fail_closed(monkeypatch):
    manager = PluginManager()

    def broken(**_kwargs):
        raise RuntimeError("boom")

    manager._hooks["pre_tool_call"] = [broken]
    monkeypatch.setattr("shay_cli.plugins._plugin_manager", manager)
    decision = resolve_pre_tool_call_decision("write_file", {})
    assert decision["action"] == "block"
    assert decision["reason"] == "hook_error"
    assert resolve_typed_approval({"action": "request_approval"})["approved"] is False


def test_block_precedence_over_allow(monkeypatch):
    manager = PluginManager()
    manager._hooks["pre_tool_call"] = [
        lambda **_kwargs: {"action": "allow"},
        lambda **_kwargs: {"action": "block", "message": "hardline", "rule_id": "hardline.root"},
    ]
    monkeypatch.setattr("shay_cli.plugins._plugin_manager", manager)
    decision = resolve_pre_tool_call_decision("terminal", {"command": "rm -rf /"})
    assert decision["action"] == "block"
    assert decision["rule_id"] == "hardline.root"
