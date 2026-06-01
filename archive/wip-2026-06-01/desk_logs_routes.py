"""Desk logs routes — Phase 5 scaffold.

Not yet registered with the gateway router. Phase 5 wires this in after the
log-source allowlist + redaction review. The gateway today is aiohttp-based;
this file declares the routes in FastAPI's APIRouter style per the desk
redesign build plan (2026-05-29).

All handlers currently return ``501 Not Implemented`` JSON envelopes. The
TypeScript counterpart that drives this surface lives in
``shay-desktop-electron/src/main/domains/`` (logs domain, Phase 5).

Security review checklist for Phase 5 wiring:
  - Enforce ``Authorization: Bearer <API_SERVER_KEY>`` on every route.
  - The ``/stream`` SSE endpoint must impose a per-loopback-caller concurrency
    cap to prevent runaway file-handle growth.
  - The ``source`` query param must be matched against an allowlist
    (``gateway``, ``mcp.<id>``, ``shay-runner``, …) — never a path traversal
    target.
  - ``history`` and ``stream`` payloads must run through the secret-redaction
    filter shared with the chat transcript writer before leaving the gateway.
"""

from __future__ import annotations

from typing import Any, Optional

try:
    from fastapi import APIRouter, Query
    from fastapi.responses import JSONResponse
except ImportError:  # pragma: no cover - FastAPI is optional today
    APIRouter = None  # type: ignore[assignment,misc]
    Query = None  # type: ignore[assignment,misc]
    JSONResponse = None  # type: ignore[assignment,misc]


_NOT_IMPLEMENTED_BODY = {
    "error": "NotImplemented",
    "detail": (
        "Desk logs routes are scaffolded but not wired. "
        "Phase 5 (Admin / MCP / Auth) lands the gateway integration after a "
        "security review of log-source allowlists + secret redaction."
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


def build_router() -> Any:
    """Build the desk logs APIRouter.

    Returns ``None`` when FastAPI is unavailable. Phase 5 wiring short-circuits
    on ``None`` and installs FastAPI as a hard dependency.
    """
    if APIRouter is None:
        return None

    router = APIRouter(prefix="/v1/desk/logs", tags=["desk-logs"])

    @router.get("/stream")
    async def stream_logs(
        source: Optional[str] = Query(default=None, max_length=128),
        level: Optional[str] = Query(default=None, max_length=16),
    ):
        """Server-Sent Events stream of new log lines.

        TODO (Phase 5):
            - Validate ``source`` against allowlist.
            - Wire to the gateway's structured-log bus (currently emits to
              stderr); fan out via SSE with ``data: <json>`` framing.
            - Apply redaction filter before flush.
            - Return ``text/event-stream`` with periodic ``: ping`` keepalive.
        """
        return _stub_response("stream", {"source": source, "level": level})

    @router.get("/history")
    async def history(
        source: Optional[str] = Query(default=None, max_length=128),
        level: Optional[str] = Query(default=None, max_length=16),
        limit: int = Query(default=200, ge=1, le=2000),
        before: Optional[str] = Query(default=None, max_length=64),
    ):
        """Paginated historical log lines.

        TODO (Phase 5):
            - Read from the rotating log files under ``~/.shay/logs/``.
            - Support ``before=<iso8601>`` for backwards pagination.
            - Apply redaction filter before serialisation.
        """
        return _stub_response(
            "history",
            {"source": source, "level": level, "limit": limit, "before": before},
        )

    @router.get("/sources")
    async def sources():
        """Enumerate registered log sources.

        TODO (Phase 5):
            - Return [{ id, label, kind, last_seen_at, line_count }].
            - Kinds: "gateway", "mcp", "runner", "ipc".
        """
        return _stub_response("sources")

    return router


router = build_router()


__all__ = ["build_router", "router"]
