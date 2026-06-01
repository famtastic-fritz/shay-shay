"""Tests for stable bearer-token auth on the dashboard.

Covers the SHAY_DASHBOARD_TOKEN / HERMES_DASHBOARD_TOKEN env-var bearer
contract that lets external clients (hermes-workspace v2.3 etc.) auth
without scraping the ephemeral session token from the SPA HTML.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Dict, Optional

import pytest

from shay_cli import web_server


def _make_request(authorization: Optional[str] = None,
                  session_header: Optional[str] = None):
    """Build a stand-in Request whose .headers.get() satisfies the auth helper."""
    headers: Dict[str, str] = {}
    if authorization is not None:
        headers["authorization"] = authorization
    if session_header is not None:
        headers[web_server._SESSION_HEADER_NAME] = session_header
    return SimpleNamespace(headers=headers)


@pytest.fixture(autouse=True)
def _clear_bearer_env(monkeypatch):
    monkeypatch.delenv("SHAY_DASHBOARD_TOKEN", raising=False)
    monkeypatch.delenv("HERMES_DASHBOARD_TOKEN", raising=False)
    yield


def test_ephemeral_token_validates_with_no_env_vars():
    """Existing behavior preserved: the per-startup session token works."""
    req = _make_request(authorization=f"Bearer {web_server._SESSION_TOKEN}")
    assert web_server._has_valid_session_token(req) is True


def test_arbitrary_token_rejected_with_no_env_vars():
    """Without env-bearer set, only the ephemeral token validates."""
    req = _make_request(authorization="Bearer not-the-real-token")
    assert web_server._has_valid_session_token(req) is False


def test_shay_dashboard_token_validates(monkeypatch):
    monkeypatch.setenv("SHAY_DASHBOARD_TOKEN", "abc123")
    req = _make_request(authorization="Bearer abc123")
    assert web_server._has_valid_session_token(req) is True


def test_shay_dashboard_token_wrong_value_rejected(monkeypatch):
    monkeypatch.setenv("SHAY_DASHBOARD_TOKEN", "abc123")
    req = _make_request(authorization="Bearer wrong")
    assert web_server._has_valid_session_token(req) is False


def test_hermes_dashboard_token_validates_when_shay_unset(monkeypatch):
    monkeypatch.setenv("HERMES_DASHBOARD_TOKEN", "xyz789")
    req = _make_request(authorization="Bearer xyz789")
    assert web_server._has_valid_session_token(req) is True


def test_shay_token_wins_precedence_over_hermes(monkeypatch):
    monkeypatch.setenv("SHAY_DASHBOARD_TOKEN", "shay-wins")
    monkeypatch.setenv("HERMES_DASHBOARD_TOKEN", "hermes-loses")

    shay_req = _make_request(authorization="Bearer shay-wins")
    assert web_server._has_valid_session_token(shay_req) is True

    hermes_req = _make_request(authorization="Bearer hermes-loses")
    assert web_server._has_valid_session_token(hermes_req) is False


def test_ephemeral_still_works_when_stable_token_present(monkeypatch):
    """Both auth modes coexist — the ephemeral session token still validates."""
    monkeypatch.setenv("SHAY_DASHBOARD_TOKEN", "abc123")
    req = _make_request(authorization=f"Bearer {web_server._SESSION_TOKEN}")
    assert web_server._has_valid_session_token(req) is True


def test_empty_env_var_treated_as_unset(monkeypatch):
    """Empty/whitespace env values must not be accepted as a valid token."""
    monkeypatch.setenv("SHAY_DASHBOARD_TOKEN", "   ")
    req = _make_request(authorization="Bearer   ")
    assert web_server._has_valid_session_token(req) is False


def test_resolve_stable_bearer_precedence(monkeypatch):
    monkeypatch.setenv("SHAY_DASHBOARD_TOKEN", "shay-tok")
    monkeypatch.setenv("HERMES_DASHBOARD_TOKEN", "hermes-tok")
    token, source = web_server._resolve_stable_bearer_token()
    assert token == "shay-tok"
    assert source == "SHAY_DASHBOARD_TOKEN"


def test_resolve_stable_bearer_falls_back_to_hermes(monkeypatch):
    monkeypatch.setenv("HERMES_DASHBOARD_TOKEN", "hermes-tok")
    token, source = web_server._resolve_stable_bearer_token()
    assert token == "hermes-tok"
    assert source == "HERMES_DASHBOARD_TOKEN"


def test_resolve_stable_bearer_returns_none_when_unset():
    token, source = web_server._resolve_stable_bearer_token()
    assert token is None
    assert source is None
