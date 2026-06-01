"""Tests for the flag-gated recall router (memory lifecycle C5)."""

import pytest

from agent.recall_router import recall_backend_mode, route_recall
from agent.memory_recall_backend import MemoryRecallBackend, MemoryNode


def test_default_mode_is_flat(monkeypatch):
    monkeypatch.delenv("SHAY_RECALL_BACKEND", raising=False)
    assert recall_backend_mode() == "flat"


def test_c4_mode_recognised(monkeypatch):
    monkeypatch.setenv("SHAY_RECALL_BACKEND", "c4")
    assert recall_backend_mode() == "c4"


def test_flat_default_uses_supplied_callable(monkeypatch):
    monkeypatch.delenv("SHAY_RECALL_BACKEND", raising=False)
    out = route_recall("anything", flat_recall=lambda q: f"FLAT:{q}")
    assert out == "FLAT:anything"


def test_c4_mode_routes_to_backend(monkeypatch, tmp_path):
    monkeypatch.setenv("SHAY_RECALL_BACKEND", "c4")
    be = MemoryRecallBackend(db_path=str(tmp_path / "r.db"), prefer_model=False)
    try:
        be.upsert_node(MemoryNode("n1", "kanban protocol violation retry logic"))
        out = route_recall(
            "protocol violation retry", k=1, backend=be,
            flat_recall=lambda q: "SHOULD_NOT_BE_USED",
        )
        assert "Recalled context" in out
        assert "kanban protocol violation retry logic" in out
        assert "SHOULD_NOT_BE_USED" not in out
    finally:
        be.close()


def test_c4_empty_falls_back_to_flat(monkeypatch, tmp_path):
    monkeypatch.setenv("SHAY_RECALL_BACKEND", "c4")
    be = MemoryRecallBackend(db_path=str(tmp_path / "empty.db"), prefer_model=False)
    try:
        out = route_recall(
            "anything", backend=be, flat_recall=lambda q: "FLAT_BACKSTOP",
        )
        assert out == "FLAT_BACKSTOP"
    finally:
        be.close()


def test_c4_error_falls_back_to_flat(monkeypatch):
    monkeypatch.setenv("SHAY_RECALL_BACKEND", "c4")

    class Boom:
        def recall(self, *a, **k):
            raise RuntimeError("backend down")

    out = route_recall("q", backend=Boom(), flat_recall=lambda q: "FLAT_RECOVERY")
    assert out == "FLAT_RECOVERY"
