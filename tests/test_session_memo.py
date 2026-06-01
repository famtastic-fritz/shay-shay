"""Tests for the session-memo persistence (memory lifecycle stage b)."""

from pathlib import Path

import agent.session_memo as sm
from agent.context_compressor import ContextCompressor, SUMMARY_PREFIX


def test_persist_writes_l1_memo(tmp_path):
    out = tmp_path / "sessions"
    path = sm.persist_session_memo(
        session_id="sess-123",
        summary_body="## Active Task\nFinish the gate fix\n",
        platform="cli",
        project="shay-shay",
        model="aux-model",
        vault_dir=out,
    )
    assert path is not None
    assert path.exists()
    text = path.read_text()
    assert "memory_layer: L1" in text
    assert "memory/l1" in text
    assert "session_id: \"sess-123\"" in text
    assert "memo_schema: handoff-v1" in text
    assert "## Active Task" in text
    assert "Finish the gate fix" in text


def test_persist_idempotent_overwrite(tmp_path):
    out = tmp_path / "sessions"
    sm.persist_session_memo(
        session_id="sess-x", summary_body="first", vault_dir=out,
    )
    sm.persist_session_memo(
        session_id="sess-x", summary_body="second pass", vault_dir=out,
    )
    files = list(out.glob("*.md"))
    assert len(files) == 1
    assert "second pass" in files[0].read_text()


def test_persist_empty_summary_writes_nothing(tmp_path):
    out = tmp_path / "sessions"
    assert sm.persist_session_memo(
        session_id="empty", summary_body="   \n  ", vault_dir=out,
    ) is None
    assert not out.exists() or not list(out.glob("*.md"))


def test_persist_scrubs_secrets(tmp_path):
    out = tmp_path / "sessions"
    body = "## Critical Context\napi_key: sk-supersecret-abc123\nnormal line"
    path = sm.persist_session_memo(
        session_id="secret", summary_body=body, vault_dir=out,
    )
    text = path.read_text()
    assert "sk-supersecret-abc123" not in text
    assert "[REDACTED]" in text
    assert "normal line" in text


def test_compressor_on_session_end_persists_previous_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAY_MEMORY_VAULT", str(tmp_path / "vault"))
    eng = ContextCompressor(model="test-model", quiet_mode=True)
    eng.on_session_start("sess-end", platform="cli", model="test-model")
    eng._previous_summary = f"{SUMMARY_PREFIX}\n## Active Task\nShip C1\n"

    eng.on_session_end("sess-end", messages=[])

    memo = tmp_path / "vault" / "reflections" / "episodic" / "sessions" / "sess-end.md"
    assert memo.exists()
    text = memo.read_text()
    # Prefix is stripped; section body is kept.
    assert "## Active Task" in text
    assert "Ship C1" in text
    assert SUMMARY_PREFIX not in text


def test_compressor_on_session_end_no_summary_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAY_MEMORY_VAULT", str(tmp_path / "vault"))
    eng = ContextCompressor(model="test-model", quiet_mode=True)
    eng.on_session_start("sess-quiet", platform="cli")
    # No _previous_summary, no in-context summary in messages.
    eng.on_session_end("sess-quiet", messages=[
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ])
    sessions = tmp_path / "vault" / "reflections" / "episodic" / "sessions"
    assert not sessions.exists() or not list(sessions.glob("*.md"))
