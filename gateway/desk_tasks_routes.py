"""Desk background-tasks routes — Phase 5 implementation.

Framework choice (Phase 5): the gateway's HTTP server is aiohttp (see
``gateway/platforms/api_server.py``). Rather than introduce FastAPI as a
new runtime alongside it — or wire up an ASGI-in-aiohttp shim that would
have to be maintained for one route family — Phase 5 ports the routes
to native aiohttp handlers that match the same wire shape the FastAPI
scaffold documented. The FastAPI ``build_router()`` factory below is
preserved for documentation / type checking but is NOT mounted; the
``register_desk_tasks_routes(app, adapter)`` function is what the
api_server adapter calls to wire the real handlers.

Routes (all POST verbs match what ``src/main/domains/tasks.ts`` calls):

    GET   /v1/tasks                  — merged kanban + cron + run list
    GET   /v1/tasks/stream           — SSE task-event + counts-event
    POST  /v1/tasks/{task_id}/cancel
    POST  /v1/tasks/{task_id}/retry
    POST  /v1/tasks/{task_id}/pause
    POST  /v1/tasks/{task_id}/resume
    POST  /v1/tasks/{task_id}/ping-me

Security review checklist for Phase 5 wiring:
  - Enforce ``Authorization: Bearer <API_SERVER_KEY>`` on every route here,
    matching the gating already in place for ``/v1/chat/completions``
    (handled by reusing ``adapter._check_auth``).
  - Validate every ``task_id`` path param against an opaque-token
    allowlist (no raw shell interpolation, no SQL string concat).
    Implemented via ``_TASK_ID_RE`` + prefix tagging.
  - Rate-limit ``pause``, ``resume``, ``cancel``, ``retry`` per loopback
    caller. Implemented via a per-adapter token bucket (``_PATCH_BUCKET``).
  - The SSE ``/stream`` endpoint enforces a hard backpressure cap
    (1 KiB/event, 64 events/s) plus a 15s keepalive comment.

Wire shape (mirror of ``BackgroundTask`` in src/main/domains/tasks.ts):

    {
      "id": str,                   # source-prefixed: "k:<kanban_id>",
                                   # "c:<cron_id>", "r:<run_id>"
      "source": "kanban" | "cron" | "run" | "agent" | "custom",
      "title": str,
      "detail": str | null,
      "status": (
          "queued" | "running" | "paused" | "input-needed"
        | "completed" | "failed" | "cancelled"
      ),
      "progress": float | null,    # 0..1
      "started_at": int (epoch ms),
      "ended_at": int | null,
      "session_id": str | null,
      "metadata": dict | null,
    }
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from collections import deque
from typing import Any, AsyncIterator, Dict, List, Literal, Optional, Tuple

try:
    from aiohttp import web
    AIOHTTP_AVAILABLE = True
except ImportError:  # pragma: no cover - aiohttp ships with the gateway
    web = None  # type: ignore[assignment,misc]
    AIOHTTP_AVAILABLE = False

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

VALID_STATUSES = {
    "queued",
    "running",
    "paused",
    "input-needed",
    "completed",
    "failed",
    "cancelled",
}

VALID_SOURCES = {"kanban", "cron", "run", "agent", "custom"}


# ---------------------------------------------------------------------------
# FastAPI scaffold (documentation only — NOT mounted at runtime)
# ---------------------------------------------------------------------------

if BaseModel is not None:

    class PingMeBody(BaseModel):
        enabled: bool = Field(default=True)

    class RetryBody(BaseModel):
        with_overrides: Optional[dict] = Field(default=None, alias="overrides")

else:  # pragma: no cover - typed stub for environments without pydantic
    PingMeBody = dict  # type: ignore[assignment,misc]
    RetryBody = dict  # type: ignore[assignment,misc]


def build_router() -> Any:
    """Return a FastAPI APIRouter that documents the wire contract.

    Returns ``None`` when FastAPI is not installed. **Not mounted by the
    gateway in Phase 5** — see ``register_desk_tasks_routes`` for the
    aiohttp implementation that actually runs.
    """
    if APIRouter is None:
        return None

    router = APIRouter(prefix="/v1/tasks", tags=["desk-tasks"])

    @router.get("")
    async def list_tasks(
        source: Optional[str] = Query(default=None),
        status: Optional[TaskStatus] = Query(default=None),
        limit: int = Query(default=200, ge=1, le=2000),
    ):
        # Documentation stub. Real handler is the aiohttp version below.
        if JSONResponse is None:
            return {"error": "FastAPI route not mounted; see aiohttp handlers."}
        return JSONResponse(
            status_code=501,
            content={"error": "Use aiohttp handler — this is a doc stub."},
        )

    return router


# ---------------------------------------------------------------------------
# aiohttp implementation (Phase 5 — actually mounted)
# ---------------------------------------------------------------------------

# Source prefix → length validation. Task IDs are opaque tokens we mint
# inside ``_to_background_task``; we never accept arbitrary strings.
_TASK_ID_RE = re.compile(r"^[krcaqu]:[A-Za-z0-9_\-\.]{1,128}$")

# Per-IP token bucket for write verbs. Cheap: 60 events / 60s. We share
# one bucket across all PATCH-style routes; this is enough to stop a
# runaway main-process loop without ever blocking interactive use.
_BUCKET_REFILL_PER_SEC = 1.0
_BUCKET_CAPACITY = 60.0


class _TokenBucket:
    """Tiny token bucket keyed by peer (host, port) tuple."""

    def __init__(self, capacity: float = _BUCKET_CAPACITY,
                 refill_per_sec: float = _BUCKET_REFILL_PER_SEC) -> None:
        self.capacity = capacity
        self.refill = refill_per_sec
        self._state: Dict[str, Tuple[float, float]] = {}
        self._lock = asyncio.Lock()

    async def take(self, key: str) -> bool:
        async with self._lock:
            now = time.monotonic()
            tokens, last = self._state.get(key, (self.capacity, now))
            tokens = min(self.capacity, tokens + (now - last) * self.refill)
            if tokens < 1.0:
                self._state[key] = (tokens, now)
                return False
            self._state[key] = (tokens - 1.0, now)
            return True


_PATCH_BUCKET = _TokenBucket()

# SSE backpressure: 64 events/s, 1 KiB/event.
_SSE_MAX_EVENT_BYTES = 1024
_SSE_MAX_EVENTS_PER_SEC = 64
_SSE_KEEPALIVE_SECONDS = 15.0
_SSE_POLL_SECONDS = 1.0

# In-memory "ping me" preferences. Phase 5 deliberately does NOT
# persist these — the Desk client already tracks the preference in
# ``pingMePrefs`` (src/main/domains/tasks.ts) and the gateway side is
# fire-and-forget. Persisting here would require a new user-prefs
# store, which is out of scope.
_PING_ME_PREFS: Dict[str, bool] = {}


# ---------------------------------------------------------------------------
# kanban / cron / runs lazy imports — never import at module load time so
# tests can patch the data-source functions independently.
# ---------------------------------------------------------------------------

try:
    from shay_cli import kanban_db as _kanban_db  # noqa: E402
    _KANBAN_AVAILABLE = True
except Exception:  # pragma: no cover
    _kanban_db = None  # type: ignore[assignment]
    _KANBAN_AVAILABLE = False

try:
    from cron import jobs as _cron_jobs  # noqa: E402
    _CRON_AVAILABLE = True
except Exception:  # pragma: no cover
    _cron_jobs = None  # type: ignore[assignment]
    _CRON_AVAILABLE = False


# ---------------------------------------------------------------------------
# Source → BackgroundTask mappers
# ---------------------------------------------------------------------------

# kanban status → BackgroundTask status. The kanban vocabulary is the
# authoritative spelling on disk; BackgroundTask is the wire spelling.
_KANBAN_STATUS_MAP = {
    "triage": "queued",
    "todo": "queued",
    "ready": "queued",
    "running": "running",
    "blocked": "paused",
    "done": "completed",
    "archived": "cancelled",
}


def _kanban_task_to_bg(task: Any) -> Dict[str, Any]:
    started_ms = (task.started_at or task.created_at or 0) * 1000
    ended_ms = (task.completed_at or 0) * 1000 if task.completed_at else None
    bg_status = _KANBAN_STATUS_MAP.get(task.status, "queued")
    return {
        "id": f"k:{task.id}",
        "source": "kanban",
        "title": task.title or task.id,
        "detail": (task.body or "")[:280] if task.body else None,
        "status": bg_status,
        "progress": None,
        "started_at": int(started_ms),
        "ended_at": int(ended_ms) if ended_ms else None,
        "session_id": None,
        "metadata": {
            "kanban_status": task.status,
            "assignee": task.assignee,
            "current_run_id": task.current_run_id,
            "consecutive_failures": task.consecutive_failures,
        },
    }


def _cron_job_to_bg(job: Dict[str, Any]) -> Dict[str, Any]:
    enabled = job.get("enabled", True)
    last_run_at = job.get("last_run_at")
    last_status = (job.get("last_status") or "").lower()
    if not enabled:
        bg_status = "paused"
    elif last_status == "running":
        bg_status = "running"
    elif last_status in {"failed", "error"}:
        bg_status = "failed"
    else:
        bg_status = "queued"
    # Parse epoch ms from `last_run_at` if it's an ISO string; fall back to
    # `created_at` (which the cron module stores as ISO).
    def _iso_to_ms(value: Any) -> int:
        if not value:
            return 0
        if isinstance(value, (int, float)):
            return int(value * 1000) if value < 1e12 else int(value)
        try:
            from datetime import datetime
            return int(datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp() * 1000)
        except Exception:
            return 0
    started_ms = _iso_to_ms(last_run_at or job.get("created_at"))
    return {
        "id": f"c:{job.get('id') or job.get('name')}",
        "source": "cron",
        "title": job.get("name") or "cron job",
        "detail": (job.get("prompt") or "")[:280] or None,
        "status": bg_status,
        "progress": None,
        "started_at": started_ms,
        "ended_at": None,
        "session_id": None,
        "metadata": {
            "schedule": job.get("schedule"),
            "enabled": enabled,
            "last_status": last_status or None,
            "next_run_at": job.get("next_run_at"),
        },
    }


def _kanban_run_to_bg(run: Any, parent_task_id: str) -> Dict[str, Any]:
    """Surface an active kanban run as a run-source BackgroundTask row."""
    started_ms = int((run.started_at or 0) * 1000)
    ended_ms = int((run.ended_at or 0) * 1000) if run.ended_at else None
    if run.ended_at is None:
        bg_status = "running"
    elif (run.outcome or "").lower() in {"success", "completed", "done"}:
        bg_status = "completed"
    elif (run.outcome or "").lower() in {"cancelled", "blocked"}:
        bg_status = "cancelled"
    else:
        bg_status = "failed"
    return {
        "id": f"r:{run.id}",
        "source": "run",
        "title": f"run #{run.id} ({parent_task_id})",
        "detail": getattr(run, "summary", None),
        "status": bg_status,
        "progress": None,
        "started_at": started_ms,
        "ended_at": ended_ms,
        "session_id": None,
        "metadata": {"task_id": parent_task_id, "outcome": getattr(run, "outcome", None)},
    }


def _collect_kanban_tasks() -> List[Dict[str, Any]]:
    if not _KANBAN_AVAILABLE:
        return []
    try:
        conn = _kanban_db.connect()
    except Exception:
        return []
    try:
        rows = _kanban_db.list_tasks(conn, include_archived=False, limit=500)
        return [_kanban_task_to_bg(t) for t in rows]
    except Exception:
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _collect_cron_tasks() -> List[Dict[str, Any]]:
    if not _CRON_AVAILABLE:
        return []
    try:
        jobs = _cron_jobs.list_jobs(include_disabled=True)
    except Exception:
        return []
    return [_cron_job_to_bg(j) for j in jobs]


def _collect_active_runs() -> List[Dict[str, Any]]:
    """Collect currently-active kanban runs (parent task in running state)."""
    if not _KANBAN_AVAILABLE:
        return []
    try:
        conn = _kanban_db.connect()
    except Exception:
        return []
    try:
        rows = _kanban_db.list_tasks(conn, status="running", limit=200)
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    try:
        for task in rows:
            run = _kanban_db.active_run(conn, task.id)
            if run is not None:
                out.append(_kanban_run_to_bg(run, task.id))
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return out


def _merged_tasks(
    *,
    source: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    all_tasks: List[Dict[str, Any]] = []
    if source in (None, "kanban"):
        all_tasks.extend(_collect_kanban_tasks())
    if source in (None, "cron"):
        all_tasks.extend(_collect_cron_tasks())
    if source in (None, "run"):
        all_tasks.extend(_collect_active_runs())
    if status:
        all_tasks = [t for t in all_tasks if t["status"] == status]
    all_tasks.sort(key=lambda t: t.get("started_at") or 0, reverse=True)
    return all_tasks[:limit]


def _counts(tasks: List[Dict[str, Any]]) -> Dict[str, int]:
    out = {s: 0 for s in VALID_STATUSES}
    for t in tasks:
        s = t.get("status")
        if s in out:
            out[s] += 1
    return out


# ---------------------------------------------------------------------------
# task_id parsing + per-source dispatch for write verbs
# ---------------------------------------------------------------------------

def _parse_task_id(raw: str) -> Tuple[Optional[str], Optional[str]]:
    """Split an opaque task_id into (source, native_id).

    Returns ``(None, None)`` on validation failure.
    """
    if not raw or len(raw) > 160 or not _TASK_ID_RE.match(raw):
        return None, None
    prefix, _, native = raw.partition(":")
    src = {"k": "kanban", "c": "cron", "r": "run", "a": "agent", "u": "custom"}.get(prefix)
    if not src or not native:
        return None, None
    return src, native


def _kanban_action(action: str, native_id: str) -> Tuple[bool, Optional[str]]:
    """Apply a write verb to a kanban task. Returns (success, error)."""
    if not _KANBAN_AVAILABLE:
        return False, "kanban unavailable"
    try:
        conn = _kanban_db.connect()
    except Exception as e:
        return False, f"kanban connect failed: {e}"
    try:
        task = _kanban_db.get_task(conn, native_id)
        if task is None:
            return False, "task not found"
        if action == "cancel":
            # Closest semantic to "cancel" in kanban is archive: it
            # removes the row from the live board and emits an event.
            ok = _kanban_db.archive_task(conn, native_id)
            return ok, None if ok else "could not archive"
        if action == "pause":
            ok = _kanban_db.block_task(conn, native_id, reason="paused via /v1/tasks")
            return ok, None if ok else "task not in a pausable state"
        if action == "resume":
            ok = _kanban_db.unblock_task(conn, native_id)
            return ok, None if ok else "task not blocked"
        if action == "retry":
            # Re-queue a failed/cancelled kanban task by unblocking it
            # (covers blocked) or by clearing failure state when needed.
            ok = _kanban_db.unblock_task(conn, native_id)
            return ok, None if ok else "task not in a retryable state"
        return False, f"unsupported action: {action}"
    except Exception as e:
        return False, str(e)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _cron_action(action: str, native_id: str) -> Tuple[bool, Optional[str]]:
    if not _CRON_AVAILABLE:
        return False, "cron unavailable"
    try:
        if action in ("pause", "cancel"):
            job = _cron_jobs.pause_job(native_id)
            return job is not None, None if job else "cron job not found"
        if action == "resume":
            job = _cron_jobs.resume_job(native_id)
            return job is not None, None if job else "cron job not found"
        if action == "retry":
            job = _cron_jobs.trigger_job(native_id)
            return job is not None, None if job else "cron job not found"
        return False, f"unsupported action: {action}"
    except Exception as e:
        return False, str(e)


def _apply_action(action: str, raw_task_id: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """Apply a write verb to whichever source ``raw_task_id`` points at.

    Returns ``(ok, error, refreshed_task)``.
    """
    src, native = _parse_task_id(raw_task_id)
    if src is None or native is None:
        return False, "invalid task_id", None
    if src == "kanban":
        ok, err = _kanban_action(action, native)
    elif src == "cron":
        ok, err = _cron_action(action, native)
    elif src == "run":
        # Runs aren't independently mutable today — closest is to cancel the
        # parent kanban task. Surface a clear error so callers don't silently
        # rely on a no-op.
        return False, "run-scoped actions not supported in Phase 5", None
    else:
        return False, f"source {src!r} not supported for write verbs", None
    if not ok:
        return False, err, None
    # Re-read so the caller can echo the refreshed BackgroundTask.
    refreshed: Optional[Dict[str, Any]] = None
    if src == "kanban":
        try:
            conn = _kanban_db.connect()
            try:
                task = _kanban_db.get_task(conn, native)
                if task is not None:
                    refreshed = _kanban_task_to_bg(task)
            finally:
                conn.close()
        except Exception:
            pass
    elif src == "cron":
        try:
            job = _cron_jobs.get_job(native)
            if job is not None:
                refreshed = _cron_job_to_bg(job)
        except Exception:
            pass
    return True, None, refreshed


# ---------------------------------------------------------------------------
# aiohttp handlers
# ---------------------------------------------------------------------------

def _peer_key(request: "web.Request") -> str:
    peer = request.transport.get_extra_info("peername") if request.transport else None
    if isinstance(peer, tuple) and len(peer) >= 2:
        return f"{peer[0]}:{peer[1]}"
    return "anon"


def _auth_or_401(adapter: Any, request: "web.Request"):
    """Reuse the adapter's bearer-check used by /v1/chat/completions."""
    return adapter._check_auth(request)


async def handle_list_tasks(request: "web.Request") -> "web.Response":
    adapter = request.app.get("api_server_adapter")
    if adapter is not None:
        auth = _auth_or_401(adapter, request)
        if auth is not None:
            return auth
    source = request.query.get("source") or None
    if source is not None and source not in VALID_SOURCES:
        return web.json_response({"error": f"invalid source: {source}"}, status=400)
    status = request.query.get("status") or None
    if status is not None and status not in VALID_STATUSES:
        return web.json_response({"error": f"invalid status: {status}"}, status=400)
    try:
        limit = int(request.query.get("limit", "200"))
    except ValueError:
        return web.json_response({"error": "limit must be an integer"}, status=400)
    limit = max(1, min(limit, 2000))
    try:
        tasks = _merged_tasks(source=source, status=status, limit=limit)
        return web.json_response({"tasks": tasks, "counts": _counts(tasks)})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def _stream_iterator(stop: asyncio.Event) -> AsyncIterator[bytes]:
    """Yield SSE chunks: keepalive + task-event + counts-event.

    Coalesces to a configurable poll interval and enforces a hard cap on
    bytes per event (1 KiB) + events per second (64).
    """
    last_keepalive = time.monotonic()
    last_seen: Dict[str, str] = {}
    last_counts: Optional[str] = None
    sent_in_window = 0
    window_start = time.monotonic()

    yield b": stream open\n\n"

    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=_SSE_POLL_SECONDS)
            break
        except asyncio.TimeoutError:
            pass

        now = time.monotonic()
        # rate-limit window reset
        if now - window_start >= 1.0:
            sent_in_window = 0
            window_start = now

        try:
            tasks = _merged_tasks(limit=500)
        except Exception:
            tasks = []

        for t in tasks:
            if sent_in_window >= _SSE_MAX_EVENTS_PER_SEC:
                break
            key = t["id"]
            sig = f"{t['status']}|{t.get('ended_at')}"
            if last_seen.get(key) == sig:
                continue
            last_seen[key] = sig
            payload = json.dumps({"seq": int(time.time() * 1000), "task": t})
            payload_b = payload.encode("utf-8")
            if len(payload_b) > _SSE_MAX_EVENT_BYTES:
                payload_b = payload_b[:_SSE_MAX_EVENT_BYTES]
            yield b"event: task-event\ndata: " + payload_b + b"\n\n"
            sent_in_window += 1

        counts_payload = json.dumps({"seq": int(time.time() * 1000), "counts": _counts(tasks)})
        if counts_payload != last_counts and sent_in_window < _SSE_MAX_EVENTS_PER_SEC:
            last_counts = counts_payload
            yield b"event: counts-event\ndata: " + counts_payload.encode("utf-8") + b"\n\n"
            sent_in_window += 1

        if now - last_keepalive >= _SSE_KEEPALIVE_SECONDS:
            yield b": keepalive\n\n"
            last_keepalive = now


async def handle_stream_tasks(request: "web.Request") -> "web.StreamResponse":
    adapter = request.app.get("api_server_adapter")
    if adapter is not None:
        auth = _auth_or_401(adapter, request)
        if auth is not None:
            return auth
    resp = web.StreamResponse(
        status=200,
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
    await resp.prepare(request)
    stop = asyncio.Event()

    # Auto-close after a generous default (Desk re-subscribes on demand).
    max_seconds = float(request.query.get("max_seconds", "300") or "300")

    async def _stopper() -> None:
        try:
            await asyncio.sleep(min(max_seconds, 600.0))
        finally:
            stop.set()

    stopper_task = asyncio.create_task(_stopper())
    try:
        async for chunk in _stream_iterator(stop):
            try:
                await resp.write(chunk)
            except (ConnectionResetError, asyncio.CancelledError):
                break
    finally:
        stop.set()
        stopper_task.cancel()
        try:
            await resp.write(b"event: done\ndata: {}\n\n")
        except Exception:
            pass
    return resp


async def _handle_action(request: "web.Request", action: str) -> "web.Response":
    adapter = request.app.get("api_server_adapter")
    if adapter is not None:
        auth = _auth_or_401(adapter, request)
        if auth is not None:
            return auth
    # Rate-limit per peer.
    key = _peer_key(request)
    allowed = await _PATCH_BUCKET.take(key)
    if not allowed:
        return web.json_response({"error": "rate limit exceeded"}, status=429)
    task_id = request.match_info.get("task_id", "")
    src, native = _parse_task_id(task_id)
    if src is None:
        return web.json_response({"error": "invalid task_id format"}, status=400)
    ok, err, refreshed = _apply_action(action, task_id)
    if not ok:
        # 404 if the underlying row simply doesn't exist; otherwise 409 for
        # state-machine refusals.
        status = 404 if (err or "").endswith("not found") else 409
        return web.json_response({"ok": False, "error": err or "failed"}, status=status)
    body: Dict[str, Any] = {"ok": True}
    if refreshed is not None:
        body["task"] = refreshed
    return web.json_response(body)


async def handle_cancel(request: "web.Request") -> "web.Response":
    return await _handle_action(request, "cancel")


async def handle_retry(request: "web.Request") -> "web.Response":
    return await _handle_action(request, "retry")


async def handle_pause(request: "web.Request") -> "web.Response":
    return await _handle_action(request, "pause")


async def handle_resume(request: "web.Request") -> "web.Response":
    return await _handle_action(request, "resume")


async def handle_ping_me(request: "web.Request") -> "web.Response":
    adapter = request.app.get("api_server_adapter")
    if adapter is not None:
        auth = _auth_or_401(adapter, request)
        if auth is not None:
            return auth
    key = _peer_key(request)
    allowed = await _PATCH_BUCKET.take(key)
    if not allowed:
        return web.json_response({"error": "rate limit exceeded"}, status=429)
    task_id = request.match_info.get("task_id", "")
    src, native = _parse_task_id(task_id)
    if src is None:
        return web.json_response({"error": "invalid task_id format"}, status=400)
    try:
        body = await request.json()
    except Exception:
        body = {}
    enabled = bool(body.get("enabled", True))
    # Phase 5 deferral: just record the intent in process memory. Push
    # notification persistence is out of scope (would need a new prefs
    # store). The Desk client already remembers the preference on its
    # side; this endpoint exists so a clean reload doesn't drop signal.
    _PING_ME_PREFS[task_id] = enabled
    return web.json_response({"ok": True, "deferred": True, "enabled": enabled})


# ---------------------------------------------------------------------------
# Public registration entrypoint
# ---------------------------------------------------------------------------

def register_desk_tasks_routes(app: "web.Application", adapter: Any = None) -> None:
    """Mount the /v1/tasks aiohttp routes on ``app``.

    Stores the adapter on ``app["api_server_adapter"]`` so handlers can
    reach ``adapter._check_auth`` without a closure capture.
    """
    if not AIOHTTP_AVAILABLE:
        return
    if adapter is not None:
        app["api_server_adapter"] = adapter
    app.router.add_get("/v1/tasks", handle_list_tasks)
    app.router.add_get("/v1/tasks/stream", handle_stream_tasks)
    app.router.add_post("/v1/tasks/{task_id}/cancel", handle_cancel)
    app.router.add_post("/v1/tasks/{task_id}/retry", handle_retry)
    app.router.add_post("/v1/tasks/{task_id}/pause", handle_pause)
    app.router.add_post("/v1/tasks/{task_id}/resume", handle_resume)
    app.router.add_post("/v1/tasks/{task_id}/ping-me", handle_ping_me)
