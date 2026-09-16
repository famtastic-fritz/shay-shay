"""Durable adapter for API-visible runs.

The gateway owns transport concerns (HTTP, asyncio and live agent handles),
while this module owns the durable task/run/event projection in Kanban.  It is
deliberately small: the existing :mod:`kanban_db` kernel remains the only
writer for lifecycle transitions and this adapter only binds an external run
identifier to that ledger.
"""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import asdict, dataclass
from typing import Any, Optional

from .kanban_db import (
    Event,
    active_run,
    cancel_run,
    claim_task,
    complete_task,
    connect,
    create_task,
    get_task,
    list_events_after,
    recover_interrupted_runs,
    record_run_event,
    set_run_waiting_for_approval,
    write_txn,
)


@dataclass(frozen=True)
class DurableRun:
    """Stable external-to-Kanban run binding."""

    run_id: str
    task_id: str
    kanban_run_id: Optional[int]
    status: str
    session_id: Optional[str] = None
    model: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    output: Optional[str] = None
    error: Optional[str] = None


def _event_dict(event: Event) -> dict[str, Any]:
    """Serialize an existing ledger event without leaking internal objects."""
    return {
        "id": event.id,
        "task_id": event.task_id,
        "run_id": event.run_id,
        "event": event.kind,
        "payload": event.payload,
        "timestamp": event.created_at,
    }


class KanbanRunAdapter:
    """Project API runs onto the existing durable Kanban ledger.

    ``enabled`` is intentionally a caller decision.  API server compatibility
    mode can keep the historical process-memory implementation while this
    adapter is exercised in a feature-flagged rollout.
    """

    def __init__(self, db_path=None, *, board: Optional[str] = None, recover: bool = True):
        self._conn = connect(db_path, board=board)
        if recover:
            recover_interrupted_runs(self._conn, current_pid=os.getpid())

    @property
    def connection(self):
        """Expose the connection for tests and narrowly-scoped API reads."""
        return self._conn

    def close(self) -> None:
        self._conn.close()

    def _binding(self, run_id: str):
        return self._conn.execute(
            "SELECT * FROM kanban_run_bindings WHERE run_id = ?", (run_id,)
        ).fetchone()

    def _binding_for_request(self, request_key: str):
        return self._conn.execute(
            "SELECT * FROM kanban_run_bindings WHERE request_key = ?",
            (request_key,),
        ).fetchone()

    def begin(
        self,
        run_id: str,
        *,
        input_text: str,
        request_key: Optional[str] = None,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
        title: str = "API run",
    ) -> DurableRun:
        """Create or recover one idempotent API run.

        Repeating ``request_key`` returns the original binding and does not
        create another task, run, or event transition.  If a process died
        between task creation and binding insertion, the task's ledger key
        recovers the same row before a new one is attempted.
        """
        if not run_id or not str(run_id).strip():
            raise ValueError("run_id is required")
        request_key = str(request_key or run_id)
        old = self._binding(run_id) or self._binding_for_request(request_key)
        if old:
            return self.snapshot(old["run_id"])

        input_sha = hashlib.sha256((input_text or "").encode("utf-8")).hexdigest()
        task_key = f"api-run:{request_key}"
        task_id = create_task(
            self._conn,
            title=title,
            body=input_text,
            created_by="api_server",
            workspace_kind="scratch",
            idempotency_key=task_key,
            tenant="api_server",
        )
        task = get_task(self._conn, task_id)
        run = active_run(self._conn, task_id)
        if run is None and task and task.status == "ready":
            claim_task(self._conn, task_id, claimer=f"api:{os.getpid()}")
            run = active_run(self._conn, task_id)
        if run is None:
            # A retry can find an existing terminal task; bind to its latest
            # run for honest status rather than claiming it again.
            from .kanban_db import latest_run
            run = latest_run(self._conn, task_id)
        created_at = int(time.time())
        with write_txn(self._conn):
            self._conn.execute(
                """
                INSERT OR IGNORE INTO kanban_run_bindings
                    (run_id, task_id, request_key, session_id, model, input_sha256, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, task_id, request_key, session_id, model, input_sha, created_at),
            )
            self._conn.execute(
                "UPDATE tasks SET worker_pid = ? WHERE id = ? AND status = 'running'",
                (os.getpid(), task_id),
            )
            if run is not None:
                self._conn.execute(
                    "UPDATE task_runs SET worker_pid = ? WHERE id = ? AND ended_at IS NULL",
                    (os.getpid(), int(run.id)),
                )
        return self.snapshot(run_id)

    def snapshot(self, run_id: str) -> DurableRun:
        binding = self._binding(run_id)
        if binding is None:
            raise KeyError(run_id)
        task = get_task(self._conn, binding["task_id"])
        run = active_run(self._conn, binding["task_id"])
        if run is None:
            from .kanban_db import latest_run
            run = latest_run(self._conn, binding["task_id"])
        status = "unknown"
        output = task.result if task else None
        error = None
        updated_at = None
        kanban_id = None
        if run is not None:
            kanban_id = int(run.id)
            status = run.status
            if run.outcome == "completed":
                status = "completed"
            elif run.outcome:
                status = run.outcome
            error = run.error
            updated_at = run.ended_at or run.last_heartbeat_at or run.started_at
        elif task:
            status = task.status
            updated_at = task.completed_at or task.started_at or task.created_at
        return DurableRun(
            run_id=binding["run_id"],
            task_id=binding["task_id"],
            kanban_run_id=kanban_id,
            status=status,
            session_id=binding["session_id"],
            model=binding["model"],
            created_at=binding["created_at"],
            updated_at=updated_at,
            output=output,
            error=error,
        )

    def event(self, run_id: str, kind: str, payload: Optional[dict[str, Any]] = None) -> int:
        binding = self._binding(run_id)
        if binding is None:
            raise KeyError(run_id)
        run = active_run(self._conn, binding["task_id"])
        return record_run_event(
            self._conn, binding["task_id"], kind, payload,
            run_id=(int(run.id) if run else None),
        )

    def events(self, run_id: str, *, cursor: int = 0) -> list[dict[str, Any]]:
        binding = self._binding(run_id)
        if binding is None:
            raise KeyError(run_id)
        return [
            _event_dict(event)
            for event in list_events_after(
                self._conn, binding["task_id"], cursor=int(cursor),
            )
        ]

    def waiting_for_approval(self, run_id: str, *, approval_id: Optional[str] = None) -> bool:
        binding = self._binding(run_id)
        if binding is None:
            return False
        run = active_run(self._conn, binding["task_id"])
        return set_run_waiting_for_approval(
            self._conn, binding["task_id"],
            run_id=(int(run.id) if run else None), approval_id=approval_id,
        )

    def complete(self, run_id: str, *, output: Optional[str] = None, metadata: Optional[dict] = None) -> bool:
        binding = self._binding(run_id)
        if binding is None:
            return False
        # A cancelled/interrupted terminal outcome is immutable.  The legacy
        # kernel permits manual completion of blocked cards, so this adapter
        # must add the run-level single-writer guard before delegating.
        if self.snapshot(run_id).status in {"cancelled", "interrupted"}:
            return False
        run = active_run(self._conn, binding["task_id"])
        return complete_task(
            self._conn, binding["task_id"], result=output,
            summary=output, metadata=metadata,
            expected_run_id=(int(run.id) if run else None),
        )

    def fail(self, run_id: str, *, error: str, metadata: Optional[dict] = None) -> bool:
        binding = self._binding(run_id)
        if binding is None:
            return False
        run = active_run(self._conn, binding["task_id"])
        # ``block_task`` is the existing durable failure transition.  Preserve
        # the error in the run summary/event without inventing completion.
        from .kanban_db import block_task
        return block_task(
            self._conn, binding["task_id"], reason=error,
            expected_run_id=(int(run.id) if run else None),
        )

    def cancel(self, run_id: str, *, reason: Optional[str] = None, actor: str = "api") -> bool:
        binding = self._binding(run_id)
        if binding is None:
            return False
        from .kanban_db import latest_run
        current = active_run(self._conn, binding["task_id"])
        if current is None:
            current = latest_run(self._conn, binding["task_id"])
        return cancel_run(
            self._conn, binding["task_id"],
            run_id=(int(current.id) if current else None),
            reason=reason, actor=actor,
        )

    def recover(self, *, reason: str = "gateway_restart") -> list[int]:
        return recover_interrupted_runs(
            self._conn, current_pid=os.getpid(), reason=reason,
        )


# Short alias used by callers that describe the component as a durable run
# service rather than an adapter.
DurableRunAdapter = KanbanRunAdapter
