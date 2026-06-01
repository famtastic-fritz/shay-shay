import json

from agent.intelligence_ledger import (
    append_event,
    events_path,
    intelligence_home,
    is_enabled,
    read_events,
    summarize_events,
)


def test_paths_are_profile_scoped(tmp_path, monkeypatch):
    profile_home = tmp_path / ".shay" / "profiles" / "coder"
    monkeypatch.setenv("SHAY_HOME", str(profile_home))

    assert intelligence_home() == profile_home / "intelligence"
    assert events_path() == profile_home / "intelligence" / "events.jsonl"


def test_append_event_creates_jsonl_and_read_events(tmp_path, monkeypatch):
    shay_home = tmp_path / ".shay"
    monkeypatch.setenv("SHAY_HOME", str(shay_home))
    monkeypatch.delenv("SHAY_INTELLIGENCE_ENABLED", raising=False)

    first = append_event(
        "tool.failed",
        summary="Browser check failed",
        metadata={"tool": "browser", "code": 500},
        source="test",
        session_id="session-1",
        task_id="task-1",
        ts=123.0,
    )
    second = append_event("skill.loaded", summary="Loaded shay-shay", source="test", ts=124.0)

    assert first is not None
    assert second is not None
    assert events_path().exists()

    raw_lines = events_path().read_text(encoding="utf-8").splitlines()
    assert len(raw_lines) == 2
    assert json.loads(raw_lines[0])["type"] == "tool.failed"

    events = read_events(limit=None)
    assert [event["type"] for event in events] == ["tool.failed", "skill.loaded"]
    assert events[0]["summary"] == "Browser check failed"
    assert events[0]["metadata"] == {"code": 500, "tool": "browser"}


def test_read_events_filters_and_limits(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAY_HOME", str(tmp_path / ".shay"))

    append_event("alpha", ts=10.0)
    append_event("beta", ts=20.0)
    append_event("alpha", ts=30.0)

    assert [event["type"] for event in read_events(limit=2)] == ["beta", "alpha"]
    assert [event["ts"] for event in read_events(event_type="alpha", limit=None)] == [10.0, 30.0]
    assert [event["type"] for event in read_events(since_ts=20.0, limit=None)] == ["beta", "alpha"]
    assert read_events(limit=0) == []


def test_disabled_mode_skips_writes(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAY_HOME", str(tmp_path / ".shay"))
    monkeypatch.setenv("SHAY_INTELLIGENCE_ENABLED", "false")

    assert not is_enabled()
    assert append_event("tool.called") is None
    assert not events_path().exists()


def test_redacts_secret_keys_and_obvious_token_values(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAY_HOME", str(tmp_path / ".shay"))

    record = append_event(
        "memory.written",
        summary="Stored token sk-abcdefghijklmnopqrstuvwxyz1234567890",
        metadata={
            "api_key": "sk-secret-key-value",
            "nested": {"Authorization": "Bearer abcdefghijklmnopqrstuvwxyz1234567890"},
            "safe": "visible",
        },
    )

    assert record is not None
    event = read_events(limit=1)[0]
    assert "sk-abcdefghijklmnopqrstuvwxyz1234567890" not in event["summary"]
    assert event["metadata"]["api_key"] == "[REDACTED]"
    assert event["metadata"]["nested"]["Authorization"] == "[REDACTED]"
    assert event["metadata"]["safe"] == "visible"


def test_read_events_skips_corrupt_rows(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAY_HOME", str(tmp_path / ".shay"))
    append_event("valid", ts=1.0)
    with events_path().open("a", encoding="utf-8") as handle:
        handle.write("not json\n")
        handle.write(json.dumps({"type": "also-valid", "ts": 2.0}) + "\n")

    assert [event["type"] for event in read_events(limit=None)] == ["valid", "also-valid"]


def test_summarize_events_counts_types_sources_and_latest_ts():
    summary = summarize_events([
        {"type": "tool.failed", "source": "cli", "ts": 1.0},
        {"type": "tool.failed", "source": "cli", "ts": 3.0},
        {"type": "skill.loaded", "source": "gateway", "ts": 2.0},
    ])

    assert summary == {
        "total": 3,
        "by_type": {"skill.loaded": 1, "tool.failed": 2},
        "by_source": {"cli": 2, "gateway": 1},
        "latest_ts": 3.0,
    }
