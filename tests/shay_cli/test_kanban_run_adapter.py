"""Focused R3 tests for the durable API-run adapter."""

import sqlite3
from pathlib import Path

from shay_cli import kanban_db as kb
from shay_cli.kanban_run_adapter import KanbanRunAdapter


def test_api_run_is_idempotent_and_replayable(tmp_path: Path):
    adapter = KanbanRunAdapter(tmp_path / "kanban.db", recover=False)
    first = adapter.begin(
        "run-first", input_text="hello", request_key="request-1", session_id="s1"
    )
    second = adapter.begin(
        "run-retry", input_text="hello", request_key="request-1", session_id="s1"
    )
    assert second.run_id == first.run_id
    assert adapter.connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1
    assert adapter.connection.execute("SELECT COUNT(*) FROM task_runs").fetchone()[0] == 1

    event_id = adapter.event(first.run_id, "message.delta", {"delta": "hi"})
    replay = adapter.events(first.run_id, cursor=event_id - 1)
    assert [event["id"] for event in replay] == [event_id]
    assert replay[0]["event"] == "message.delta"

    assert adapter.complete(first.run_id, output="done")
    assert adapter.complete(first.run_id, output="done") is False
    assert adapter.snapshot(first.run_id).status == "completed"
    adapter.close()


def test_restart_marks_old_active_run_interrupted(tmp_path: Path):
    db_path = tmp_path / "kanban.db"
    first = KanbanRunAdapter(db_path, recover=False)
    run = first.begin("run-restart", input_text="long work")
    # Simulate a process that disappeared while the tool was in flight.
    first.connection.execute(
        "UPDATE task_runs SET worker_pid = 999999 WHERE id = ?", (run.kanban_run_id,)
    )
    first.connection.execute(
        "UPDATE tasks SET worker_pid = 999999 WHERE id = ?", (run.task_id,)
    )
    first.close()

    second = KanbanRunAdapter(db_path, recover=True)
    recovered = second.snapshot(run.run_id)
    assert recovered.status == "interrupted"
    assert recovered.output is None
    events = second.events(run.run_id)
    assert events[-1]["event"] == "interrupted"
    assert events[-1]["payload"]["retry_required"] is True
    # Re-opening is idempotent; it must not append another transition.
    before = len(events)
    assert second.recover() == []
    assert len(second.events(run.run_id)) == before
    second.close()


def test_cancel_is_terminal_and_idempotent(tmp_path: Path):
    adapter = KanbanRunAdapter(tmp_path / "kanban.db", recover=False)
    run = adapter.begin("run-cancel", input_text="stop me")
    assert adapter.cancel(run.run_id, reason="operator stop")
    assert adapter.cancel(run.run_id, reason="operator stop") is True
    assert adapter.snapshot(run.run_id).status == "cancelled"
    assert adapter.complete(run.run_id, output="must not complete") is False
    assert adapter.events(run.run_id)[-1]["event"] == "cancelled"
    adapter.close()


def test_legacy_active_idempotency_duplicates_are_preserved_and_reconciled(tmp_path: Path):
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE tasks (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, body TEXT, assignee TEXT,
            status TEXT NOT NULL, priority INTEGER DEFAULT 0, created_by TEXT,
            created_at INTEGER NOT NULL, started_at INTEGER, completed_at INTEGER,
            workspace_kind TEXT NOT NULL, workspace_path TEXT, claim_lock TEXT,
            claim_expires INTEGER, tenant TEXT, result TEXT, idempotency_key TEXT,
            consecutive_failures INTEGER NOT NULL DEFAULT 0, worker_pid INTEGER,
            last_failure_error TEXT, max_runtime_seconds INTEGER,
            last_heartbeat_at INTEGER, current_run_id INTEGER,
            workflow_template_id TEXT, current_step_key TEXT, skills TEXT,
            max_retries INTEGER)"""
    )
    conn.execute(
        "CREATE TABLE task_events (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT, run_id INTEGER, kind TEXT, payload TEXT, created_at INTEGER)"
    )
    conn.executemany(
        "INSERT INTO tasks(id,title,status,created_at,workspace_kind,idempotency_key) VALUES(?,?,?,?,?,?)",
        [("t_old", "old", "ready", 1, "scratch", "same"),
         ("t_new", "new", "ready", 2, "scratch", "same")],
    )
    conn.commit()
    conn.close()

    opened = kb.connect(path)
    rows = opened.execute(
        "SELECT id,idempotency_key FROM tasks ORDER BY created_at"
    ).fetchall()
    assert rows[0]["id"] == "t_old"
    assert rows[0]["idempotency_key"] == "same"
    assert rows[1]["id"] == "t_new"
    assert rows[1]["idempotency_key"] is None
    audit = opened.execute(
        "SELECT canonical_task_id,duplicate_task_id FROM task_idempotency_reconciliations"
    ).fetchone()
    assert tuple(audit) == ("t_old", "t_new")
    assert kb.reconcile_idempotency_duplicates(opened)["duplicates_reconciled"] == 0
    opened.close()
