"""Proves the Workspace `capabilities.kanban=true` probe will succeed.

Workspace v2.3 (gateway-capabilities.ts:612-627) probes
``GET ${CLAUDE_DASHBOARD_URL}/api/plugins/kanban/board`` and treats any HTTP
status that is NOT 404 or 405 as "kanban available". For Shay's FastAPI
dashboard to expose that route, three things must line up:

1. ``plugins/kanban/dashboard/manifest.json`` exists with the right shape
   (``name``, ``api`` pointing at a Python file that exposes
   ``router = APIRouter()``).
2. ``_discover_dashboard_plugins()`` finds it via the bundled-plugins root
   (``get_bundled_plugins_dir()``) and reports ``has_api=True``.
3. The router actually defines ``GET /board`` so the mounted path
   ``/api/plugins/kanban/board`` returns a non-404/non-405 status.

This test pins all three so a regression in any of them is caught before
Workspace silently downgrades to ``kanban: false``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shay_cli import kanban_db as kb
from shay_cli.plugins import get_bundled_plugins_dir


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "plugins" / "kanban" / "dashboard" / "manifest.json"
PLUGIN_API = REPO_ROOT / "plugins" / "kanban" / "dashboard" / "plugin_api.py"


# ---------------------------------------------------------------------------
# 1. Manifest shape
# ---------------------------------------------------------------------------


def test_kanban_manifest_exists_and_has_required_keys():
    assert MANIFEST.exists(), f"manifest missing: {MANIFEST}"
    data = json.loads(MANIFEST.read_text())
    # Discovery requires name; route mount requires api.
    assert data.get("name") == "kanban", data
    assert data.get("api") == "plugin_api.py", data
    # The api file the manifest points at must exist.
    assert (MANIFEST.parent / data["api"]).exists()


# ---------------------------------------------------------------------------
# 2. Discovery finds it via the bundled-plugins root
# ---------------------------------------------------------------------------


def test_bundled_plugins_dir_resolves_to_shay_shay_plugins():
    """The discovery root must point at this repo's plugins/ tree, otherwise
    the bundled manifest is invisible to _discover_dashboard_plugins()."""
    bundled = get_bundled_plugins_dir().resolve()
    expected = (REPO_ROOT / "plugins").resolve()
    assert bundled == expected, (
        f"bundled plugins dir {bundled} != expected {expected} — "
        "_discover_dashboard_plugins() will not find the kanban manifest"
    )


def test_discover_dashboard_plugins_finds_kanban(tmp_path, monkeypatch):
    """_discover_dashboard_plugins() must surface the kanban entry with
    has_api=True so _mount_plugin_api_routes() actually mounts it."""
    # Point user-plugins dir at an empty tmp so we only exercise the bundled
    # path (which is what production uses for shay-shay's in-tree plugins).
    empty_home = tmp_path / "shayhome"
    empty_home.mkdir()
    monkeypatch.setenv("SHAY_HOME", str(empty_home))
    monkeypatch.delenv("SHAY_ENABLE_PROJECT_PLUGINS", raising=False)

    from shay_cli import web_server

    plugins = web_server._discover_dashboard_plugins()
    kanban = next((p for p in plugins if p["name"] == "kanban"), None)
    assert kanban is not None, (
        f"kanban not discovered. Found: {[p['name'] for p in plugins]}"
    )
    assert kanban["has_api"] is True
    assert kanban["_api_file"] == "plugin_api.py"
    # Source is "bundled" — manifest lives in the in-repo plugins/ tree.
    assert kanban["source"] == "bundled"


# ---------------------------------------------------------------------------
# 3. The probe target — GET /api/plugins/kanban/board — is reachable
# ---------------------------------------------------------------------------


def _load_router():
    spec = importlib.util.spec_from_file_location(
        "shay_dashboard_plugin_kanban_probe", PLUGIN_API,
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod.router


@pytest.fixture
def kanban_client(tmp_path, monkeypatch):
    home = tmp_path / ".shay"
    home.mkdir()
    monkeypatch.setenv("SHAY_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    app = FastAPI()
    # Mount at the exact prefix _mount_plugin_api_routes() uses.
    app.include_router(_load_router(), prefix="/api/plugins/kanban")
    return TestClient(app)


def test_workspace_probe_status_is_not_404_or_405(kanban_client):
    """probeKanban() in gateway-capabilities.ts treats anything other than
    404/405 as "kanban available". The route must therefore answer with
    a real status (200 here)."""
    r = kanban_client.get("/api/plugins/kanban/board")
    assert r.status_code not in (404, 405), (
        f"Workspace would mark kanban as unavailable: got {r.status_code}"
    )
    # And in fact the empty board returns 200.
    assert r.status_code == 200


def test_workspace_probe_path_matches_manifest_name(kanban_client):
    """The exact URL Workspace hits is built from manifest.name. If the
    manifest name drifts from `kanban`, this guard fires."""
    data = json.loads(MANIFEST.read_text())
    probe_path = f"/api/plugins/{data['name']}/board"
    assert probe_path == "/api/plugins/kanban/board"
    assert kanban_client.get(probe_path).status_code == 200
