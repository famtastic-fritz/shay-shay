"""R3 restart/replay integration contract for durable API runs."""

from pathlib import Path

from shay_cli.kanban_run_adapter import KanbanRunAdapter


def test_status_and_events_survive_gateway_restart(tmp_path: Path):
    path = tmp_path / "kanban.db"
    gateway = KanbanRunAdapter(path, recover=False)
    run = gateway.begin("run-gateway-restart", input_text="persist me")
    event_id = gateway.event(run.run_id, "tool.started", {"tool": "noop"})
    # A crash/restart can be represented by a worker PID no longer owned by
    # the new process.  The new adapter closes it honestly as interrupted.
    gateway.connection.execute(
        "UPDATE task_runs SET worker_pid = 999999 WHERE id = ?", (run.kanban_run_id,)
    )
    gateway.connection.execute(
        "UPDATE tasks SET worker_pid = 999999 WHERE id = ?", (run.task_id,)
    )
    gateway.close()

    restarted = KanbanRunAdapter(path, recover=True)
    assert restarted.snapshot(run.run_id).status == "interrupted"
    replay = restarted.events(run.run_id, cursor=event_id - 1)
    assert [event["id"] for event in replay] == [event_id, event_id + 1]
    assert replay[-1]["event"] == "interrupted"
    restarted.close()
