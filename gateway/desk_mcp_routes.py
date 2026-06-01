"""Desk MCP admin routes — Phase 5 scaffold.

Not yet registered with the gateway router. Phase 5 wires this in after the
MCP server inventory + login-flow security review. The gateway today is
aiohttp-based; this file declares the routes in FastAPI's APIRouter style
per the desk redesign build plan (2026-05-29).

All handlers currently return ``501 Not Implemented`` JSON envelopes. The
TypeScript counterpart that drives this surface lives in
``shay-desktop-electron/src/main/domains/mcp.ts`` — keep the wire shapes
in lock-step.

Security review checklist for Phase 5 wiring:
  - Enforce ``Authorization: Bearer <API_SERVER_KEY>`` on every route here,
    matching the existing ``/v1/chat/completions`` gating in
    ``gateway/platforms/api_server.py``.
  - The ``configure`` body may contain free-form environment variables; the
    handler must redact known secret patterns (``*_TOKEN``, ``*_KEY``,
    ``*_SECRET``) before echoing them into logs or events.
  - ``test`` and ``restart`` must rate-limit per server_id to prevent
    runaway loops if the renderer thrashes.
  - ``login`` initiates an OAuth flow inside the gateway process and must
    bind to loopback only — never a public interface.
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

try:
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover - pydantic ships with FastAPI today
    BaseModel = None  # type: ignore[assignment,misc]
    Field = None  # type: ignore[assignment,misc]


if BaseModel is not None:

    class AddServerBody(BaseModel):
        server_id: str = Field(alias="serverId", max_length=128)
        name: str = Field(max_length=200)
        command: Optional[str] = Field(default=None, max_length=2048)
        args: Optional[list[str]] = None
        env: Optional[dict[str, str]] = None
        url: Optional[str] = Field(default=None, max_length=2048)
        transport: Optional[str] = Field(default=None, max_length=32)

    class ConfigureBody(BaseModel):
        name: Optional[str] = Field(default=None, max_length=200)
        command: Optional[str] = Field(default=None, max_length=2048)
        args: Optional[list[str]] = None
        env: Optional[dict[str, str]] = None
        url: Optional[str] = Field(default=None, max_length=2048)
        transport: Optional[str] = Field(default=None, max_length=32)
        enabled: Optional[bool] = None

    class TestBody(BaseModel):
        timeout_ms: Optional[int] = Field(default=None, alias="timeoutMs", ge=1, le=60_000)

    class LoginBody(BaseModel):
        provider: Optional[str] = Field(default=None, max_length=64)
        scopes: Optional[list[str]] = None

else:  # pragma: no cover
    AddServerBody = dict  # type: ignore[assignment,misc]
    ConfigureBody = dict  # type: ignore[assignment,misc]
    TestBody = dict  # type: ignore[assignment,misc]
    LoginBody = dict  # type: ignore[assignment,misc]


_NOT_IMPLEMENTED_BODY = {
    "error": "NotImplemented",
    "detail": (
        "Desk MCP admin routes are scaffolded but not wired. "
        "Phase 5 (Admin / MCP / Auth) lands the gateway integration after a "
        "security review of loopback Bearer enforcement + secret redaction."
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


def build_router() -> Any:
    """Build the desk MCP APIRouter.

    Returns ``None`` when FastAPI is unavailable. Phase 5 wiring short-circuits
    on ``None`` and installs FastAPI as a hard dependency.
    """
    if APIRouter is None:
        return None

    router = APIRouter(prefix="/v1/desk/mcp", tags=["desk-mcp"])

    @router.post("/add")
    async def add_server(body: AddServerBody):
        """Register a new MCP server in the gateway config.

        TODO (Phase 5):
            - Validate ``server_id`` against ``^[a-z0-9][a-z0-9-]{0,62}$``.
            - Append to ``~/.shay/mcp.json`` atomically (tmp + rename).
            - Hot-reload the MCP supervisor without dropping in-flight calls.
        """
        return _stub_response("add", _dump(body))

    @router.delete("/{server_id}")
    async def remove_server(server_id: str):
        """Remove an MCP server.

        TODO (Phase 5):
            - Stop the supervised process.
            - Remove the entry from ``~/.shay/mcp.json``.
            - Emit ``mcp.removed`` SSE event.
        """
        return _stub_response("remove", {"server_id": server_id})

    @router.patch("/{server_id}/configure")
    async def configure_server(server_id: str, body: ConfigureBody):
        """Update an MCP server's configuration.

        TODO (Phase 5):
            - Diff against existing config; restart only when command/args/env
              changed, otherwise apply hot.
            - Redact secrets in the emitted ``mcp.configured`` event.
        """
        return _stub_response(
            "configure", {"server_id": server_id, "body": _dump(body)}
        )

    @router.post("/{server_id}/test")
    async def test_server(server_id: str, body: Optional[TestBody] = None):
        """Run a connectivity probe against an MCP server.

        TODO (Phase 5):
            - Spawn (or attach to running) MCP client.
            - Issue ``initialize`` + ``tools/list`` within timeout_ms.
            - Return summary of latency, tool count, and any handshake error.
        """
        return _stub_response(
            "test", {"server_id": server_id, "body": _dump(body) if body else {}}
        )

    @router.post("/{server_id}/restart")
    async def restart_server(server_id: str):
        """Restart a supervised MCP server.

        TODO (Phase 5):
            - SIGTERM the existing child; wait up to 5s; SIGKILL on timeout.
            - Respawn under the supervisor and emit ``mcp.restarted``.
        """
        return _stub_response("restart", {"server_id": server_id})

    @router.get("/{server_id}/tools")
    async def list_tools(server_id: str):
        """Enumerate the tools exposed by an MCP server.

        TODO (Phase 5):
            - Cached read from the supervisor's last ``tools/list`` response.
            - 404 when the server is unregistered, 503 when not yet handshaken.
        """
        return _stub_response("tools", {"server_id": server_id})

    @router.post("/{server_id}/login")
    async def login(server_id: str, body: Optional[LoginBody] = None):
        """Initiate an OAuth/login flow for an MCP server that requires it.

        TODO (Phase 5):
            - Look up the provider config (Spotify PKCE, Nous device-auth, etc).
            - Bind a loopback callback or return a device_code envelope.
            - Store the resulting token in the OS keychain via the Desk binary.
        """
        return _stub_response(
            "login", {"server_id": server_id, "body": _dump(body) if body else {}}
        )

    @router.get("/{server_id}/login/status")
    async def login_status(server_id: str):
        """Report whether an MCP server has a usable credential.

        TODO (Phase 5):
            - Read from keychain; return { connected, expires_at, scopes }.
            - Never return the token itself.
        """
        return _stub_response("loginStatus", {"server_id": server_id})

    @router.get("/{server_id}/logs")
    async def server_logs(
        server_id: str,
        limit: int = Query(default=200, ge=1, le=2000),
        since: Optional[str] = Query(default=None, max_length=64),
    ):
        """Tail the stdout/stderr log for an MCP server.

        TODO (Phase 5):
            - Read from the supervisor's ring buffer.
            - Support ``since=<iso8601>`` for incremental fetches.
        """
        return _stub_response(
            "logs", {"server_id": server_id, "limit": limit, "since": since}
        )

    return router


router = build_router()


__all__ = ["build_router", "router"]
