"""Tests for shay_cli.build_tracker — read-only aggregation module."""
import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure we can import from the shay-shay repo
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

import shay_cli.build_tracker as bt


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_kanban_dir(tmp_path):
    """Create a minimal ~/.shay-like directory with board DBs + profile state DBs."""
    shay_home = tmp_path / "shay"
    shay_home.mkdir()

    # Board: masterplan
    board_dir = shay_home / "kanban" / "boards" / "masterplan"
    board_dir.mkdir(parents=True)
    db_path = board_dir / "kanban.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
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

    base_ts = int(time.time()) - 3600

    rows = [
        # protocol violation
        ("t_aaa", "builder", "done", "crashed",
         base_ts, base_ts + 120,
         json.dumps({"pid": 100, "exit_code": 0}),
         "worker exited cleanly (rc=0) without calling kanban_complete or kanban_block — protocol violation"),
        # gate bypass: completed, tests_run=0, changed_files set
        ("t_bbb", "builder", "done", "completed",
         base_ts + 200, base_ts + 560,
         json.dumps({"tests_run": 0, "tests_passed": 0, "changed_files": ["/foo/bar.py"]}),
         None),
        # normal success with tests
        ("t_ccc", "builder", "done", "completed",
         base_ts + 600, base_ts + 900,
         json.dumps({"tests_run": 10, "tests_passed": 9, "changed_files": ["/baz.py"]}),
         None),
        # timeout
        ("t_ddd", "builder", "done", "timed_out",
         base_ts + 1000, base_ts + 2700,
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

    # Profile: builder state.db with sessions
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
        ("sess_001", "cli", "claude-sonnet-4", "anthropic", 0.42,
         1000, 5000, float(base_ts + 190), float(base_ts + 600)),
    )
    sconn.commit()
    sconn.close()

    return shay_home


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_load_all_runs_returns_list(tmp_kanban_dir):
    with patch.object(bt, "_shay_home", return_value=tmp_kanban_dir):
        runs = bt.load_all_runs()
    assert isinstance(runs, list)
    assert len(runs) == 4


def test_protocol_violation_flagged(tmp_kanban_dir):
    with patch.object(bt, "_shay_home", return_value=tmp_kanban_dir):
        runs = bt.load_all_runs()
    pv = [r for r in runs if r.protocol_violation]
    assert len(pv) == 1
    assert pv[0].task_id == "t_aaa"


def test_gate_bypass_flagged(tmp_kanban_dir):
    with patch.object(bt, "_shay_home", return_value=tmp_kanban_dir):
        runs = bt.load_all_runs()
    gb = [r for r in runs if r.gate_bypass]
    assert len(gb) == 1
    assert gb[0].task_id == "t_bbb"


def test_non_bypass_with_tests(tmp_kanban_dir):
    """Completed run with tests_run > 0 should NOT be flagged as bypass."""
    with patch.object(bt, "_shay_home", return_value=tmp_kanban_dir):
        runs = bt.load_all_runs()
    ccc = next(r for r in runs if r.task_id == "t_ccc")
    assert not ccc.gate_bypass
    assert ccc.tests_run == 10
    assert ccc.tests_passed == 9


def test_duration_computed(tmp_kanban_dir):
    with patch.object(bt, "_shay_home", return_value=tmp_kanban_dir):
        runs = bt.load_all_runs()
    aaa = next(r for r in runs if r.task_id == "t_aaa")
    assert aaa.duration_s == pytest.approx(120.0)


def test_cost_joined(tmp_kanban_dir):
    """The completed run that overlaps with the session should get cost attached."""
    with patch.object(bt, "_shay_home", return_value=tmp_kanban_dir):
        runs = bt.load_all_runs()
    # t_bbb overlaps with our session (base+200 to base+560, session base+190 to base+600)
    bbb = next(r for r in runs if r.task_id == "t_bbb")
    assert bbb.estimated_cost_usd == pytest.approx(0.42)
    assert bbb.model == "claude-sonnet-4"


def test_aggregate_brain_stats(tmp_kanban_dir):
    with patch.object(bt, "_shay_home", return_value=tmp_kanban_dir):
        runs = bt.load_all_runs()
    stats = bt.aggregate_by_brain(runs)
    assert "unknown" in stats or "claude-sonnet-4" in stats
    # Overall: 4 runs, t_bbb completed (cost joined, model set), others unknown
    all_totals = sum(s.total for s in stats.values())
    assert all_totals == 4


def test_since_hours_filter(tmp_kanban_dir):
    """since_hours=0.0001 should return nothing (all runs older)."""
    with patch.object(bt, "_shay_home", return_value=tmp_kanban_dir):
        runs_all = bt.load_all_runs(since_hours=None)
        runs_fresh = bt.load_all_runs(since_hours=0.0001)
    assert len(runs_all) == 4
    assert len(runs_fresh) == 0


def test_print_summary_no_crash(tmp_kanban_dir, capsys):
    with patch.object(bt, "_shay_home", return_value=tmp_kanban_dir):
        runs = bt.load_all_runs()
    bt.print_summary(runs, verbose=True)
    captured = capsys.readouterr()
    assert "SHAY BUILDS SUMMARY" in captured.out
    assert "GATE-BYPASS SMELL" in captured.out
    assert "protocol-violations" in captured.out


def test_success_rate_math(tmp_kanban_dir):
    with patch.object(bt, "_shay_home", return_value=tmp_kanban_dir):
        runs = bt.load_all_runs()
    # 2 completed (t_bbb, t_ccc), 1 crashed (t_aaa), 1 timed_out (t_ddd) = 50% success
    stats = bt.aggregate_by_brain(runs)
    total_completed = sum(s.completed for s in stats.values())
    total_runs = sum(s.total for s in stats.values())
    assert total_completed == 2
    assert total_runs == 4


def test_all_board_dbs_finds_masterplan(tmp_kanban_dir):
    with patch.object(bt, "_shay_home", return_value=tmp_kanban_dir):
        boards = bt._all_board_dbs()
    slugs = [slug for slug, _ in boards]
    assert "masterplan" in slugs


def test_profile_state_dbs_finds_builder(tmp_kanban_dir):
    with patch.object(bt, "_shay_home", return_value=tmp_kanban_dir):
        dbs = bt._profile_state_dbs()
    assert "builder" in dbs
