"""Tests for shay_cli.build_ledger — durable ledger + search module."""
import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

import shay_cli.build_ledger as bl
import shay_cli.build_tracker as bt


# ---------------------------------------------------------------------------
# Shared fixture: minimal shay home with runs
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_shay(tmp_path):
    """Minimal ~/.shay-like directory with 4 runs and a sessions table."""
    shay_home = tmp_path / "shay"
    shay_home.mkdir()

    board_dir = shay_home / "kanban" / "boards" / "masterplan"
    board_dir.mkdir(parents=True)
    db_path = board_dir / "kanban.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE tasks (
            id TEXT PRIMARY KEY,
            title TEXT
        );
        CREATE TABLE task_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            profile TEXT,
            step_key TEXT,
            status TEXT NOT NULL,
            claim_lock TEXT,
            claim_expires INTEGER,
            worker_pid INTEGER,
            max_runtime_seconds INTEGER,
            last_heartbeat_at INTEGER,
            started_at INTEGER NOT NULL,
            ended_at INTEGER,
            outcome TEXT,
            summary TEXT,
            metadata TEXT,
            error TEXT
        );
    """)

    base_ts = int(time.time()) - 7200

    # Insert task titles
    conn.executemany("INSERT INTO tasks (id, title) VALUES (?,?)", [
        ("t_aaa", "B3 — Wire synthesize_sections into build_app"),
        ("t_bbb", "H2 — Agent capability preflight check"),
        ("t_ccc", "BT — Build Tracker"),
        ("t_ddd", "P0-WT — Verify git-worktree isolation"),
    ])

    rows = [
        # protocol violation
        ("t_aaa", "builder", "done", "crashed",
         base_ts, base_ts + 120,
         json.dumps({"pid": 100}),
         "worker exited cleanly (rc=0) without calling kanban_complete or kanban_block — protocol violation"),
        # gate bypass
        ("t_bbb", "builder", "done", "completed",
         base_ts + 300, base_ts + 660,
         json.dumps({"tests_run": 0, "tests_passed": 0, "changed_files": ["/foo/pipeline.py"]}),
         None),
        # normal success
        ("t_ccc", "builder", "done", "completed",
         base_ts + 700, base_ts + 1000,
         json.dumps({"tests_run": 12, "tests_passed": 12,
                     "changed_files": ["/shay_cli/build_tracker.py"],
                     "decisions": ["READ-ONLY path"]}),
         None),
        # timeout
        ("t_ddd", "researcher", "done", "timed_out",
         base_ts + 1100, base_ts + 2700,
         json.dumps({}),
         None),
    ]
    conn.executemany(
        "INSERT INTO task_runs (task_id, profile, status, outcome, started_at, ended_at, metadata, error) "
        "VALUES (?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()

    # Profile sessions
    profile_dir = shay_home / "profiles" / "builder"
    profile_dir.mkdir(parents=True)
    state_db = profile_dir / "state.db"
    sconn = sqlite3.connect(str(state_db))
    sconn.executescript("""
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL DEFAULT 'cli',
            model TEXT,
            billing_provider TEXT,
            estimated_cost_usd REAL,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            started_at REAL NOT NULL,
            ended_at REAL
        );
    """)
    sconn.execute(
        "INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?)",
        ("sess_001", "cli", "claude-sonnet-4", "anthropic", 0.55,
         2000, 8000, float(base_ts + 280), float(base_ts + 700)),
    )
    sconn.commit()
    sconn.close()

    return shay_home


@pytest.fixture
def tmp_ledger(tmp_path):
    return tmp_path / "build-ledger.db"


# ---------------------------------------------------------------------------
# build_id determinism
# ---------------------------------------------------------------------------

def test_build_id_deterministic():
    a = bl._build_id("masterplan", 7)
    b = bl._build_id("masterplan", 7)
    assert a == b
    assert a.startswith("b_")
    assert len(a) == 16   # "b_" + 14 hex chars


def test_build_id_different_for_different_runs():
    a = bl._build_id("masterplan", 7)
    b = bl._build_id("masterplan", 8)
    assert a != b


# ---------------------------------------------------------------------------
# Error normalization
# ---------------------------------------------------------------------------

def test_normalize_error_strips_hex():
    sig = bl._normalize_error("PID=12345 exit 0 ref=deadbeef1234abcd")
    assert "deadbeef" not in sig
    assert "<HEX>" in sig


def test_normalize_error_clusters_protocol_violations():
    e1 = "worker exited cleanly (rc=0) without calling kanban_complete or kanban_block — protocol violation [pid=53229]"
    e2 = "worker exited cleanly (rc=0) without calling kanban_complete or kanban_block — protocol violation [pid=34157]"
    assert bl._normalize_error(e1) == bl._normalize_error(e2)


def test_normalize_error_none():
    assert bl._normalize_error(None) is None


# ---------------------------------------------------------------------------
# capture_all
# ---------------------------------------------------------------------------

def test_capture_all_inserts_runs(tmp_shay, tmp_ledger):
    with patch.object(bl, "_shay_home", return_value=tmp_shay), \
         patch.object(bt, "_shay_home", return_value=tmp_shay):
        result = bl.capture_all(ledger_path=tmp_ledger, vault_dir=None)
    assert result["new"] == 4
    assert result["skipped"] == 0


def test_capture_all_idempotent(tmp_shay, tmp_ledger):
    """Running capture twice should not double-insert."""
    with patch.object(bl, "_shay_home", return_value=tmp_shay), \
         patch.object(bt, "_shay_home", return_value=tmp_shay):
        r1 = bl.capture_all(ledger_path=tmp_ledger, vault_dir=None)
        r2 = bl.capture_all(ledger_path=tmp_ledger, vault_dir=None)
    assert r1["new"] == 4
    assert r2["new"] == 0
    assert r2["skipped"] == 4


def test_capture_all_stores_task_title(tmp_shay, tmp_ledger):
    with patch.object(bl, "_shay_home", return_value=tmp_shay), \
         patch.object(bt, "_shay_home", return_value=tmp_shay):
        bl.capture_all(ledger_path=tmp_ledger, vault_dir=None)

    conn = sqlite3.connect(str(tmp_ledger))
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT task_title FROM builds WHERE task_id = 't_ccc'")
    row = cur.fetchone()
    conn.close()
    assert row is not None
    assert "Build Tracker" in row["task_title"]


def test_capture_all_gate_bypass_flag(tmp_shay, tmp_ledger):
    with patch.object(bl, "_shay_home", return_value=tmp_shay), \
         patch.object(bt, "_shay_home", return_value=tmp_shay):
        bl.capture_all(ledger_path=tmp_ledger, vault_dir=None)

    conn = sqlite3.connect(str(tmp_ledger))
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT gate_bypass FROM builds WHERE task_id = 't_bbb'")
    row = cur.fetchone()
    conn.close()
    assert row["gate_bypass"] == 1


def test_capture_all_protocol_violation_flag(tmp_shay, tmp_ledger):
    with patch.object(bl, "_shay_home", return_value=tmp_shay), \
         patch.object(bt, "_shay_home", return_value=tmp_shay):
        bl.capture_all(ledger_path=tmp_ledger, vault_dir=None)

    conn = sqlite3.connect(str(tmp_ledger))
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT protocol_violation, error_signature FROM builds WHERE task_id = 't_aaa'")
    row = cur.fetchone()
    conn.close()
    assert row["protocol_violation"] == 1
    assert row["error_signature"] is not None


def test_capture_all_writes_vault_note(tmp_shay, tmp_ledger, tmp_path):
    vault_dir = tmp_path / "vault" / "builds"
    with patch.object(bl, "_shay_home", return_value=tmp_shay), \
         patch.object(bt, "_shay_home", return_value=tmp_shay):
        bl.capture_all(ledger_path=tmp_ledger, vault_dir=vault_dir)

    notes = list(vault_dir.glob("b_*.md"))
    assert len(notes) == 4
    # Check one note has expected content
    content = notes[0].read_text()
    assert "Build b_" in content


# ---------------------------------------------------------------------------
# list_builds
# ---------------------------------------------------------------------------

def test_list_builds_returns_all(tmp_shay, tmp_ledger):
    with patch.object(bl, "_shay_home", return_value=tmp_shay), \
         patch.object(bt, "_shay_home", return_value=tmp_shay):
        bl.capture_all(ledger_path=tmp_ledger, vault_dir=None)
        builds = bl.list_builds(ledger_path=tmp_ledger)
    assert len(builds) == 4


def test_list_builds_filter_outcome(tmp_shay, tmp_ledger):
    with patch.object(bl, "_shay_home", return_value=tmp_shay), \
         patch.object(bt, "_shay_home", return_value=tmp_shay):
        bl.capture_all(ledger_path=tmp_ledger, vault_dir=None)
        completed = bl.list_builds(outcome="completed", ledger_path=tmp_ledger)
    assert len(completed) == 2
    assert all(b["outcome"] == "completed" for b in completed)


def test_list_builds_filter_profile(tmp_shay, tmp_ledger):
    with patch.object(bl, "_shay_home", return_value=tmp_shay), \
         patch.object(bt, "_shay_home", return_value=tmp_shay):
        bl.capture_all(ledger_path=tmp_ledger, vault_dir=None)
        researcher = bl.list_builds(profile="researcher", ledger_path=tmp_ledger)
    assert len(researcher) == 1
    assert researcher[0]["task_id"] == "t_ddd"


def test_list_builds_empty_before_capture(tmp_ledger):
    # Ledger not yet written — should return empty gracefully
    builds = bl.list_builds(ledger_path=tmp_ledger)
    assert builds == []


# ---------------------------------------------------------------------------
# show_build
# ---------------------------------------------------------------------------

def test_show_build_found(tmp_shay, tmp_ledger):
    with patch.object(bl, "_shay_home", return_value=tmp_shay), \
         patch.object(bt, "_shay_home", return_value=tmp_shay):
        bl.capture_all(ledger_path=tmp_ledger, vault_dir=None)
        builds = bl.list_builds(ledger_path=tmp_ledger)
    bid = builds[0]["build_id"]
    result = bl.show_build(bid, ledger_path=tmp_ledger)
    assert result is not None
    assert result["build_id"] == bid


def test_show_build_not_found(tmp_ledger):
    result = bl.show_build("b_doesnotexist", ledger_path=tmp_ledger)
    assert result is None


# ---------------------------------------------------------------------------
# search_ledger
# ---------------------------------------------------------------------------

def test_search_finds_protocol_violation(tmp_shay, tmp_ledger):
    with patch.object(bl, "_shay_home", return_value=tmp_shay), \
         patch.object(bt, "_shay_home", return_value=tmp_shay):
        bl.capture_all(ledger_path=tmp_ledger, vault_dir=None)
        results = bl.search_ledger("protocol violation", ledger_path=tmp_ledger)
    assert len(results) >= 1
    assert any(r["task_id"] == "t_aaa" for r in results)


def test_search_finds_gate_bypass(tmp_shay, tmp_ledger):
    with patch.object(bl, "_shay_home", return_value=tmp_shay), \
         patch.object(bt, "_shay_home", return_value=tmp_shay):
        bl.capture_all(ledger_path=tmp_ledger, vault_dir=None)
        # Search by decision text that's in t_ccc
        results = bl.search_ledger("READ-ONLY", ledger_path=tmp_ledger)
    assert len(results) >= 1
    assert any(r["task_id"] == "t_ccc" for r in results)


def test_search_filter_file_touched(tmp_shay, tmp_ledger):
    with patch.object(bl, "_shay_home", return_value=tmp_shay), \
         patch.object(bt, "_shay_home", return_value=tmp_shay):
        bl.capture_all(ledger_path=tmp_ledger, vault_dir=None)
        # t_bbb changed /foo/pipeline.py
        results = bl.search_ledger("protocol", file_touched="pipeline.py",
                                   ledger_path=tmp_ledger)
    # protocol violation is t_aaa which has no changed_files → filtered out
    for r in results:
        files = r.get("changed_files") or []
        assert any("pipeline.py" in f for f in files)


def test_search_filter_outcome(tmp_shay, tmp_ledger):
    with patch.object(bl, "_shay_home", return_value=tmp_shay), \
         patch.object(bt, "_shay_home", return_value=tmp_shay):
        bl.capture_all(ledger_path=tmp_ledger, vault_dir=None)
        results = bl.search_ledger("builder", outcome="completed",
                                   ledger_path=tmp_ledger)
    assert all(r["outcome"] == "completed" for r in results)


def test_search_empty_before_capture(tmp_ledger):
    results = bl.search_ledger("anything", ledger_path=tmp_ledger)
    assert results == []


# ---------------------------------------------------------------------------
# print helpers (smoke)
# ---------------------------------------------------------------------------

def test_print_builds_list_no_crash(tmp_shay, tmp_ledger, capsys):
    with patch.object(bl, "_shay_home", return_value=tmp_shay), \
         patch.object(bt, "_shay_home", return_value=tmp_shay):
        bl.capture_all(ledger_path=tmp_ledger, vault_dir=None)
        builds = bl.list_builds(ledger_path=tmp_ledger)
    bl.print_builds_list(builds)
    out = capsys.readouterr().out
    assert "b_" in out


def test_print_build_detail_no_crash(tmp_shay, tmp_ledger, capsys):
    with patch.object(bl, "_shay_home", return_value=tmp_shay), \
         patch.object(bt, "_shay_home", return_value=tmp_shay):
        bl.capture_all(ledger_path=tmp_ledger, vault_dir=None)
        builds = bl.list_builds(ledger_path=tmp_ledger)
    bl.print_build_detail(builds[0])
    out = capsys.readouterr().out
    assert "BUILD" in out
