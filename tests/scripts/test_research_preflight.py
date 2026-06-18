from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "research_preflight.py"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def _init_state_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            title TEXT,
            source TEXT,
            started_at TEXT
        );
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY,
            session_id TEXT,
            timestamp TEXT,
            content TEXT,
            tool_name TEXT,
            tool_calls TEXT
        );
        CREATE VIRTUAL TABLE messages_fts USING fts5(content);
        INSERT INTO sessions (id, title, source, started_at)
        VALUES ('sess-1', 'Prior research thread', 'cli', '2026-06-18T00:00:00Z');
        INSERT INTO messages (id, session_id, timestamp, content, tool_name, tool_calls)
        VALUES (1, 'sess-1', '2026-06-18T00:10:00Z', 'We already researched the closed loop for duplicate research memory.', '', '');
        INSERT INTO messages_fts(rowid, content)
        VALUES (1, 'We already researched the closed loop for duplicate research memory.');
        """
    )
    conn.commit()
    conn.close()


def test_research_preflight_reports_already_researched_with_artifact_and_session_hits(tmp_path):
    research_root = tmp_path / "research"
    registry = research_root / "_ledger" / "research-registry.jsonl"
    ledger = research_root / "_ledger" / "research-artifacts.jsonl"
    artifact_path = research_root / "research-memory-closed-loop-2026-06-18.md"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        """---
summary: Existing summary
question: How do we prevent duplicate research?
---
# Research memory closed loop
""",
        encoding="utf-8",
    )

    row = {
        "created_at": "2026-06-18T12:00:00Z",
        "topic_key": "research-memory-closed-loop",
        "title": "Research memory closed loop",
        "summary": "Build a reusable research-memory loop.",
        "question": "How should Shay prevent duplicate research?",
        "path": str(artifact_path),
        "permalink": "shay-memory/research/research-memory-closed-loop-2026-06-18",
        "tags": ["research", "memory"],
        "freshness": "current",
        "verdict": "partial",
        "related_topics": ["duplicate research"],
        "resume_sentence": "Open the prior artifact and continue.",
    }
    _write_jsonl(registry, [row])
    _write_jsonl(ledger, [row])

    state_db = tmp_path / "state.db"
    _init_state_db(state_db)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--topic",
            "research memory closed loop",
            "--research-root",
            str(research_root),
            "--registry",
            str(registry),
            "--ledger",
            str(ledger),
            "--state-db",
            str(state_db),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["verdict"] == "already researched"
    assert payload["artifact_matches"]
    assert payload["artifact_matches"][0]["title"] == "Research memory closed loop"
    assert payload["session_hits"]
    assert payload["session_hits"][0]["session_id"] == "sess-1"


def test_research_preflight_reports_new_topic_when_no_matches_exist(tmp_path):
    research_root = tmp_path / "research"
    registry = research_root / "_ledger" / "research-registry.jsonl"
    ledger = research_root / "_ledger" / "research-artifacts.jsonl"
    state_db = tmp_path / "state.db"
    _init_state_db(state_db)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--topic",
            "entirely novel vendor scan",
            "--research-root",
            str(research_root),
            "--registry",
            str(registry),
            "--ledger",
            str(ledger),
            "--state-db",
            str(state_db),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["verdict"] == "new topic"
    assert payload["artifact_matches"] == []
