"""Focused tests for the opt-in operator-view plugin."""

from __future__ import annotations

import argparse
import json

from shay_cli.plugins import PluginContext, PluginManager, PluginManifest


def test_registers_one_plugin_cli_command_without_touching_global_registry():
    from plugins.operator_view import register

    manager = PluginManager()
    register(PluginContext(PluginManifest(name="operator_view"), manager))

    assert list(manager._cli_commands) == ["operator"]
    command = manager._cli_commands["operator"]
    assert command["plugin"] == "operator_view"
    assert callable(command["setup_fn"])
    assert command["handler_fn"].__name__ == "run_operator_command"


def test_operator_parser_exposes_composed_actions_and_json_flag():
    from plugins.operator_view.commands import register_cli

    parser = argparse.ArgumentParser()
    register_cli(parser)
    args = parser.parse_args(["--json", "events", "task-1", "--after", "4"])

    assert args.operator_action == "events"
    assert args.task_id == "task-1"
    assert args.after == 4
    assert args.json is True


def test_operator_machine_output_is_canonical_and_missing_usage_is_not_zero(capsys):
    from plugins.operator_view.commands import _decorate_task, _json_dump

    _json_dump(_decorate_task({
        "object": "shay.task",
        "task_id": "task-1",
        "status": "running",
        "run": {"run_id": 8},
    }))
    out = capsys.readouterr().out
    assert "\\x1b" not in out
    payload = json.loads(out)
    assert payload["run"]["provider"] is None
    assert payload["run"]["model"] is None
    assert payload["run"]["usage"] is None
    assert payload["file_changes"]["available"] is False
    assert payload["typed_effect"]["available"] is False


def test_disabled_plugin_status_is_truthful(monkeypatch):
    from plugins.operator_view.commands import bundled_plugin_status

    monkeypatch.setattr("shay_cli.plugins._get_enabled_plugins", lambda: set())
    status = bundled_plugin_status()
    assert status["installed"] is True
    assert status["enabled"] is False
    assert status["available"] is False
    assert "disabled by default" in status["reason"]
