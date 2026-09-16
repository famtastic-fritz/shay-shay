from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "reconcile_shay_agent_trace.py"


def _ledger_row() -> dict:
    return {
        "schema_version": 2,
        "contract_revision": "non-synced-v3",
        "setup_attempt_id": "local-state-v3",
        "event_id": "SHAY-AGENT-PROGRAM:EXEC:E0001",
        "event_sequence": 1,
        "prior_event_id": None,
        "prior_line_sha256": None,
        "program_id": "SHAY-AGENT-ENHANCEMENT-2026-09-13",
        "requirement_id": None,
        "event_type": "execution_ledger_initialized",
        "recorded_at": "2026-09-14T01:41:21.888282Z",
        "actor_role": "setup_operator",
        "idempotency_key": "SHAY-AGENT-ENHANCEMENT-2026-09-13:PROGRAM:execution_ledger_initialized:singleton:none",
        "implementation_base_sha": None,
        "integration_base_sha": None,
        "candidate_binding": None,
        "review_result": None,
        "commit_ref": None,
        "remote_ref": None,
        "kanban_ref": None,
        "reconciliation_ref": None,
        "r8_snapshot_ref": None,
        "outcome": "initialized",
    }


def _write_ledger(path: Path, rows: list[dict]) -> None:
    previous = None
    encoded = []
    for sequence, row in enumerate(rows, 1):
        row = dict(row)
        row["event_sequence"] = sequence
        row["prior_event_id"] = None if previous is None else json.loads(previous)["event_id"]
        row["prior_line_sha256"] = None
        if previous is not None:
            import hashlib

            row["prior_line_sha256"] = hashlib.sha256(previous).hexdigest()
        current = json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
        encoded.append(current)
        previous = current
    path.write_bytes(b"\n".join(encoded) + b"\n")


def _write_board(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE tasks (id TEXT PRIMARY KEY, title TEXT NOT NULL, body TEXT,
          assignee TEXT, status TEXT NOT NULL, priority INTEGER, created_by TEXT,
          created_at INTEGER NOT NULL, started_at INTEGER, completed_at INTEGER,
          workspace_kind TEXT, workspace_path TEXT, claim_lock TEXT,
          claim_expires INTEGER, tenant TEXT, result TEXT, idempotency_key TEXT,
          consecutive_failures INTEGER, worker_pid INTEGER, last_failure_error TEXT,
          max_runtime_seconds INTEGER, last_heartbeat_at INTEGER, current_run_id INTEGER,
          workflow_template_id TEXT, current_step_key TEXT, skills TEXT, max_retries INTEGER);
        CREATE TABLE task_links (parent_id TEXT NOT NULL, child_id TEXT NOT NULL);
        CREATE TABLE task_comments (id INTEGER PRIMARY KEY, task_id TEXT, author TEXT, body TEXT, created_at INTEGER);
        CREATE TABLE task_events (id INTEGER PRIMARY KEY, task_id TEXT, run_id INTEGER, kind TEXT, payload TEXT, created_at INTEGER);
        CREATE TABLE task_runs (id INTEGER PRIMARY KEY, task_id TEXT, profile TEXT, step_key TEXT,
          status TEXT NOT NULL, claim_lock TEXT, claim_expires INTEGER, worker_pid INTEGER,
          max_runtime_seconds INTEGER, last_heartbeat_at INTEGER, started_at INTEGER NOT NULL,
          ended_at INTEGER, outcome TEXT, summary TEXT, metadata TEXT, error TEXT);
        """
    )
    titles = [
        "capability contract and trace freeze", "baseline and complete E2E stress gate",
        "read-only anti-drift reconciler", "durable lifecycle and API adapter",
        "typed safety and approval seam", "memory provenance and promotion",
        "shared client domain contract", "operator CLI and doctor UX", "canonical acceptance and finalization",
    ]
    ids = ["t_a87e0383", "t_b9500d49", "t_77168057", "t_1e889bd1", "t_3be22fbc", "t_aa326c83", "t_782fa6d4", "t_6157bc92", "t_c69ad3e0"]
    for i, (task_id, title) in enumerate(zip(ids, titles)):
        req = f"R{i}"
        conn.execute("INSERT INTO tasks (id,title,status,created_at,idempotency_key) VALUES (?,?,?,?,?)", (task_id, f"{req} - {title}", "done" if i == 0 else "todo", i + 1, f"SHAY-AGENT-ENHANCEMENT-2026-09-13:R{i}"))
        conn.execute("INSERT INTO task_events (id,task_id,kind,created_at) VALUES (?,?,?,?)", (i + 1, task_id, "created", i + 1))
    links = [(0, 1), (1, 2), (2, 3), (2, 4), (3, 5), (3, 6), (4, 5), (4, 6), (6, 7), (5, 8), (7, 8)]
    conn.executemany("INSERT INTO task_links VALUES (?,?)", [(ids[a], ids[b]) for a, b in links])
    conn.commit()
    conn.close()


def _run(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    (tmp_path / "docs/architecture").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs/architecture/shay-agent-enhancement-trace.jsonl").write_text(
        json.dumps({"event_id": "SHAY-AGENT-R0:E0001", "requirement_id": "SHAY-AGENT-R0", "event_revision": 1}) + "\n",
        encoding="utf-8",
    )
    return subprocess.run([sys.executable, str(SCRIPT), "--repo", str(tmp_path), "--ledger", str(tmp_path / "ledger.jsonl"), "--lock", str(tmp_path / "ledger.lock"), "--board-db", str(tmp_path / "board.db"), "--json"], text=True, capture_output=True)


def test_reconciliation_is_read_only_and_byte_deterministic(tmp_path):
    _write_ledger(tmp_path / "ledger.jsonl", [_ledger_row()])
    (tmp_path / "ledger.lock").touch()
    _write_board(tmp_path / "board.db")
    before = (tmp_path / "ledger.jsonl").read_bytes()
    first = _run(tmp_path)
    second = _run(tmp_path)
    assert first.returncode == 0, first.stderr + first.stdout
    assert first.stdout == second.stdout
    assert json.loads(first.stdout)["counts"]["total"] == 0
    assert (tmp_path / "ledger.jsonl").read_bytes() == before


def test_duplicate_json_key_fails_without_repair(tmp_path):
    _write_ledger(tmp_path / "ledger.jsonl", [_ledger_row()])
    raw = (tmp_path / "ledger.jsonl").read_bytes().replace(b'"outcome":"initialized"', b'"outcome":"initialized","outcome":"tampered"')
    (tmp_path / "ledger.jsonl").write_bytes(raw)
    (tmp_path / "ledger.lock").touch()
    _write_board(tmp_path / "board.db")
    result = _run(tmp_path)
    assert result.returncode != 0
    assert "ledger unreadable" in result.stdout
    assert (tmp_path / "ledger.jsonl").read_bytes() == raw


def test_orphan_run_is_reported_as_nonzero_drift(tmp_path):
    _write_ledger(tmp_path / "ledger.jsonl", [_ledger_row()])
    (tmp_path / "ledger.lock").touch()
    _write_board(tmp_path / "board.db")
    conn = sqlite3.connect(tmp_path / "board.db")
    conn.execute("INSERT INTO task_runs (id,task_id,status,started_at) VALUES (99,'missing-task','done',1)")
    conn.commit()
    conn.close()
    result = _run(tmp_path)
    payload = json.loads(result.stdout)
    assert result.returncode != 0
    assert payload["counts"]["orphans"] == 1
