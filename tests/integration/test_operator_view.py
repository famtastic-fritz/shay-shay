"""Subprocess-shaped integration checks for the operator view contract."""

from __future__ import annotations

import argparse
import json

from shay_cli.kanban_db import connect, create_task, record_run_event


def _args(action: str, task_id: str, *, machine: bool = True, after: int = 0):
    return argparse.Namespace(
        operator_action=action,
        task_id=task_id,
        board=None,
        json=machine,
        after=after,
        actor="integration-test",
    )


def test_operator_view_projects_same_durable_task_and_event_cursor(monkeypatch, tmp_path, capsys):
    from plugins.operator_view import commands

    db = tmp_path / "profile with spaces" / "kanban.db"
    db.parent.mkdir(parents=True)
    with connect(db) as conn:
        task_id = create_task(
            conn,
            title="Unicode ✓ operator task",
            body="body",
            created_by="test",
            workspace_kind="scratch",
            idempotency_key="operator-integration-1",
        )
        record_run_event(conn, task_id, "operator_test", {"unicode": "✓"})

    monkeypatch.setattr(commands, "kanban_db_path", lambda board=None: db)
    assert commands.operator_command(_args("inspect", task_id)) == 0
    inspect_payload = json.loads(capsys.readouterr().out)
    assert inspect_payload["task_id"] == task_id
    assert inspect_payload["title"] == "Unicode ✓ operator task"

    assert commands.operator_command(_args("events", task_id, after=0)) == 0
    events_payload = json.loads(capsys.readouterr().out)
    assert events_payload["task_id"] == task_id
    assert events_payload["events"]
    assert any(event["kind"] == "operator_test" for event in events_payload["events"])
    assert "\\x1b" not in json.dumps(events_payload)


def test_missing_task_has_stable_machine_error_and_nonzero_code(monkeypatch, tmp_path, capsys):
    from plugins.operator_view import commands

    db = tmp_path / "kanban.db"
    with connect(db):
        pass
    monkeypatch.setattr(commands, "kanban_db_path", lambda board=None: db)

    assert commands.operator_command(_args("inspect", "missing-task")) == commands.EXIT_NOT_FOUND
    payload = json.loads(capsys.readouterr().out)
    assert payload["code"] == "task_not_found"
    assert payload["operator_schema"] == commands.OPERATOR_SCHEMA
