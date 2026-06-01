"""Tests for the `/api/mcp*` routes that bridge shay's `mcp_servers` config
to the hermes-workspace v2.3 MCP UI contract.

Coverage:
- GET /api/mcp returns `{servers:[...]}` in workspace's `McpServer` JSON shape
- Secret values are masked; ``${ENV_REF}`` literals preserved
- POST /api/mcp validates input and persists via _save_mcp_server()
- DELETE /api/mcp/{name} removes the entry / 404 on unknown
- POST /api/mcp/test by-name calls the probe; ad-hoc input also supported
- POST /api/mcp/discover returns tools without persisting
- All routes require auth (401 without session token)
- SPA root injects __HERMES__SESSION_TOKEN__ so workspace's regex matches
- shay's nested `tools.{include,exclude}` is bridged to flat
  `includeTools` / `excludeTools` in the JSON shape
"""
from __future__ import annotations

import pytest

from shay_cli import mcp_config


# ─── Pure helpers ───────────────────────────────────────────────────────────


def test_mcp_entry_to_json_http_with_env_ref():
    cfg = {
        "url": "https://mcp.example.com/mcp",
        "auth": "bearer",
        "headers": {"Authorization": "Bearer ${MCP_FOO_API_KEY}"},
        "enabled": True,
    }
    out = mcp_config.mcp_entry_to_json("foo", cfg)
    assert out["name"] == "foo"
    assert out["id"] == "foo"
    assert out["transportType"] == "http"
    assert out["url"] == "https://mcp.example.com/mcp"
    assert out["authType"] == "bearer"
    assert out["hasBearerToken"] is True
    # Env-ref preserved as-is — not masked
    assert out["headers"]["Authorization"] == "Bearer ${MCP_FOO_API_KEY}"
    assert out["status"] == "unknown"
    assert out["source"] == "configured"
    assert out["authEnvRef"] == "MCP_FOO_API_KEY"


def test_mcp_entry_to_json_stdio_with_secret_env_masked():
    cfg = {
        "command": "npx",
        "args": ["@modelcontextprotocol/server-github"],
        "env": {"GITHUB_TOKEN": "ghp_real_secret_abc123"},
    }
    out = mcp_config.mcp_entry_to_json("github", cfg)
    assert out["transportType"] == "stdio"
    assert out["command"] == "npx"
    assert out["args"] == ["@modelcontextprotocol/server-github"]
    # Secret value masked
    assert out["env"]["GITHUB_TOKEN"] == mcp_config.MASK_SENTINEL
    # _TOKEN suffix => bearer detected
    assert out["hasBearerToken"] is True
    assert out["authType"] == "bearer"


def test_mcp_entry_to_json_bridges_nested_tools_to_flat_arrays():
    """Shay stores `tools.{include,exclude}`; workspace expects flat keys."""
    cfg = {
        "url": "https://x/mcp",
        "tools": {"include": ["search", "read"], "exclude": ["write"]},
    }
    out = mcp_config.mcp_entry_to_json("x", cfg)
    assert out["includeTools"] == ["search", "read"]
    assert out["excludeTools"] == ["write"]
    # toolMode inferred from include presence
    assert out["toolMode"] == "include"


def test_mcp_entry_to_json_no_secrets_means_no_bearer():
    cfg = {"url": "https://x/mcp"}
    out = mcp_config.mcp_entry_to_json("x", cfg)
    assert out["hasBearerToken"] is False
    assert out["authType"] == "none"


def test_mcp_input_to_config_entry_http():
    name, cfg = mcp_config.mcp_input_to_config_entry({
        "name": "foo",
        "transportType": "http",
        "url": "https://mcp.example.com/mcp",
    })
    assert name == "foo"
    assert cfg["url"] == "https://mcp.example.com/mcp"
    assert cfg["enabled"] is True


def test_mcp_input_to_config_entry_stdio():
    name, cfg = mcp_config.mcp_input_to_config_entry({
        "name": "gh",
        "transportType": "stdio",
        "command": "npx",
        "args": ["@modelcontextprotocol/server-github"],
    })
    assert name == "gh"
    assert cfg["command"] == "npx"
    assert cfg["args"] == ["@modelcontextprotocol/server-github"]


def test_mcp_input_to_config_entry_rejects_missing_transport():
    with pytest.raises(ValueError):
        mcp_config.mcp_input_to_config_entry({"name": "x"})


def test_mcp_input_to_config_entry_rejects_missing_name():
    with pytest.raises(ValueError):
        mcp_config.mcp_input_to_config_entry({"transportType": "http", "url": "https://x"})


def test_mcp_input_to_config_entry_rejects_http_without_url():
    with pytest.raises(ValueError):
        mcp_config.mcp_input_to_config_entry({"name": "x", "transportType": "http"})


def test_mcp_input_to_config_entry_includes_tool_filter():
    name, cfg = mcp_config.mcp_input_to_config_entry({
        "name": "x",
        "transportType": "http",
        "url": "https://x/mcp",
        "includeTools": ["a", "b"],
    })
    assert cfg["tools"]["include"] == ["a", "b"]


# ─── Route tests (TestClient) ───────────────────────────────────────────────


class TestMcpRoutes:
    @pytest.fixture(autouse=True)
    def _setup_client(self, monkeypatch, _isolate_shay_home):
        try:
            from starlette.testclient import TestClient
        except ImportError:
            pytest.skip("fastapi/starlette not installed")

        import shay_state
        from shay_constants import get_shay_home
        from shay_cli.web_server import app, _SESSION_HEADER_NAME, _SESSION_TOKEN

        monkeypatch.setattr(shay_state, "DEFAULT_DB_PATH", get_shay_home() / "state.db")

        self.client = TestClient(app)
        self._session_header = _SESSION_HEADER_NAME
        self._session_token = _SESSION_TOKEN
        self.client.headers[_SESSION_HEADER_NAME] = _SESSION_TOKEN

    def _seed_server(self, name: str, cfg: dict):
        from shay_cli.config import load_config, save_config
        config = load_config()
        config.setdefault("mcp_servers", {})[name] = cfg
        save_config(config)

    def test_list_empty(self):
        resp = self.client.get("/api/mcp")
        assert resp.status_code == 200
        data = resp.json()
        assert data == {"servers": [], "total": 0}

    def test_list_returns_workspace_shape(self):
        self._seed_server("foo", {
            "url": "https://mcp.example.com/mcp",
            "auth": "bearer",
            "headers": {"Authorization": "Bearer ${MCP_FOO_API_KEY}"},
        })
        resp = self.client.get("/api/mcp")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        srv = data["servers"][0]
        assert srv["name"] == "foo"
        assert srv["transportType"] == "http"
        assert srv["authType"] == "bearer"
        assert srv["hasBearerToken"] is True
        # Env-ref preserved
        assert srv["headers"]["Authorization"] == "Bearer ${MCP_FOO_API_KEY}"

    def test_list_masks_raw_secrets(self):
        self._seed_server("gh", {
            "command": "npx",
            "args": ["@modelcontextprotocol/server-github"],
            "env": {"GITHUB_TOKEN": "literal-secret"},
        })
        resp = self.client.get("/api/mcp")
        srv = resp.json()["servers"][0]
        assert srv["env"]["GITHUB_TOKEN"] == mcp_config.MASK_SENTINEL

    def test_unauthenticated_request_rejected(self):
        from starlette.testclient import TestClient
        from shay_cli.web_server import app
        unauth = TestClient(app)
        resp = unauth.get("/api/mcp")
        assert resp.status_code == 401

    def test_post_creates_server(self):
        resp = self.client.post("/api/mcp", json={
            "name": "newone",
            "transportType": "http",
            "url": "https://mcp.example.com/mcp",
        })
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ok"] is True
        assert body["server"]["name"] == "newone"
        # Persisted
        from shay_cli.mcp_config import _get_mcp_servers
        assert "newone" in _get_mcp_servers()

    def test_post_rejects_invalid_payload(self):
        resp = self.client.post("/api/mcp", json={"transportType": "http"})
        assert resp.status_code == 400

    def test_delete_removes_server(self):
        self._seed_server("victim", {"url": "https://x/mcp"})
        resp = self.client.delete("/api/mcp/victim")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        from shay_cli.mcp_config import _get_mcp_servers
        assert "victim" not in _get_mcp_servers()

    def test_delete_unknown_404(self):
        resp = self.client.delete("/api/mcp/nope")
        assert resp.status_code == 404

    def test_test_by_name_calls_probe(self, monkeypatch):
        self._seed_server("probed", {"url": "https://x/mcp"})

        captured: list = []

        def _fake_probe(name, cfg, connect_timeout=30):
            captured.append((name, cfg))
            return [("tool_a", "desc a")]

        monkeypatch.setattr(mcp_config, "_probe_single_server", _fake_probe)

        resp = self.client.post("/api/mcp/test", json={"name": "probed"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ok"] is True
        assert body["status"] == "connected"
        assert body["discoveredTools"] == [{"name": "tool_a", "description": "desc a"}]
        assert captured and captured[0][0] == "probed"

    def test_test_by_name_unknown_404(self):
        resp = self.client.post("/api/mcp/test", json={"name": "ghost"})
        assert resp.status_code == 404

    def test_test_reports_failure(self, monkeypatch):
        self._seed_server("breaks", {"url": "https://x/mcp"})

        def _broken(name, cfg, connect_timeout=30):
            raise RuntimeError("401 Unauthorized")

        monkeypatch.setattr(mcp_config, "_probe_single_server", _broken)
        resp = self.client.post("/api/mcp/test", json={"name": "breaks"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert body["status"] == "failed"
        assert "401" in body["error"]

    def test_discover_with_ad_hoc_input(self, monkeypatch):
        def _fake(name, cfg, connect_timeout=30):
            return [("t1", "d1"), ("t2", "d2")]

        monkeypatch.setattr(mcp_config, "_probe_single_server", _fake)

        resp = self.client.post("/api/mcp/discover", json={
            "name": "adhoc",
            "transportType": "http",
            "url": "https://x/mcp",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["tools"] == [
            {"name": "t1", "description": "d1"},
            {"name": "t2", "description": "d2"},
        ]
        # ad-hoc must NOT persist
        from shay_cli.mcp_config import _get_mcp_servers
        assert "adhoc" not in _get_mcp_servers()

    def test_logs_returns_stub(self):
        self._seed_server("loggy", {"url": "https://x/mcp"})
        resp = self.client.get("/api/mcp/loggy/logs")
        assert resp.status_code == 200
        body = resp.json()
        assert body == {"lines": [], "available": False}

    def test_logs_unknown_404(self):
        resp = self.client.get("/api/mcp/ghost/logs")
        assert resp.status_code == 404


def test_workspace_dashboard_token_regex_matches_spa_root(_isolate_shay_home, monkeypatch, tmp_path):
    """The SPA shell must inline a `window.__HERMES__SESSION_TOKEN__` literal
    so hermes-workspace's `fetchDashboardToken()` regex extracts a valid token.

    Mirrors the production regex from
    _refs/hermes-workspace-v2.3/src/server/gateway-capabilities.ts (line 157-158).
    """
    import re
    from starlette.testclient import TestClient
    from shay_cli import web_server

    # The workspace regex
    DASHBOARD_TOKEN_REGEX = re.compile(
        r"window\._+(?:CLAUDE|HERMES)_+SESSION_+TOKEN__+\s*=\s*[\"']([^\"']+)[\"']"
    )

    # Build a minimal SPA shell on a temp WEB_DIST so the SPA mount activates.
    web_dist = tmp_path / "web_dist"
    web_dist.mkdir()
    (web_dist / "index.html").write_text(
        "<!doctype html><html><head><title>Shay</title></head>"
        "<body><div id=root></div></body></html>"
    )
    (web_dist / "assets").mkdir()
    monkeypatch.setattr(web_server, "WEB_DIST", web_dist)

    # Mount SPA onto a fresh FastAPI app so we don't clobber the global one.
    from fastapi import FastAPI
    fresh = FastAPI()
    web_server.mount_spa(fresh)
    client = TestClient(fresh)
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text
    match = DASHBOARD_TOKEN_REGEX.search(html)
    assert match is not None, (
        "workspace's dashboard-token regex did not match shay's SPA root HTML — "
        "MCP probe via dashboardFetch will fail with 401"
    )
    assert match.group(1) == web_server._SESSION_TOKEN
