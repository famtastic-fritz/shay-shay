"""Desk auth routes — Phase 5 scaffold.

Not yet registered with the gateway router. Phase 5 wires this in after the
provider/fallback chain security review. The gateway today is aiohttp-based;
this file declares the routes in FastAPI's APIRouter style per the desk
redesign build plan (2026-05-29).

All handlers currently return ``501 Not Implemented`` JSON envelopes. The
TypeScript counterpart that drives this surface lives in
``shay-desktop-electron/src/main/domains/auth.ts`` (Phase 5).

Security review checklist for Phase 5 wiring:
  - Enforce ``Authorization: Bearer <API_SERVER_KEY>`` on every route. The
    irony of an auth surface requiring the gateway's own bearer is intended:
    the Desk binary always knows the current API_SERVER_KEY because it owns
    the keychain entry, and renderer-originated requests are proxied through
    the main process.
  - ``generateApiServerKey`` rotates a secret that other consumers (CLI,
    cron jobs) may have cached — the response must include a
    ``previousKeyAcceptedUntil`` timestamp and the supervisor must keep
    accepting the old key for that window.
  - ``add`` / ``remove`` operate on per-provider credentials in the keychain;
    no token material is ever included in responses.
  - ``setFallbackChain`` must validate that each chain entry refers to a
    provider that exists *and* is currently authenticated.
  - ``beginOAuth`` may bind a loopback callback on the Desk binary side; the
    gateway's job is to mint the state token and surface the authorize URL.
"""

from __future__ import annotations

from typing import Any, Optional

try:
    from fastapi import APIRouter
    from fastapi.responses import JSONResponse
except ImportError:  # pragma: no cover - FastAPI is optional today
    APIRouter = None  # type: ignore[assignment,misc]
    JSONResponse = None  # type: ignore[assignment,misc]

try:
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover - pydantic ships with FastAPI today
    BaseModel = None  # type: ignore[assignment,misc]
    Field = None  # type: ignore[assignment,misc]


if BaseModel is not None:

    class AddProviderBody(BaseModel):
        provider: str = Field(max_length=64)
        kind: str = Field(max_length=32)  # "oauth", "api_key", "device_auth", "setup_token"
        token: Optional[str] = Field(default=None, max_length=8192)
        refresh_token: Optional[str] = Field(
            default=None, alias="refreshToken", max_length=8192
        )
        metadata: Optional[dict[str, Any]] = None

    class RemoveProviderBody(BaseModel):
        provider: str = Field(max_length=64)

    class RefreshBody(BaseModel):
        provider: str = Field(max_length=64)

    class SetActiveProviderBody(BaseModel):
        provider: str = Field(max_length=64)

    class FallbackChainBody(BaseModel):
        chain: list[str] = Field(default_factory=list)

    class BeginOAuthBody(BaseModel):
        provider: str = Field(max_length=64)
        scopes: Optional[list[str]] = None

    class FinishOAuthBody(BaseModel):
        provider: str = Field(max_length=64)
        code: Optional[str] = Field(default=None, max_length=4096)
        state: Optional[str] = Field(default=None, max_length=512)
        device_code: Optional[str] = Field(
            default=None, alias="deviceCode", max_length=512
        )

else:  # pragma: no cover
    AddProviderBody = dict  # type: ignore[assignment,misc]
    RemoveProviderBody = dict  # type: ignore[assignment,misc]
    RefreshBody = dict  # type: ignore[assignment,misc]
    SetActiveProviderBody = dict  # type: ignore[assignment,misc]
    FallbackChainBody = dict  # type: ignore[assignment,misc]
    BeginOAuthBody = dict  # type: ignore[assignment,misc]
    FinishOAuthBody = dict  # type: ignore[assignment,misc]


_NOT_IMPLEMENTED_BODY = {
    "error": "NotImplemented",
    "detail": (
        "Desk auth routes are scaffolded but not wired. "
        "Phase 5 (Admin / MCP / Auth) lands the gateway integration after a "
        "security review of provider chain + API_SERVER_KEY rotation."
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
    """Build the desk auth APIRouter.

    Returns ``None`` when FastAPI is unavailable. Phase 5 wiring short-circuits
    on ``None`` and installs FastAPI as a hard dependency.
    """
    if APIRouter is None:
        return None

    router = APIRouter(prefix="/v1/desk/auth", tags=["desk-auth"])

    @router.get("/list")
    async def list_providers():
        """Enumerate configured providers.

        TODO (Phase 5):
            - Return [{ provider, kind, connected, expires_at, scopes }].
            - Never include the token itself.
        """
        return _stub_response("list")

    @router.post("/add")
    async def add_provider(body: AddProviderBody):
        """Persist a new provider credential.

        TODO (Phase 5):
            - Classify token (sk-ant-oat, sk-ant-api, cc-, eyJ).
            - Persist under keychain key matching provider+kind.
            - Emit ``auth.added`` SSE event (no token material in payload).
        """
        return _stub_response("add", _dump(body))

    @router.post("/remove")
    async def remove_provider(body: RemoveProviderBody):
        """Forget a provider credential.

        TODO (Phase 5):
            - Delete keychain entry under provider+kind.
            - If the removed provider was active, fall back to the next
              entry in the fallback chain and emit ``auth.activeChanged``.
        """
        return _stub_response("remove", _dump(body))

    @router.post("/refresh")
    async def refresh_provider(body: RefreshBody):
        """Refresh a provider's access token via its stored refresh token.

        TODO (Phase 5):
            - Look up refresh_token in keychain.
            - POST to provider's token endpoint.
            - Update access_token + expires_at; emit ``auth.refreshed``.
        """
        return _stub_response("refresh", _dump(body))

    @router.post("/setActive")
    async def set_active_provider(body: SetActiveProviderBody):
        """Set the active provider for chat completions.

        TODO (Phase 5):
            - Validate provider is in ``list`` and currently connected.
            - Write to ``~/.shay/active_provider``.
            - Emit ``auth.activeChanged``.
        """
        return _stub_response("setActiveProvider", _dump(body))

    @router.post("/fallback")
    async def set_fallback_chain(body: FallbackChainBody):
        """Set the fallback chain when the active provider errors.

        TODO (Phase 5):
            - Validate every chain entry exists and is connected.
            - Write to ``~/.shay/fallback_chain``.
            - Emit ``auth.fallbackChanged``.
        """
        return _stub_response("setFallbackChain", _dump(body))

    @router.post("/apiServerKey/generate")
    async def generate_api_server_key():
        """Rotate the gateway's loopback bearer key.

        TODO (Phase 5):
            - Generate 32-byte random key, base64url-encode.
            - Persist via keychain (key: ``gateway.api_server_key``).
            - Keep the previous value accepted for ``previousKeyAcceptedUntil``
              (default: 5 minutes) so in-flight clients can roll over.
            - Return { key, previousKeyAcceptedUntil }.
        """
        return _stub_response("generateApiServerKey")

    @router.get("/apiServerKey/status")
    async def get_api_server_key_status():
        """Report the current API_SERVER_KEY metadata.

        TODO (Phase 5):
            - Return { lastRotatedAt, previousKeyAcceptedUntil, fingerprint }.
            - ``fingerprint`` is sha256(key)[0:16] — never the key itself.
        """
        return _stub_response("getApiServerKeyStatus")

    @router.post("/oauth/begin")
    async def begin_oauth(body: BeginOAuthBody):
        """Mint state + return authorize URL or device-code envelope.

        TODO (Phase 5):
            - Provider-specific:
              * Spotify → PKCE: derive verifier+challenge, bind loopback in
                the Desk binary, return { authorizeUrl, state }.
              * Nous   → device_code: POST to provider, return
                { device_code, user_code, verification_uri, interval, expires_in }.
              * Anthropic setup-token → no-op; client paste-back only.
            - Persist verifier/state in a short-lived in-memory map keyed
              by state token; TTL = 10 minutes.
        """
        return _stub_response("beginOAuth", _dump(body))

    @router.post("/oauth/finish")
    async def finish_oauth(body: FinishOAuthBody):
        """Exchange code or poll device_code; persist resulting tokens.

        TODO (Phase 5):
            - Match ``state`` to the in-memory map; fail closed on miss.
            - Provider-specific token exchange.
            - Persist access+refresh in keychain via ``add``.
            - Return { provider, expiresAt, scopes } — never the token.
        """
        return _stub_response("finishOAuth", _dump(body))

    return router


router = build_router()


__all__ = ["build_router", "router"]
