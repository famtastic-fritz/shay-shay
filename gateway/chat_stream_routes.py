"""Enhanced-chat SSE route — POST /api/sessions/{session_id}/chat/stream.

This is the gateway endpoint that Hermes Workspace (v2.3+) targets when
``resolveChatBackend()`` selects ``claude-enhanced``. See the Workspace
source at ``src/server/claude-api.ts`` (``streamChat()`` lines 363-459)
and ``src/server/chat-backends.ts`` (lines 19-69) for the consumer
contract. In short:

    Request (JSON body):
        {
          "message":        "<latest user message string>",   # required
          "model":          "<model id>",                     # optional
          "system_message": "<ephemeral system prompt>",      # optional
          "attachments":    [ ... ]                           # optional
        }

    Response (SSE):
        event: assistant.delta
        data: {"delta":"<partial text chunk>"}

        ...many more deltas...

        event: assistant.completed
        data: {"content":"<full text>","session_id":"...","usage":{...}}

The path's ``session_id`` is authoritative — no header negotiation. The
gateway loads prior turns from the session DB so the client only sends
the latest user message.

Phase-5 wiring pattern: aiohttp-native handlers registered onto the
existing aiohttp ``web.Application`` via :func:`register_chat_stream_routes`.
Mirrors ``gateway/desk_tasks_routes.py``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional

try:
    from aiohttp import web
    AIOHTTP_AVAILABLE = True
except ImportError:  # pragma: no cover - aiohttp ships with the gateway
    web = None  # type: ignore[assignment,misc]
    AIOHTTP_AVAILABLE = False


logger = logging.getLogger(__name__)


# Session IDs are opaque tokens minted by the Workspace dashboard /
# Shay's session DB. We allow a generous character set but cap length
# and reject control bytes to prevent header / log injection.
_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_\-.:]{1,128}$")


def _valid_session_id(raw: str) -> bool:
    return bool(raw) and bool(_SESSION_ID_RE.match(raw))


def _sse_frame(event: str, payload: Dict[str, Any]) -> bytes:
    """Encode a single SSE frame: ``event:`` + ``data:`` + blank line.

    The Workspace parser splits on blank lines, so the trailing ``\\n\\n``
    is mandatory. ``data:`` payloads must be a single JSON line.
    """
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {data}\n\n".encode("utf-8")


async def handle_chat_stream(request: "web.Request") -> "web.StreamResponse":
    """POST /api/sessions/{session_id}/chat/stream.

    Emits a stream of ``assistant.delta`` SSE events as the agent
    produces text, then a single ``assistant.completed`` envelope. On
    client disconnect, interrupts the underlying agent so it stops
    burning LLM tokens.
    """
    adapter = request.app.get("api_server_adapter")
    if adapter is None:
        return web.json_response(
            {"error": "gateway adapter unavailable"}, status=503
        )

    auth_err = adapter._check_auth(request)
    if auth_err is not None:
        return auth_err

    session_id = (request.match_info.get("session_id") or "").strip()
    if not _valid_session_id(session_id):
        return web.json_response(
            {"error": "invalid session_id"}, status=400
        )

    try:
        body = await request.json()
    except Exception:
        return web.json_response(
            {"error": "invalid JSON body"}, status=400
        )

    if not isinstance(body, dict):
        return web.json_response(
            {"error": "JSON body must be an object"}, status=400
        )

    user_message = body.get("message")
    if not isinstance(user_message, str) or not user_message.strip():
        return web.json_response(
            {"error": "missing or empty 'message'"}, status=400
        )

    system_prompt = body.get("system_message")
    if system_prompt is not None and not isinstance(system_prompt, str):
        return web.json_response(
            {"error": "'system_message' must be a string"}, status=400
        )

    # ``model`` and ``attachments`` are accepted but not yet routed —
    # the existing /v1/chat/completions ignores per-request model
    # overrides at this layer. Record them so future work has a hook.
    requested_model = body.get("model") or adapter._model_name
    _ = body.get("attachments")  # noqa: F841 — reserved for future use

    # Load prior conversation turns from the session DB. Workspace only
    # sends the latest user message; history is server-side.
    history: List[Dict[str, str]] = []
    try:
        db = adapter._ensure_session_db()
        if db is not None:
            history = db.get_messages_as_conversation(session_id) or []
    except Exception as exc:  # pragma: no cover - DB failures are rare
        logger.warning(
            "chat_stream: failed to load history for %s: %s", session_id, exc
        )
        history = []

    import queue as _q
    stream_q: _q.Queue = _q.Queue()

    def _on_delta(delta: Optional[str]) -> None:
        # ``None`` is the agent's "close display box" sentinel — drop
        # it; we detect end-of-stream via ``agent_task.done()`` instead.
        if delta is not None:
            stream_q.put(delta)

    agent_ref: list = [None]
    agent_task = asyncio.ensure_future(
        adapter._run_agent(
            user_message=user_message,
            conversation_history=history,
            ephemeral_system_prompt=system_prompt,
            session_id=session_id,
            stream_delta_callback=_on_delta,
            agent_ref=agent_ref,
        )
    )

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "X-Shay-Shay-Session-Id": session_id,
    }
    origin = request.headers.get("Origin", "")
    cors = adapter._cors_headers_for_origin(origin) if origin else None
    if cors:
        headers.update(cors)

    response = web.StreamResponse(status=200, headers=headers)
    await response.prepare(request)

    delta_count = 0
    accumulated_parts: List[str] = []
    last_activity = time.monotonic()
    KEEPALIVE_SECONDS = 15.0

    try:
        loop = asyncio.get_running_loop()
        while True:
            try:
                delta = await loop.run_in_executor(
                    None, lambda: stream_q.get(timeout=0.5)
                )
            except _q.Empty:
                if agent_task.done():
                    # Drain anything left in the queue.
                    while True:
                        try:
                            delta = stream_q.get_nowait()
                        except _q.Empty:
                            break
                        if delta is None:
                            break
                        if isinstance(delta, str) and delta:
                            await response.write(
                                _sse_frame("assistant.delta", {"delta": delta})
                            )
                            accumulated_parts.append(delta)
                            delta_count += 1
                    break
                if time.monotonic() - last_activity >= KEEPALIVE_SECONDS:
                    await response.write(b": keepalive\n\n")
                    last_activity = time.monotonic()
                continue

            if delta is None:
                break

            # Tool-progress tuples flow through the same queue in
            # /v1/chat/completions; the enhanced path ignores them per
            # the Workspace consumer contract. We pass them through as
            # forward-compat ``shay.tool.progress`` events anyway.
            if isinstance(delta, tuple) and len(delta) == 2 and delta[0] == "__tool_progress__":
                try:
                    await response.write(
                        _sse_frame("shay.tool.progress", delta[1] or {})
                    )
                except Exception:
                    pass
                last_activity = time.monotonic()
                continue

            if not isinstance(delta, str) or not delta:
                continue

            await response.write(
                _sse_frame("assistant.delta", {"delta": delta})
            )
            accumulated_parts.append(delta)
            delta_count += 1
            last_activity = time.monotonic()

        # Collect the final result + usage from the agent task.
        final_text = "".join(accumulated_parts)
        usage: Dict[str, Any] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }
        effective_session_id = session_id
        try:
            result, agent_usage = await agent_task
            if isinstance(agent_usage, dict):
                usage = agent_usage
            if isinstance(result, dict):
                # Agent may have rotated the session id on compression.
                eff = result.get("session_id")
                if isinstance(eff, str) and eff:
                    effective_session_id = eff
                # Fallback: if no deltas streamed, use the final_response.
                if delta_count == 0:
                    fallback = result.get("final_response") or ""
                    if isinstance(fallback, str):
                        final_text = fallback
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning(
                "chat_stream: agent task failed for %s: %s", session_id, exc
            )

        completed_payload: Dict[str, Any] = {
            "content": final_text,
            "session_id": effective_session_id,
            "usage": {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            "model": requested_model,
        }
        await response.write(
            _sse_frame("assistant.completed", completed_payload)
        )

    except (ConnectionResetError, ConnectionAbortedError,
            BrokenPipeError, OSError, asyncio.CancelledError):
        # Client disconnected — interrupt the agent so it stops
        # making LLM calls, then cancel the wrapper task.
        agent = agent_ref[0] if agent_ref else None
        if agent is not None:
            try:
                agent.interrupt("enhanced-chat client disconnected")
            except Exception:
                pass
        if not agent_task.done():
            agent_task.cancel()
            try:
                await agent_task
            except (asyncio.CancelledError, Exception):
                pass
        logger.info(
            "chat_stream: client disconnected, interrupted agent for %s",
            session_id,
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(
            "chat_stream: unexpected error for %s: %s", session_id, exc,
            exc_info=True,
        )
        try:
            await response.write(
                _sse_frame("error", {"message": str(exc)})
            )
        except Exception:
            pass

    return response


def register_chat_stream_routes(
    app: "web.Application", adapter: Any = None,
) -> None:
    """Mount the enhanced-chat SSE route on ``app``.

    Stores the adapter on ``app["api_server_adapter"]`` so the handler
    can reach ``adapter._check_auth``, ``adapter._ensure_session_db``,
    and ``adapter._run_agent`` without a closure capture.
    """
    if not AIOHTTP_AVAILABLE:
        return
    if adapter is not None:
        app["api_server_adapter"] = adapter
    app.router.add_post(
        "/api/sessions/{session_id}/chat/stream", handle_chat_stream,
    )


__all__ = ["register_chat_stream_routes", "handle_chat_stream"]
