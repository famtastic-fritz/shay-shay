"""Tests for the enhanced-chat SSE route.

Endpoint: POST /api/sessions/{session_id}/chat/stream

Phase-5 wiring landed in ``gateway/chat_stream_routes.py``. These tests
exercise the aiohttp handler in isolation, mocking the adapter's
``_run_agent`` to drive synthetic deltas through the SSE writer.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Tuple

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from gateway import chat_stream_routes as routes
from gateway.config import PlatformConfig
from gateway.platforms.api_server import APIServerAdapter, cors_middleware


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_adapter(api_key: str = "") -> APIServerAdapter:
    extra: Dict[str, Any] = {}
    if api_key:
        extra["key"] = api_key
    config = PlatformConfig(enabled=True, extra=extra)
    return APIServerAdapter(config)


def _install_fake_agent(
    adapter: APIServerAdapter,
    deltas: List[str],
    *,
    final_response: str | None = None,
    raise_exc: Exception | None = None,
) -> Dict[str, Any]:
    """Replace ``adapter._run_agent`` with a stub that fires *deltas*.

    Returns a captures dict tests can inspect after the call.
    """
    captures: Dict[str, Any] = {"calls": []}

    async def fake_run_agent(
        user_message: str,
        conversation_history: List[Dict[str, str]],
        ephemeral_system_prompt: str | None = None,
        session_id: str | None = None,
        stream_delta_callback=None,
        tool_progress_callback=None,
        tool_start_callback=None,
        tool_complete_callback=None,
        agent_ref=None,
        gateway_session_key=None,
    ) -> Tuple[Dict[str, Any], Dict[str, int]]:
        captures["calls"].append({
            "user_message": user_message,
            "history": conversation_history,
            "system": ephemeral_system_prompt,
            "session_id": session_id,
        })
        if agent_ref is not None:
            class _StubAgent:
                def interrupt(self, reason: str = "") -> None:
                    captures.setdefault("interrupts", []).append(reason)
            agent_ref[0] = _StubAgent()

        if raise_exc is not None:
            raise raise_exc

        # Stream deltas with tiny yields so the executor pump can keep up.
        for d in deltas:
            if stream_delta_callback is not None:
                stream_delta_callback(d)
            await asyncio.sleep(0.01)

        result = {
            "final_response": final_response if final_response is not None
            else "".join(deltas),
            "session_id": session_id,
            "completed": True,
        }
        usage = {"input_tokens": 7, "output_tokens": 11, "total_tokens": 18}
        return result, usage

    adapter._run_agent = fake_run_agent  # type: ignore[assignment]
    return captures


def _install_fake_session_db(
    adapter: APIServerAdapter,
    history: List[Dict[str, str]],
) -> None:
    class _StubDB:
        def get_messages_as_conversation(self, sid: str) -> List[Dict[str, str]]:
            return list(history)
    adapter._ensure_session_db = lambda: _StubDB()  # type: ignore[assignment]


def _create_app(adapter: APIServerAdapter) -> web.Application:
    app = web.Application(middlewares=[cors_middleware])
    routes.register_chat_stream_routes(app, adapter)
    return app


def _parse_sse(raw: str) -> List[Tuple[str, Any]]:
    """Parse SSE text into a list of (event_name, data_obj_or_str)."""
    events: List[Tuple[str, Any]] = []
    event_name = "message"
    data_lines: List[str] = []
    for line in raw.split("\n"):
        if line == "":
            if data_lines:
                data_str = "\n".join(data_lines)
                try:
                    payload = json.loads(data_str)
                except Exception:
                    payload = data_str
                events.append((event_name, payload))
            event_name = "message"
            data_lines = []
            continue
        if line.startswith(":"):
            # SSE comment / keepalive — skip.
            continue
        if line.startswith("event:"):
            event_name = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data_lines.append(line[len("data:"):].lstrip())
    return events


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def adapter() -> APIServerAdapter:
    return _make_adapter()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_stream_emits_deltas_and_completed(adapter):
    deltas = ["Hello", ", ", "world", "!"]
    captures = _install_fake_agent(adapter, deltas)
    _install_fake_session_db(adapter, [{"role": "user", "content": "prev"}])

    app = _create_app(adapter)
    async with TestClient(TestServer(app)) as client:
        resp = await client.post(
            "/api/sessions/sess-abc/chat/stream",
            json={"message": "Hi", "system_message": "be terse"},
        )
        assert resp.status == 200
        assert resp.headers.get("Content-Type", "").startswith(
            "text/event-stream"
        )
        body = await resp.text()

    events = _parse_sse(body)
    # At least one delta must have arrived.
    delta_events = [e for e in events if e[0] == "assistant.delta"]
    completed_events = [e for e in events if e[0] == "assistant.completed"]
    assert delta_events, f"expected assistant.delta events, got: {events}"
    assert len(completed_events) == 1, (
        f"expected exactly one assistant.completed, got: {completed_events}"
    )

    # Concatenation of deltas equals the final text.
    streamed = "".join(e[1]["delta"] for e in delta_events)
    assert streamed == "Hello, world!"

    completed = completed_events[0][1]
    assert completed["session_id"] == "sess-abc"
    assert completed["content"] == "Hello, world!"
    assert completed["usage"]["total_tokens"] == 18

    # Adapter received the path session id + the loaded history.
    assert captures["calls"][0]["session_id"] == "sess-abc"
    assert captures["calls"][0]["history"] == [
        {"role": "user", "content": "prev"}
    ]
    assert captures["calls"][0]["user_message"] == "Hi"
    assert captures["calls"][0]["system"] == "be terse"


@pytest.mark.asyncio
async def test_chat_stream_fallback_when_no_deltas(adapter):
    # Agent produces no deltas but returns final_response — the
    # ``assistant.completed`` envelope should carry that fallback content.
    _install_fake_agent(adapter, [], final_response="full answer")
    _install_fake_session_db(adapter, [])

    app = _create_app(adapter)
    async with TestClient(TestServer(app)) as client:
        resp = await client.post(
            "/api/sessions/sess-xyz/chat/stream",
            json={"message": "anything"},
        )
        assert resp.status == 200
        body = await resp.text()

    events = _parse_sse(body)
    delta_events = [e for e in events if e[0] == "assistant.delta"]
    completed_events = [e for e in events if e[0] == "assistant.completed"]
    assert delta_events == []
    assert len(completed_events) == 1
    assert completed_events[0][1]["content"] == "full answer"


@pytest.mark.asyncio
async def test_chat_stream_rejects_missing_message(adapter):
    _install_fake_agent(adapter, [])
    _install_fake_session_db(adapter, [])
    app = _create_app(adapter)
    async with TestClient(TestServer(app)) as client:
        resp = await client.post(
            "/api/sessions/sess-1/chat/stream", json={}
        )
        assert resp.status == 400


@pytest.mark.asyncio
async def test_chat_stream_rejects_invalid_session_id(adapter):
    _install_fake_agent(adapter, [])
    _install_fake_session_db(adapter, [])
    app = _create_app(adapter)
    async with TestClient(TestServer(app)) as client:
        # A space in the path won't even route; use a character outside
        # the allowlist that still routes (e.g., '+').
        resp = await client.post(
            "/api/sessions/bad+id/chat/stream",
            json={"message": "x"},
        )
        assert resp.status == 400


@pytest.mark.asyncio
async def test_chat_stream_enforces_auth_when_key_configured():
    adapter = _make_adapter(api_key="sk-secret")
    _install_fake_agent(adapter, ["ok"])
    _install_fake_session_db(adapter, [])
    app = _create_app(adapter)
    async with TestClient(TestServer(app)) as client:
        # No Authorization header — should 401.
        resp = await client.post(
            "/api/sessions/sess-1/chat/stream",
            json={"message": "x"},
        )
        assert resp.status == 401

        # With the right bearer — should 200.
        resp_ok = await client.post(
            "/api/sessions/sess-1/chat/stream",
            json={"message": "x"},
            headers={"Authorization": "Bearer sk-secret"},
        )
        assert resp_ok.status == 200
        body = await resp_ok.text()
        events = _parse_sse(body)
        assert any(e[0] == "assistant.completed" for e in events)


def test_register_chat_stream_adds_route(adapter):
    app = web.Application()
    routes.register_chat_stream_routes(app, adapter)
    paths = {
        getattr(r, "resource", None) and r.resource.canonical
        for r in app.router.routes()
    }
    assert any(
        p and "/api/sessions" in p and "/chat/stream" in p for p in paths
    )


def test_capabilities_advertises_enhanced_chat(adapter):
    # The capabilities envelope grew an ``enhanced_chat`` feature flag
    # and a ``chat_stream`` endpoint entry so Workspace probes can flip
    # ``enhancedChat: true`` without scraping docs.
    import asyncio as _asyncio

    async def _go():
        # Build a fake aiohttp request just enough for _handle_capabilities.
        from unittest.mock import MagicMock
        req = MagicMock()
        req.headers = {}
        # _check_auth returns None when no key is configured.
        resp = await adapter._handle_capabilities(req)
        return resp

    resp = _asyncio.get_event_loop().run_until_complete(_go()) \
        if not _asyncio.get_event_loop().is_running() \
        else _asyncio.run(_go())
    # web.Response stores body as bytes
    payload = json.loads(resp.body)
    assert payload["features"].get("enhanced_chat") is True
    assert "chat_stream" in payload["endpoints"]
    assert payload["endpoints"]["chat_stream"]["method"] == "POST"
