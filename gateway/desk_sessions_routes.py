"""Desk sessions write-RPC routes — Phase 2 scaffold.

Not yet registered with the gateway router. Phase 5 wires this in (security
review needed first). The gateway today is aiohttp-based; this file declares
the routes in FastAPI's APIRouter style per the desk redesign build plan
(2026-05-29). The Phase 5 integration will either:

  (a) mount this APIRouter behind an ASGI-in-aiohttp adapter, or
  (b) port these stubs to aiohttp `web.RouteTableDef` handlers that match
      the contract documented below.

Either way, the shape of the request/response payloads is the source of
truth that the Desk binary (`shay-desktop-electron/src/main/sessions-rpc.ts`)
will marshal against.

All handlers currently return `501 Not Implemented` JSON envelopes. Each
handler carries a TODO block listing the SQL the Phase 5 implementation
will run against `~/.shay/state.db` (or, where appropriate, the Desk-owned
`sessions-overlay.db` via a privileged IPC bridge).

Security review checklist for Phase 5 wiring:
  - Verify `Authorization: Bearer <API_SERVER_KEY>` is enforced for every
    route here, the same way the existing `/v1/chat/completions` is gated
    in `gateway/platforms/api_server.py`.
  - Validate session_id strings against the project's UUID/slug allowlist
    before touching sqlite — no raw string interpolation.
  - Confirm `mode` payloads are coerced to the {"chat","cowork","code"}
    enum before write.
  - Rate-limit `searchFuzzy` and `delete` per loopback caller.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

try:
    from fastapi import APIRouter, HTTPException, Query
    from fastapi.responses import JSONResponse
except ImportError:  # pragma: no cover - FastAPI is optional today
    APIRouter = None  # type: ignore[assignment,misc]
    HTTPException = None  # type: ignore[assignment,misc]
    Query = None  # type: ignore[assignment,misc]
    JSONResponse = None  # type: ignore[assignment,misc]

try:
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover - pydantic ships with FastAPI today
    BaseModel = None  # type: ignore[assignment,misc]
    Field = None  # type: ignore[assignment,misc]


# Typed payload schemas — mirrors the TypeScript contract in
# `shay-desktop-electron/src/main/sessions-rpc.ts`. Each PATCH body is
# coerced through one of these models in Phase 5 before any sqlite write,
# so the wire shape and the overlay-db column shape stay in lock-step.
SessionMode = Literal["chat", "cowork", "code"]


if BaseModel is not None:

    class RenameBody(BaseModel):
        custom_title: Optional[str] = Field(
            default=None, alias="customTitle", max_length=200
        )

    class PinBody(BaseModel):
        pinned: bool

    class ArchiveBody(BaseModel):
        archived: bool

    class SetProjectBody(BaseModel):
        project_id: Optional[str] = Field(
            default=None, alias="projectId", max_length=128
        )

    class SetModeBody(BaseModel):
        mode: Optional[SessionMode] = None

    class ForkBody(BaseModel):
        at_message_id: Optional[str] = Field(
            default=None, alias="atMessageId", max_length=128
        )

else:  # pragma: no cover - typed stub for environments without pydantic
    RenameBody = dict  # type: ignore[assignment,misc]
    PinBody = dict  # type: ignore[assignment,misc]
    ArchiveBody = dict  # type: ignore[assignment,misc]
    SetProjectBody = dict  # type: ignore[assignment,misc]
    SetModeBody = dict  # type: ignore[assignment,misc]
    ForkBody = dict  # type: ignore[assignment,misc]


_NOT_IMPLEMENTED_BODY = {
    "error": "NotImplemented",
    "detail": (
        "Desk sessions write-RPC is scaffolded but not wired. "
        "Phase 5 (Admin / MCP / Auth) lands the gateway integration "
        "after a security review of loopback Bearer enforcement."
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
    """Serialize a Pydantic model (v1 or v2) to a plain dict.

    Falls back to returning the value unchanged when pydantic isn't
    available — the stub responses are only used for echoing the received
    payload in 501s, so a plain dict from the FastAPI body parser is fine.
    """
    if model is None:
        return None
    if hasattr(model, "model_dump"):
        return model.model_dump(by_alias=True, exclude_none=True)
    if hasattr(model, "dict"):
        return model.dict(by_alias=True, exclude_none=True)  # pragma: no cover
    return model


def build_router() -> Any:
    """Build the desk sessions APIRouter.

    Returns `None` when FastAPI is not installed in the active Python
    environment. The Phase 5 wiring is responsible for short-circuiting
    when `None` is returned (and likely for installing FastAPI as a hard
    dependency at that point — today the gateway runs on aiohttp).
    """
    if APIRouter is None:
        return None

    router = APIRouter(prefix="/v1/desk/sessions", tags=["desk-sessions"])

    @router.get("")
    async def list_sessions(
        limit: int = Query(default=30, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ):
        """List sessions, merging overlay fields.

        TODO (Phase 5):
            SELECT s.id, s.source, s.started_at, s.ended_at,
                   s.message_count, s.model, s.title
              FROM sessions s
              ORDER BY s.started_at DESC
              LIMIT :limit OFFSET :offset;

        Then LEFT JOIN against the Desk overlay (`session_meta`) on
        `id` to layer on `pinned`, `archived`, `custom_title`,
        `project_id`, `brain_id`, `mode`, `updated_at`.
        """
        return _stub_response("list", {"limit": limit, "offset": offset})

    @router.get("/{session_id}")
    async def get_session(session_id: str):
        """Fetch a single merged session row.

        TODO (Phase 5):
            SELECT * FROM sessions WHERE id = :session_id;
            -- merge overlay fields from session_meta WHERE id = :session_id;
        """
        return _stub_response("get", {"session_id": session_id})

    @router.patch("/{session_id}/rename")
    async def rename_session(session_id: str, body: RenameBody):
        """Rename via custom_title overlay column.

        TODO (Phase 5):
            INSERT INTO session_meta (id, custom_title, updated_at)
            VALUES (:session_id, :custom_title, :now)
            ON CONFLICT(id) DO UPDATE
              SET custom_title = excluded.custom_title,
                  updated_at = excluded.updated_at;
        """
        return _stub_response(
            "rename", {"session_id": session_id, "body": _dump(body)}
        )

    @router.patch("/{session_id}/pin")
    async def pin_session(session_id: str, body: PinBody):
        """Toggle pinned overlay column.

        TODO (Phase 5):
            INSERT INTO session_meta (id, pinned, updated_at)
            VALUES (:session_id, :pinned, :now)
            ON CONFLICT(id) DO UPDATE
              SET pinned = excluded.pinned,
                  updated_at = excluded.updated_at;
        """
        return _stub_response(
            "pin", {"session_id": session_id, "body": _dump(body)}
        )

    @router.patch("/{session_id}/archive")
    async def archive_session(session_id: str, body: ArchiveBody):
        """Toggle archived overlay column.

        TODO (Phase 5):
            INSERT INTO session_meta (id, archived, updated_at)
            VALUES (:session_id, :archived, :now)
            ON CONFLICT(id) DO UPDATE
              SET archived = excluded.archived,
                  updated_at = excluded.updated_at;
        """
        return _stub_response(
            "archive", {"session_id": session_id, "body": _dump(body)}
        )

    @router.patch("/{session_id}/project")
    async def set_project(session_id: str, body: SetProjectBody):
        """Set project_id overlay column.

        TODO (Phase 5):
            INSERT INTO session_meta (id, project_id, updated_at)
            VALUES (:session_id, :project_id, :now)
            ON CONFLICT(id) DO UPDATE
              SET project_id = excluded.project_id,
                  updated_at = excluded.updated_at;
        """
        return _stub_response(
            "setProject", {"session_id": session_id, "body": _dump(body)},
        )

    @router.patch("/{session_id}/mode")
    async def set_mode(session_id: str, body: SetModeBody):
        """Set mode overlay column.

        TODO (Phase 5):
            -- coerce body['mode'] into {'chat','cowork','code'} first
            INSERT INTO session_meta (id, mode, updated_at)
            VALUES (:session_id, :mode, :now)
            ON CONFLICT(id) DO UPDATE
              SET mode = excluded.mode,
                  updated_at = excluded.updated_at;
        """
        return _stub_response(
            "setMode", {"session_id": session_id, "body": _dump(body)},
        )

    @router.get("/search/fuzzy")
    async def search_fuzzy(
        q: str = Query(..., min_length=1, max_length=200),
        limit: int = Query(default=20, ge=1, le=100),
    ):
        """Fuzzy search across sessions, FTS-backed where available.

        TODO (Phase 5):
            -- Try FTS first:
            SELECT DISTINCT m.session_id, s.title, s.started_at, s.source,
                   s.message_count, s.model,
                   snippet(messages_fts, 0, '<<', '>>', '...', 40) AS snippet
              FROM messages_fts
              JOIN messages m ON m.id = messages_fts.rowid
              JOIN sessions s ON s.id = m.session_id
              WHERE messages_fts MATCH :sanitized_q
              ORDER BY rank
              LIMIT :limit;

            -- Fallback: substring match against session_meta.custom_title
            -- and sessions.title for the most recent 500 rows.
        """
        return _stub_response("searchFuzzy", {"q": q, "limit": limit})

    @router.post("/{session_id}/fork")
    async def fork_session(session_id: str, body: Optional[ForkBody] = None):
        """Fork a session at an optional message id.

        TODO (Phase 5, depends on Phase 3 backend fork primitive):
            -- 1. Allocate new session id, copy `sessions` row.
            -- 2. Copy `messages` up to and including :at_message_id
            --    (or all messages if at_message_id is null).
            -- 3. Carry overlay fields (project_id, brain_id, mode) onto
            --    the new session_meta row, drop pinned/archived flags.
            -- 4. Emit `sessions.changed` SSE event for both rows.
        """
        return _stub_response(
            "fork", {"session_id": session_id, "body": _dump(body) if body else {}},
        )

    @router.delete("/{session_id}")
    async def delete_session(session_id: str):
        """Delete a session everywhere.

        TODO (Phase 5):
            BEGIN;
              DELETE FROM session_meta WHERE id = :session_id;
              DELETE FROM messages_fts WHERE rowid IN (
                SELECT id FROM messages WHERE session_id = :session_id
              );
              DELETE FROM messages WHERE session_id = :session_id;
              DELETE FROM sessions WHERE id = :session_id;
            COMMIT;
        """
        return _stub_response("delete", {"session_id": session_id})

    return router


# Eagerly construct the router so importers can `from
# gateway.desk_sessions_routes import router` once Phase 5 wires it in.
# `None` is a sentinel meaning "FastAPI unavailable in this environment".
router = build_router()


__all__ = ["build_router", "router"]
