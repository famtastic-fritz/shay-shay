"""Tests for the Desk background-tasks routes (/v1/tasks).

Phase 5 implementation lives in ``gateway/desk_tasks_routes.py``. These
tests exercise the aiohttp handlers in isolation, the same way
``test_api_server_jobs.py`` covers the cron API.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from gateway.config import PlatformConfig
from gateway.platforms.api_server import APIServerAdapter, cors_middleware
from gateway import desk_tasks_routes as routes

_MOD = "gateway.desk_tasks_routes"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_adapter(api_key: str = "") -> APIServerAdapter:
    extra = {}
    if api_key:
        extra["key"] = api_key
    config = PlatformConfig(enabled=True, extra=extra)
    return APIServerAdapter(config)


def _create_app(adapter: APIServerAdapter) -> web.Application:
    app = web.Application(middlewares=[cors_middleware])
    routes.register_desk_tasks_routes(app, adapter)
    return app


def _fake_kanban_task(
    *,
    task_id: str = "kanban-001",
    title: str = "Fix the thing",
    status: str = "ready",
    body: str | None = "do it",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=task_id,
        title=title,
        body=body,
        assignee="claude",
        status=status,
        priority=0,
        created_by="fritz",
        created_at=1_700_000_000,
        started_at=None,
        completed_at=None,
        workspace_kind="git",
        workspace_path=None,
        claim_lock=None,
        claim_expires=None,
        tenant=None,
        result=None,
        idempotency_key=None,
        consecutive_failures=0,
        worker_pid=None,
        last_failure_error=None,
        max_runtime_seconds=None,
        last_heartbeat_at=None,
        current_run_id=None,
        workflow_template_id=None,
        current_step_key=None,
        skills=None,
        max_retries=None,
        required_tools=None,
    )


SAMPLE_CRON_JOB = {
    "id": "aabbccddeeff",
    "name": "nightly",
    "schedule": "0 2 * * *",
    "prompt": "summarize",
    "enabled": True,
    "deliver": "local",
    "last_status": None,
    "last_run_at": None,
}


@pytest.fixture
def adapter():
    return _make_adapter()


@pytest.fixture
def auth_adapter():
    return _make_adapter(api_key="sk-secret")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class TestAuth:
    @pytest.mark.asyncio
    async def test_no_auth_when_key_required_returns_401(self, auth_adapter):
        app = _create_app(auth_adapter)
        async with TestClient(TestServer(app)) as cli:
            resp = await cli.get("/v1/tasks")
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_bad_bearer_returns_401(self, auth_adapter):
        app = _create_app(auth_adapter)
        async with TestClient(TestServer(app)) as cli:
            resp = await cli.get(
                "/v1/tasks",
                headers={"Authorization": "Bearer nope"},
            )
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_valid_bearer_empty_state(self, auth_adapter):
        app = _create_app(auth_adapter)
        async with TestClient(TestServer(app)) as cli:
            with patch(f"{_MOD}._KANBAN_AVAILABLE", False), \
                 patch(f"{_MOD}._CRON_AVAILABLE", False):
                resp = await cli.get(
                    "/v1/tasks",
                    headers={"Authorization": "Bearer sk-secret"},
                )
                assert resp.status == 200
                data = await resp.json()
                assert data["tasks"] == []
                # counts dict has all statuses with zero values
                assert all(v == 0 for v in data["counts"].values())


# ---------------------------------------------------------------------------
# GET /v1/tasks — list merge
# ---------------------------------------------------------------------------

class TestListTasks:
    @pytest.mark.asyncio
    async def test_merges_kanban_and_cron(self, adapter):
        app = _create_app(adapter)
        fake_conn = MagicMock()
        kanban_db_mock = MagicMock()
        kanban_db_mock.connect.return_value = fake_conn
        kanban_db_mock.list_tasks.return_value = [
            _fake_kanban_task(task_id="kanban-001", status="running"),
        ]
        kanban_db_mock.active_run.return_value = None
        cron_mock = MagicMock()
        cron_mock.list_jobs.return_value = [SAMPLE_CRON_JOB]

        async with TestClient(TestServer(app)) as cli:
            with patch(f"{_MOD}._KANBAN_AVAILABLE", True), \
                 patch(f"{_MOD}._kanban_db", kanban_db_mock), \
                 patch(f"{_MOD}._CRON_AVAILABLE", True), \
                 patch(f"{_MOD}._cron_jobs", cron_mock):
                resp = await cli.get("/v1/tasks")
                assert resp.status == 200
                data = await resp.json()
                ids = {t["id"] for t in data["tasks"]}
                assert "k:kanban-001" in ids
                assert "c:aabbccddeeff" in ids
                # the kanban task is running, cron job is queued
                assert data["counts"]["running"] >= 1

    @pytest.mark.asyncio
    async def test_filter_by_source(self, adapter):
        app = _create_app(adapter)
        kanban_db_mock = MagicMock()
        kanban_db_mock.connect.return_value = MagicMock()
        kanban_db_mock.list_tasks.return_value = [_fake_kanban_task()]
        kanban_db_mock.active_run.return_value = None
        cron_mock = MagicMock()
        cron_mock.list_jobs.return_value = [SAMPLE_CRON_JOB]

        async with TestClient(TestServer(app)) as cli:
            with patch(f"{_MOD}._KANBAN_AVAILABLE", True), \
                 patch(f"{_MOD}._kanban_db", kanban_db_mock), \
                 patch(f"{_MOD}._CRON_AVAILABLE", True), \
                 patch(f"{_MOD}._cron_jobs", cron_mock):
                resp = await cli.get("/v1/tasks?source=cron")
                data = await resp.json()
                sources = {t["source"] for t in data["tasks"]}
                assert sources == {"cron"}

    @pytest.mark.asyncio
    async def test_invalid_status_400(self, adapter):
        app = _create_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            resp = await cli.get("/v1/tasks?status=garbage")
            assert resp.status == 400


# ---------------------------------------------------------------------------
# PATCH-style action verbs
# ---------------------------------------------------------------------------

class TestActions:
    @pytest.mark.asyncio
    async def test_cancel_kanban_task(self, adapter):
        app = _create_app(adapter)
        kanban_db_mock = MagicMock()
        kanban_db_mock.connect.return_value = MagicMock()
        # On apply: get_task returns the task, archive_task returns True
        task_obj = _fake_kanban_task(task_id="kanban-001", status="ready")
        kanban_db_mock.get_task.side_effect = [
            task_obj,  # initial lookup inside _kanban_action
            _fake_kanban_task(task_id="kanban-001", status="archived"),  # re-read
        ]
        kanban_db_mock.archive_task.return_value = True

        async with TestClient(TestServer(app)) as cli:
            with patch(f"{_MOD}._KANBAN_AVAILABLE", True), \
                 patch(f"{_MOD}._kanban_db", kanban_db_mock):
                resp = await cli.post("/v1/tasks/k:kanban-001/cancel")
                assert resp.status == 200
                data = await resp.json()
                assert data["ok"] is True
                assert data["task"]["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_unknown_kanban_task_404(self, adapter):
        app = _create_app(adapter)
        kanban_db_mock = MagicMock()
        kanban_db_mock.connect.return_value = MagicMock()
        kanban_db_mock.get_task.return_value = None
        async with TestClient(TestServer(app)) as cli:
            with patch(f"{_MOD}._KANBAN_AVAILABLE", True), \
                 patch(f"{_MOD}._kanban_db", kanban_db_mock):
                resp = await cli.post("/v1/tasks/k:does-not-exist/cancel")
                assert resp.status == 404
                data = await resp.json()
                assert data["ok"] is False

    @pytest.mark.asyncio
    async def test_invalid_task_id_format_400(self, adapter):
        app = _create_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            resp = await cli.post("/v1/tasks/no-prefix/cancel")
            assert resp.status == 400

    @pytest.mark.asyncio
    async def test_cron_pause(self, adapter):
        app = _create_app(adapter)
        cron_mock = MagicMock()
        cron_mock.pause_job.return_value = dict(SAMPLE_CRON_JOB, enabled=False)
        cron_mock.get_job.return_value = dict(SAMPLE_CRON_JOB, enabled=False)
        async with TestClient(TestServer(app)) as cli:
            with patch(f"{_MOD}._CRON_AVAILABLE", True), \
                 patch(f"{_MOD}._cron_jobs", cron_mock):
                resp = await cli.post("/v1/tasks/c:aabbccddeeff/pause")
                assert resp.status == 200
                data = await resp.json()
                assert data["ok"] is True
                assert data["task"]["status"] == "paused"

    @pytest.mark.asyncio
    async def test_ping_me_deferred(self, adapter):
        app = _create_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            resp = await cli.post(
                "/v1/tasks/k:kanban-001/ping-me",
                json={"enabled": True},
            )
            assert resp.status == 200
            data = await resp.json()
            assert data["ok"] is True
            assert data["deferred"] is True
            assert data["enabled"] is True
            assert routes._PING_ME_PREFS.get("k:kanban-001") is True


# ---------------------------------------------------------------------------
# SSE stream — light smoke test (just confirm it streams an open marker)
# ---------------------------------------------------------------------------

class TestStream:
    @pytest.mark.asyncio
    async def test_stream_opens_and_emits_counts(self, adapter):
        app = _create_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            with patch(f"{_MOD}._KANBAN_AVAILABLE", False), \
                 patch(f"{_MOD}._CRON_AVAILABLE", False):
                # Short max_seconds keeps the test fast.
                async with cli.get("/v1/tasks/stream?max_seconds=2") as resp:
                    assert resp.status == 200
                    # Drain a few chunks; the first is the open comment, the
                    # next batch carries the counts-event.
                    import asyncio as _aio
                    buf = b""
                    deadline = _aio.get_event_loop().time() + 3.5
                    while _aio.get_event_loop().time() < deadline:
                        try:
                            chunk = await _aio.wait_for(
                                resp.content.readany(), timeout=2.5,
                            )
                        except _aio.TimeoutError:
                            break
                        if not chunk:
                            break
                        buf += chunk
                        if b"counts-event" in buf:
                            break
                    text = buf.decode("utf-8", errors="ignore")
                    assert "stream open" in text
                    assert "counts-event" in text
