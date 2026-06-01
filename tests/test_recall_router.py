"""Tests for the flag-gated recall router (memory lifecycle C5)."""

import pytest

from agent.recall_router import recall_backend_mode, route_recall, ensure_seeded
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


def test_ensure_seeded_ingests_vault_once(monkeypatch, tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "memo.md").write_text("session memo about brand kit production workflow")
    (vault / "user.md").write_text("user prefers semantic recall over flat grep")
    monkeypatch.setenv("SHAY_RECALL_SEED_DIRS", str(vault))
    be = MemoryRecallBackend(db_path=str(tmp_path / "seed.db"), prefer_model=False)
    try:
        n = ensure_seeded(be)
        assert n == 2
        assert be.count() == 2
        # Idempotent: a second call seeds nothing (backend non-empty).
        assert ensure_seeded(be) == 0
    finally:
        be.close()


def test_c4_autoseeds_when_no_backend_supplied(monkeypatch, tmp_path):
    # Flipping the flag with a fresh index should auto-seed from the vault
    # and return real hits — the activation seam, end to end.
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "memo.md").write_text(
        "kanban dispatcher protocol violation retry logic learned this session"
    )
    monkeypatch.setenv("SHAY_RECALL_BACKEND", "c4")
    monkeypatch.setenv("SHAY_RECALL_SEED_DIRS", str(vault))
    monkeypatch.setenv("SHAY_RECALL_DB", str(tmp_path / "auto.db"))
    out = route_recall("protocol violation retry", k=2,
                        flat_recall=lambda q: "SHOULD_NOT_BE_USED")
    assert "Recalled context" in out
    assert "protocol violation retry" in out
    assert "SHOULD_NOT_BE_USED" not in out
