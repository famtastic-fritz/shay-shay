"""Tests for the `/api/conductor/missions` CRUD surface.

This endpoint backs the hermes-workspace v2.3 Conductor capability. The
gateway probe (`src/server/gateway-capabilities.ts::probeConductor`) flips
`conductor: true` only when GET /api/conductor/missions returns HTTP 200 with
an `application/json` content-type. Workspace also POSTs to spawn missions and
DELETEs to stop them, so the full round-trip is covered here.

Coverage:
- GET with no auth -> 401
- GET with valid bearer, empty store -> {"version":1,"missions":[]}, 200, JSON
- list route content-type is application/json (the flag condition)
- POST creates a mission -> 200, returns mission with id + state, JSON
- GET /{id} after POST returns that mission
- GET unknown id -> 404
- DELETE /{id} -> mission state becomes 'cancelled'
- DELETE unknown id -> 404
"""
from __future__ import annotations

import pytest


class TestConductorMissionsApi:
    @pytest.fixture(autouse=True)
    def _setup_client(self, monkeypatch, _isolate_shay_home):
        from starlette.testclient import TestClient

        from shay_cli.web_server import app, _SESSION_HEADER_NAME, _SESSION_TOKEN

        self.client = TestClient(app)
        self._session_token = _SESSION_TOKEN
        self.client.headers[_SESSION_HEADER_NAME] = _SESSION_TOKEN

    # ── Auth ────────────────────────────────────────────────────────────────

    def test_list_requires_auth(self):
        from starlette.testclient import TestClient
        from shay_cli.web_server import app

        unauth = TestClient(app)
        resp = unauth.get("/api/conductor/missions")
        assert resp.status_code == 401

    # ── List ────────────────────────────────────────────────────────────────

    def test_list_empty_store(self):
        resp = self.client.get("/api/conductor/missions")
        assert resp.status_code == 200
        assert resp.json() == {"version": 1, "missions": []}

    def test_list_content_type_is_json(self):
        """The content-type is what flips the Workspace conductor flag."""
        resp = self.client.get("/api/conductor/missions")
        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"].lower()

    # ── Create ──────────────────────────────────────────────────────────────

    def test_post_creates_mission(self):
        resp = self.client.post(
            "/api/conductor/missions", json={"goal": "verify conductor wiring"}
        )
        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"].lower()
        body = resp.json()
        assert body["id"]
        assert body["state"] == "planning"
        assert body["title"].startswith("Conductor:")
        # Workspace's createDashboardConductorMission reads {id, name, session_id}.
        assert body["name"] == body["title"]
        assert body["session_id"] is None

    def test_post_accepts_name_prompt_shape(self):
        """Workspace's dashboard POST sends {name, prompt}, not {goal}."""
        resp = self.client.post(
            "/api/conductor/missions",
            json={"name": "conductor-123", "prompt": "do the thing"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"]
        assert body["state"] == "planning"

    def test_post_records_assignments(self):
        resp = self.client.post(
            "/api/conductor/missions",
            json={
                "goal": "ship feature",
                "assignments": [
                    {"workerId": "swarm5", "task": "implement", "reviewRequired": True},
                    {"workerId": "swarm6", "task": "review"},
                ],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["assignments"]) == 2
        first = body["assignments"][0]
        assert first["workerId"] == "swarm5"
        assert first["state"] == "queued"
        assert first["reviewRequired"] is True
        assert first["dependsOn"] == []

    def test_post_empty_goal_rejected(self):
        resp = self.client.post("/api/conductor/missions", json={})
        assert resp.status_code == 400

    # ── Get one ─────────────────────────────────────────────────────────────

    def test_get_after_post(self):
        created = self.client.post(
            "/api/conductor/missions", json={"goal": "round trip"}
        ).json()
        mission_id = created["id"]
        resp = self.client.get(f"/api/conductor/missions/{mission_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == mission_id

    def test_get_with_lines_param(self):
        created = self.client.post(
            "/api/conductor/missions", json={"goal": "with lines"}
        ).json()
        resp = self.client.get(
            f"/api/conductor/missions/{created['id']}?lines=50"
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_get_unknown_id_404(self):
        resp = self.client.get("/api/conductor/missions/does-not-exist")
        assert resp.status_code == 404

    # ── Delete ──────────────────────────────────────────────────────────────

    def test_delete_cancels_mission(self):
        created = self.client.post(
            "/api/conductor/missions",
            json={
                "goal": "to be cancelled",
                "assignments": [{"workerId": "swarm5", "task": "work"}],
            },
        ).json()
        mission_id = created["id"]
        resp = self.client.delete(f"/api/conductor/missions/{mission_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["mission"]["state"] == "cancelled"
        # Non-terminal assignments are cancelled too.
        assert body["mission"]["assignments"][0]["state"] == "cancelled"
        # Persisted: a follow-up GET reflects the cancellation.
        again = self.client.get(f"/api/conductor/missions/{mission_id}").json()
        assert again["state"] == "cancelled"

    def test_delete_unknown_id_404(self):
        resp = self.client.delete("/api/conductor/missions/nope")
        assert resp.status_code == 404
