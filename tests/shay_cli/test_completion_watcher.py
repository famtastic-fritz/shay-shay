"""Tests for the Completion Watcher / Reconciler (kanban_db.py).

Two required scenarios:

(A) Worker exits without calling kanban_complete but leaves a GREEN gate
    → dispatcher auto-completes the task on the worker's behalf.
    tag: reconciled-from-evidence

(B) Worker calls kanban_complete but the gate is RED
    → dispatcher overrides to blocked.
    tag: self-attested done rejected: gate failed  (D0 gate)
"""

from __future__ import annotations

import os
import secrets
import sys
import time
from pathlib import Path

import pytest

import shay_cli.kanban_db as kb


@pytest.fixture
def kanban_home(tmp_path, monkeypatch):
    """Isolated SHAY_HOME with an empty kanban DB."""
    home = tmp_path / ".shay"
    home.mkdir()
    monkeypatch.setenv("SHAY_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    return home


# ---------------------------------------------------------------------------
# Scenario A: protocol-violation exit + GREEN gate → auto-complete
# ---------------------------------------------------------------------------


def test_completion_watcher_auto_completes_when_gate_green(
    kanban_home, tmp_path, monkeypatch
):
    """Worker exits rc=0 without calling kanban_complete.
    The dispatcher runs the gate; it returns 0 (GREEN) and the workspace has
    real files.  The reconciler should auto-complete the task on behalf of the
    worker, leaving status='done' and a 'reconciled_complete' event.
    """
    import shay_cli.kanban_db as _kb

    # Create a workspace directory with a real file so _gather_workspace_diff
    # finds changes.
    workspace = tmp_path / "ws_green"
    workspace.mkdir()
    (workspace / "output.txt").write_text("done\n")

    # Gate command: always exits 0 (green).
    gate_cmd = f"{sys.executable} -c 'import sys; sys.exit(0)'"
    task_body = f"Do some work.\nHARD GATE: {gate_cmd}"

    conn = kb.connect()
    try:
        tid = kb.create_task(
            conn,
            title="silent-worker",
            assignee="bot",
            body=task_body,
        )
        # Set workspace_path directly via SQL so the reconciler can find the
        # workspace (create_task doesn't resolve scratch workspaces).
        with kb.write_txn(conn):
            conn.execute(
                "UPDATE tasks SET workspace_path = ? WHERE id = ?",
                (str(workspace), tid),
            )

        # Simulate: claim task + mark as running with a fake (dead) PID.
        host_prefix = _kb._claimer_id().split(":", 1)[0]
        lock = f"{host_prefix}:mock-green"
        kb.claim_task(conn, tid, claimer=lock)
        fake_pid = 888881
        kb._set_worker_pid(conn, tid, fake_pid)

        # Record a clean exit for the fake pid (rc=0 = clean exit on POSIX).
        _kb._record_worker_exit(fake_pid, 0)

        # Patch liveness check so the dispatcher thinks the PID is dead.
        original_alive = _kb._pid_alive
        _kb._pid_alive = lambda p: False
        try:
            kb.detect_crashed_workers(conn)
        finally:
            _kb._pid_alive = original_alive

        task = kb.get_task(conn, tid)
        assert task.status == "done", (
            f"Expected task to be auto-completed (done), got status={task.status}"
        )

        events = kb.list_events(conn, tid)
        kinds = [e.kind for e in events]
        assert "reconciled_complete" in kinds, (
            f"Expected 'reconciled_complete' event; got events: {kinds}"
        )
        # The task should NOT be blocked/crashed — it was reconciled.
        assert task.status != "blocked"
        assert task.status != "crashed"

        # Confirm reconciler stashed the id on the function.
        reconciled = getattr(kb.detect_crashed_workers, "_last_reconciled", [])
        assert tid in reconciled, (
            f"Expected {tid!r} in _last_reconciled; got {reconciled}"
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Scenario B: worker calls kanban_complete but gate is RED → override blocked
# ---------------------------------------------------------------------------


def test_d0_gate_overrides_self_attested_done_when_gate_red(kanban_home, monkeypatch):
    """Worker calls kanban_complete (self-attest done) but the HARD GATE fails.
    The D0 gate inside complete_task should detect the RED gate and override
    the task back to blocked, emitting a 'd0_gate_override' event.
    """
    # Gate command: always exits 1 (red).
    gate_cmd = f"{sys.executable} -c 'import sys; sys.exit(1)'"
    task_body = f"Ship something.\nHARD GATE: {gate_cmd}"

    conn = kb.connect()
    try:
        tid = kb.create_task(
            conn,
            title="false-done-worker",
            assignee="bot",
            body=task_body,
        )

        # Claim and start the task so complete_task can transition running→done.
        host_prefix = kb._claimer_id().split(":", 1)[0]
        lock = f"{host_prefix}:mock-red"
        kb.claim_task(conn, tid, claimer=lock)

        # Worker calls complete — but gate will return red.
        result = kb.complete_task(
            conn,
            tid,
            summary="I think I did it",
        )

        # complete_task should return True (the D0 override is internal).
        assert result is True, "complete_task should return True even on D0 override"

        task = kb.get_task(conn, tid)
        assert task.status == "blocked", (
            f"D0 gate should override done→blocked; got status={task.status}"
        )

        events = kb.list_events(conn, tid)
        kinds = [e.kind for e in events]
        assert "d0_gate_override" in kinds, (
            f"Expected 'd0_gate_override' event; got events: {kinds}"
        )

        # Verify the event carries the override tag.
        d0_event = next(e for e in events if e.kind == "d0_gate_override")
        assert d0_event.payload is not None
        assert d0_event.payload.get("gate_result") == "red"
        assert "self-attested done rejected" in d0_event.payload.get("override", "")
    finally:
        conn.close()
