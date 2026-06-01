"""Desk background-tasks routes — Phase 3 scaffold.

NOT YET REGISTERED with the gateway router. The Phase 3 Desk client
(`shay-desktop-electron/src/main/domains/tasks.ts`) treats 501 responses
from `/v1/tasks` as a signal to fall back to its local kanban + cronjob
enumeration so the right-rail tray still has signal during the rollout.

This file declares the routes in FastAPI's `APIRouter` style per the
desk redesign build plan (2026-05-29). Phase 5 either:

  (a) mounts this APIRouter behind an ASGI-in-aiohttp adapter, or
  (b) ports the stubs to aiohttp `web.RouteTableDef` handlers matching
      the contract documented below.

Either way, the wire shapes are the source of truth that the Desk binary
marshals against.

Security review checklist for Phase 5 wiring:
  - Enforce `Authorization: Bearer <API_SERVER_KEY>` on every route here,
    matching the gating already in place for `/v1/chat/completions`.
  - Validate every `task_id` path param against an opaque token allowlist
    (no raw shell interpolation, no SQL string concat).
  - Rate-limit `pause`, `resume`, `cancel`, `retry` per loopback caller.
  - The SSE `/stream` endpoint must enforce the loopback-only origin
    check and a hard backpressure cap (1 KiB/event, 64 events/s) so a
    runaway producer can't OOM the renderer.

Wire shape (mirror of `BackgroundTask` in src/main/domains/tasks.ts):

    {
      "id": str,
      "source": "kanban" | "cron" | "run" | "agent" | "custom",
      "title": str,
      "detail": str | null,
      "status": (
          "queued" | "running" | "paused" | "input-needed"
        | "completed" | "failed" | "cancelled"
      ),
      "progress": float | null,         # 0..1
      "started_at": int (epoch ms),
      "ended_at": int | null,
      "session_id": str | null,
      "metadata": dict | null,
    }
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Literal, Optional

try:
    from fastapi import APIRouter, HTTPException, Query
    from fastapi.responses import JSONResponse, StreamingResponse
except ImportError:  # pragma: no cover - FastAPI is optional today
    APIRouter = None  # type: ignore[assignment,misc]
    HTTPException = None  # type: ignore[assignment,misc]
    Query = None  # type: ignore[assignment,misc]
    JSONResponse = None  # type: ignore[assignment,misc]
    StreamingResponse = None  # type: ignore[assignment,misc]

try:
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover - pydantic ships with FastAPI today
    BaseModel = None  # type: ignore[assignment,misc]
    Field = None  # type: ignore[assignment,misc]


TaskStatus = Literal[
    "queued",
    "running",
    "paused",
    "input-needed",
    "completed",
    "failed",
    "cancelled",
]


if BaseModel is not None:

    class PingMeBody(BaseModel):
        enabled: bool = Field(default=True)

    class RetryBody(BaseModel):
        with_overrides: Optional[dict] = Field(default=None, alias="overrides")

else:  # pragma: no cover - typed stub for environments without pydantic
    PingMeBody = dict  # type: ignore[assignment,misc]
    RetryBody = dict  # type: ignore[assignment,misc]


_NOT_IMPLEMENTED_BODY = {
    "error": "NotImplemented",
    "detail": (
        "Desk background-tasks aggregator is scaffolded but not wired. "
        "Phase 5 (Admin / MCP / Auth) lands the gateway aggregator after a "
        "security review of loopback Bearer enforcement and SSE backpressure."
    ),
}


def _stub_response(method: str, payload: dict[str, Any] | None = None):
    body = dict(_NOT_IMPLEMENTED_BODY)
    body["method"] = method
    if payload is not None:
        body["received"] = payload
    if JSONResponse is None:
        return body
    return JSONResponse(status_code=501, content=body)


def _dump(model: Any) -> Any:
    if model is None:
        return None
    if hasattr(model, "model_dump"):
        return model.model_dump(by_alias=True, exclude_none=True)
    if hasattr(model, "dict"):
        return model.dict(by_alias=True, exclude_none=True)  # pragma: no cover
    return model


async def _stub_sse_stream() -> AsyncIterator[bytes]:
    """Yield a single SSE comment so the renderer's parser sees a clean close.

    Phase 5 replaces this with the real stream that fans out:
      - `task` events as `{seq, task}` per src/main/domains/tasks.ts shape
      - `counts` events as `{seq, counts}` for the tray summary
      - `done` event when the stream is intentionally closed (no auto-resync)
    """
    yield b": stub stream -- wire in Phase 5\n\n"


def build_router() -> Any:
    """Build the desk tasks APIRouter.

    Returns `None` when FastAPI is not installed in the active Python
    environment. The Phase 5 wiring is responsible for short-circuiting
    when `None` is returned (and likely for installing FastAPI as a hard
    dependency at that point — today the gateway runs on aiohttp).
    """
    if APIRouter is None:
        return None

    router = APIRouter(prefix="/v1/tasks", tags=["desk-tasks"])

    @router.get("")
    async def list_tasks(
        status: Optional[TaskStatus] = Query(default=None),
        limit: int = Query(default=200, ge=1, le=2000),
        offset: int = Query(default=0, ge=0),
    ):
        """Return the merged kanban + cron + run aggregate.

        TODO (Phase 5):
          - Read kanban cards from ~/.shay/state.db
          - Read cron registry from ~/.shay/cronjobs.json
          - Read /v1/runs ledger (in-process) for live SSE-backed runs
          - Merge by task id, sort by `started_at DESC`
          - Apply `status` filter and limit/offset.
        """
        return _stub_response(
            "list", {"status": status, "limit": limit, "offset": offset}
        )

    @router.get("/stream")
    async def stream_tasks():
        """SSE endpoint forwarded by Desk main to the renderer.

        TODO (Phase 5):
          - Subscribe to internal task event bus
          - Coalesce to <= 16ms windows for counts updates
          - Apply 64 events/sec hard ceiling per loopback connection
          - Emit a `: keepalive\\n\\n` every 15s so loadbalancers don't reap.
        """
        if StreamingResponse is None:
            return _stub_response("stream")
        return StreamingResponse(
            _stub_sse_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            status_code=501,
        )

    @router.post("/{task_id}/cancel")
    async def cancel_task(task_id: str):
        """Cancel a queued/running/paused/input-needed task.

        TODO (Phase 5):
            - Validate task_id against active tasks registry.
            - For kanban-derived: mark card status=cancelled, emit event.
            - For cron-derived: skip next scheduled fire.
            - For run-derived: send SIGTERM to the worker, escalate to
              SIGKILL after 5s if it doesn't exit cleanly.
        """
        return _stub_response("cancel", {"task_id": task_id})

    @router.post("/{task_id}/retry")
    async def retry_task(task_id: str, body: RetryBody | None = None):
        """Re-enqueue a failed/cancelled task with optional overrides."""
        return _stub_response(
            "retry", {"task_id": task_id, "body": _dump(body)}
        )

    @router.post("/{task_id}/pause")
    async def pause_task(task_id: str):
        """Pause a running task. No-op for cron-derived rows."""
        return _stub_response("pause", {"task_id": task_id})

    @router.post("/{task_id}/resume")
    async def resume_task(task_id: str):
        """Resume a paused task."""
        return _stub_response("resume", {"task_id": task_id})

    @router.post("/{task_id}/ping-me")
    async def ping_me(task_id: str, body: PingMeBody):
        """Toggle the per-task "notify me on terminal status" preference.

        TODO (Phase 5):
            - Persist to ~/.shay/desktop/task_prefs.json keyed by task_id.
            - On terminal status event, emit a `shay:notifications:emit`
              with category=task, severity derived from final status.
        """
        return _stub_response(
            "ping-me", {"task_id": task_id, "body": _dump(body)}
        )

    return router
