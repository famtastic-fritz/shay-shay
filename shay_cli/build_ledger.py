"""Build Ledger — durable, append-only record of every Shay build run.

This module is the WRITE side of the Build Tracker system.
- Reads from task_runs across all board DBs (via build_tracker.load_all_runs)
- Writes ONLY to ~/.shay/build-ledger.db — never touches board DBs
- Mirrors each build as a per-build note under
  ~/famtastic/obsidian/Shay-Memory/builds/<build_id>.md

The ledger is NEVER GC'd. Boards can be deleted; the ledger survives.

Public API:
  capture_all()                   Mirror all completed runs into the ledger.
  search_ledger(query, ...)       Full-text + filter search.
  show_build(build_id)            Return full drilldown dict for one build.
  list_builds(...)                Paginated list with filters.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from shay_cli.build_tracker import (
    BuildRun,
    _all_board_dbs,
    _load_sessions_by_profile,
    _join_cost,
    _load_task_runs,
)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _shay_home() -> Path:
    env = os.environ.get("SHAY_HOME")
    if env:
        p = Path(env)
        if (p / "kanban.db").exists() or (p / "kanban").is_dir():
            return p
        parent = p.parent
        if (parent / "kanban.db").exists() or (parent / "kanban").is_dir():
            return parent
        return p
    return Path.home() / ".shay"


def _ledger_path() -> Path:
    return _shay_home() / "build-ledger.db"


def _real_home() -> Path:
    """Return the real user home, not the profile-sandboxed one."""
    # The kanban worker runs with HOME set to a profile sandbox.
    # Walk up from _shay_home() to find the real ~/.shay parent.
    shay = _shay_home()
    # ~/.shay is the real home's .shay dir; real home is shay.parent
    real = shay.parent
    if (real / "famtastic").exists() or (real / ".config").exists():
        return real
    # Fallback: check /Users dirs
    import pwd
    try:
        return Path(pwd.getpwuid(os.getuid()).pw_dir)
    except (KeyError, AttributeError):
        return Path.home()


def _vault_builds_dir() -> Optional[Path]:
    """Best-effort: find ~/famtastic/obsidian/Shay-Memory/builds/."""
    real_home = _real_home()
    candidates = [
        real_home / "famtastic" / "obsidian" / "Shay-Memory" / "builds",
        real_home / "obsidian" / "Shay-Memory" / "builds",
        Path.home() / "famtastic" / "obsidian" / "Shay-Memory" / "builds",
    ]
    for c in candidates:
        if c.parent.exists():
            c.mkdir(parents=True, exist_ok=True)
            return c
    return None


# ---------------------------------------------------------------------------
# Schema + setup
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS builds (
    build_id         TEXT PRIMARY KEY,   -- sha256 of board+run_id (stable, deterministic)
    board            TEXT NOT NULL,
    run_id           INTEGER NOT NULL,
    task_id          TEXT NOT NULL,
    task_title       TEXT,
    profile          TEXT,
    outcome          TEXT,
    started_at       INTEGER,
    ended_at         INTEGER,
    duration_s       REAL,
    summary          TEXT,
    error            TEXT,
    error_signature  TEXT,               -- normalized so identical errors cluster
    tests_run        INTEGER DEFAULT 0,
    tests_passed     INTEGER DEFAULT 0,
    gate_bypass      INTEGER DEFAULT 0,  -- 1 if tests_run=0 but changed_files non-empty
    protocol_violation INTEGER DEFAULT 0,
    changed_files    TEXT,               -- JSON array
    decisions        TEXT,               -- JSON array
    model            TEXT,
    billing_provider TEXT,
    cost_usd         REAL,
    loop_run_count   INTEGER,            -- from metadata, present when H3 is live
    rungs_climbed    TEXT,               -- JSON array
    escalation_trail TEXT,               -- JSON blob
    captured_at      INTEGER NOT NULL,   -- when we wrote this ledger row
    UNIQUE(board, run_id)
);

CREATE VIRTUAL TABLE IF NOT EXISTS builds_fts USING fts5(
    build_id,
    task_id,
    task_title,
    summary,
    error,
    error_signature,
    changed_files,
    decisions,
    content='builds',
    content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS builds_ai AFTER INSERT ON builds BEGIN
    INSERT INTO builds_fts(rowid, build_id, task_id, task_title, summary, error, error_signature, changed_files, decisions)
    VALUES (new.rowid, new.build_id, new.task_id, new.task_title, new.summary, new.error, new.error_signature, new.changed_files, new.decisions);
END;

CREATE TRIGGER IF NOT EXISTS builds_ad AFTER DELETE ON builds BEGIN
    INSERT INTO builds_fts(builds_fts, rowid, build_id, task_id, task_title, summary, error, error_signature, changed_files, decisions)
    VALUES ('delete', old.rowid, old.build_id, old.task_id, old.task_title, old.summary, old.error, old.error_signature, old.changed_files, old.decisions);
END;

CREATE TRIGGER IF NOT EXISTS builds_au AFTER UPDATE ON builds BEGIN
    INSERT INTO builds_fts(builds_fts, rowid, build_id, task_id, task_title, summary, error, error_signature, changed_files, decisions)
    VALUES ('delete', old.rowid, old.build_id, old.task_id, old.task_title, old.summary, old.error, old.error_signature, old.changed_files, old.decisions);
    INSERT INTO builds_fts(rowid, build_id, task_id, task_title, summary, error, error_signature, changed_files, decisions)
    VALUES (new.rowid, new.build_id, new.task_id, new.task_title, new.summary, new.error, new.error_signature, new.changed_files, new.decisions);
END;
"""


def _open_ledger(path: Optional[Path] = None, readonly: bool = False) -> sqlite3.Connection:
    ledger = path or _ledger_path()
    if readonly:
        uri = f"file:{ledger}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    else:
        conn = sqlite3.connect(str(ledger), check_same_thread=False)
        conn.executescript(_SCHEMA_SQL)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Build ID + error normalization
# ---------------------------------------------------------------------------

def _build_id(board: str, run_id: int) -> str:
    """Deterministic build_id — sha256(board:run_id), first 16 hex chars."""
    raw = f"{board}:{run_id}"
    return "b_" + hashlib.sha256(raw.encode()).hexdigest()[:14]


def _normalize_error(error: Optional[str]) -> Optional[str]:
    """Strip variable parts (PIDs, timestamps, hex IDs) so identical errors cluster."""
    if not error:
        return None
    s = error.strip()
    # Strip leading/trailing whitespace lines
    s = re.sub(r'\n+', ' ', s)
    # Remove hex IDs (8+ hex chars)
    s = re.sub(r'\b[0-9a-f]{8,}\b', '<HEX>', s)
    # Remove numeric PID-like values
    s = re.sub(r'\bpid[=: ]+\d+\b', 'pid=<PID>', s, flags=re.IGNORECASE)
    # Remove timestamps like 2026-05-31 23:41
    s = re.sub(r'\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?', '<TS>', s)
    # Collapse to first 200 chars for the signature
    return s[:200]


def _task_title_for(board_db: Path, task_id: str) -> Optional[str]:
    """Best-effort: read title from tasks table."""
    try:
        uri = f"file:{board_db}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        cur = conn.execute("SELECT title FROM tasks WHERE id = ?", (task_id,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None
    except sqlite3.Error:
        return None


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------

def _run_to_row(run: BuildRun, board_db: Path) -> Dict[str, Any]:
    """Convert a BuildRun to a ledger row dict."""
    meta = run.metadata or {}
    loop_run_count = meta.get("loop_run_count") or meta.get("runs") or None
    rungs = meta.get("rungs_climbed") or meta.get("escalation_rungs") or []
    escalation = meta.get("escalation_trail") or []

    return {
        "build_id": _build_id(run.board, run.run_id),
        "board": run.board,
        "run_id": run.run_id,
        "task_id": run.task_id,
        "task_title": _task_title_for(board_db, run.task_id),
        "profile": run.profile,
        "outcome": run.outcome,
        "started_at": run.started_at,
        "ended_at": run.ended_at,
        "duration_s": run.duration_s,
        "summary": run.summary,
        "error": run.error,
        "error_signature": _normalize_error(run.error),
        "tests_run": run.tests_run,
        "tests_passed": run.tests_passed,
        "gate_bypass": int(run.gate_bypass),
        "protocol_violation": int(run.protocol_violation),
        "changed_files": json.dumps(run.changed_files),
        "decisions": json.dumps(meta.get("decisions") or []),
        "model": run.model,
        "billing_provider": run.billing_provider,
        "cost_usd": run.estimated_cost_usd,
        "loop_run_count": loop_run_count,
        "rungs_climbed": json.dumps(rungs) if rungs else None,
        "escalation_trail": json.dumps(escalation) if escalation else None,
        "captured_at": int(time.time()),
    }


def _write_vault_note(row: Dict[str, Any], vault_dir: Optional[Path]) -> None:
    """Write a per-build summary note to the Obsidian vault."""
    if vault_dir is None:
        return
    vault_dir.mkdir(parents=True, exist_ok=True)
    build_id = row["build_id"]
    note_path = vault_dir / f"{build_id}.md"
    if note_path.exists():
        return  # already mirrored

    ts = ""
    if row.get("started_at"):
        ts = datetime.fromtimestamp(row["started_at"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    dur = ""
    if row.get("duration_s"):
        d = row["duration_s"]
        dur = f"{d/60:.1f}m" if d >= 60 else f"{d:.0f}s"

    files = []
    try:
        files = json.loads(row.get("changed_files") or "[]")
    except (json.JSONDecodeError, TypeError):
        pass

    decisions = []
    try:
        decisions = json.loads(row.get("decisions") or "[]")
    except (json.JSONDecodeError, TypeError):
        pass

    flags = []
    if row.get("gate_bypass"):
        flags.append("GATE-BYPASS")
    if row.get("protocol_violation"):
        flags.append("PROTOCOL-VIOLATION")

    lines = [
        "---",
        f"title: {build_id}",
        "type: build",
        f"tags: [builds, {row.get('outcome', 'unknown')}, {row.get('profile', 'unknown')}]",
        "---",
        "",
        f"# Build {build_id}",
        "",
        f"**Task:** {row.get('task_id')} — {row.get('task_title') or '(no title)'}",
        f"**Board:** {row.get('board')}",
        f"**Profile:** {row.get('profile')}",
        f"**Outcome:** {row.get('outcome')}",
        f"**Started:** {ts}",
        f"**Duration:** {dur}",
    ]
    if row.get("model"):
        lines.append(f"**Brain:** {row['model']}")
    if row.get("cost_usd") is not None:
        lines.append(f"**Cost:** ${row['cost_usd']:.4f}")
    if flags:
        lines.append(f"**Flags:** {', '.join(flags)}")
    lines.append("")

    if row.get("summary"):
        lines += ["## Summary", "", row["summary"], ""]

    if row.get("error"):
        lines += ["## Error", "", f"```", row["error"][:1000], "```", ""]

    if files:
        lines += ["## Changed Files", ""]
        for f in files:
            lines.append(f"- {f}")
        lines.append("")

    if decisions:
        lines += ["## Decisions", ""]
        for d in decisions:
            lines.append(f"- {d}")
        lines.append("")

    if row.get("tests_run", 0) > 0:
        rate = int(100 * row["tests_passed"] / row["tests_run"])
        lines += ["## Gate Results", "",
                  f"- tests_run: {row['tests_run']}",
                  f"- tests_passed: {row['tests_passed']}",
                  f"- pass_rate: {rate}%",
                  ""]

    note_path.write_text("\n".join(lines), encoding="utf-8")


def capture_all(ledger_path: Optional[Path] = None,
                vault_dir: Optional[Path] = None) -> Dict[str, int]:
    """
    Mirror all completed task_runs into build-ledger.db.
    Returns {"new": N, "skipped": N}.
    Idempotent — will not double-insert.
    """
    resolved_vault = vault_dir if vault_dir is not None else _vault_builds_dir()
    conn = _open_ledger(ledger_path)

    new_count = 0
    skipped_count = 0

    for board_slug, db_path in _all_board_dbs():
        runs = _load_task_runs(board_slug, db_path, since_ts=None)
        # Cost join
        sessions_by_profile = _load_sessions_by_profile()
        _join_cost(runs, sessions_by_profile)

        for run in runs:
            bid = _build_id(run.board, run.run_id)
            # Check idempotency
            exists = conn.execute(
                "SELECT 1 FROM builds WHERE build_id = ?", (bid,)
            ).fetchone()

            row = _run_to_row(run, db_path)

            if exists:
                skipped_count += 1
                # Still write vault note if it's missing
                _write_vault_note(row, resolved_vault)
                continue

            conn.execute(
                """
                INSERT OR IGNORE INTO builds
                    (build_id, board, run_id, task_id, task_title, profile,
                     outcome, started_at, ended_at, duration_s,
                     summary, error, error_signature,
                     tests_run, tests_passed, gate_bypass, protocol_violation,
                     changed_files, decisions, model, billing_provider, cost_usd,
                     loop_run_count, rungs_climbed, escalation_trail, captured_at)
                VALUES
                    (:build_id, :board, :run_id, :task_id, :task_title, :profile,
                     :outcome, :started_at, :ended_at, :duration_s,
                     :summary, :error, :error_signature,
                     :tests_run, :tests_passed, :gate_bypass, :protocol_violation,
                     :changed_files, :decisions, :model, :billing_provider, :cost_usd,
                     :loop_run_count, :rungs_climbed, :escalation_trail, :captured_at)
                """,
                row,
            )
            conn.commit()
            new_count += 1
            _write_vault_note(row, resolved_vault)

    conn.close()
    return {"new": new_count, "skipped": skipped_count}


# ---------------------------------------------------------------------------
# Search + List + Show
# ---------------------------------------------------------------------------

def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    for field in ("changed_files", "decisions", "rungs_climbed", "escalation_trail"):
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


def list_builds(
    since_hours: Optional[float] = None,
    outcome: Optional[str] = None,
    profile: Optional[str] = None,
    board: Optional[str] = None,
    limit: int = 50,
    ledger_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Return a list of builds (most-recent first), with optional filters."""
    try:
        conn = _open_ledger(ledger_path, readonly=True)
    except sqlite3.OperationalError:
        return []

    conditions = []
    params: List[Any] = []

    if since_hours is not None:
        since_ts = int(time.time() - since_hours * 3600)
        conditions.append("started_at >= ?")
        params.append(since_ts)
    if outcome:
        conditions.append("outcome = ?")
        params.append(outcome)
    if profile:
        conditions.append("profile = ?")
        params.append(profile)
    if board:
        conditions.append("board = ?")
        params.append(board)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params.append(limit)

    try:
        cur = conn.execute(
            f"SELECT * FROM builds {where} ORDER BY started_at DESC LIMIT ?", params
        )
        rows = [_row_to_dict(r) for r in cur.fetchall()]
    except sqlite3.Error:
        rows = []
    conn.close()
    return rows


def show_build(build_id: str, ledger_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Return full drilldown dict for a single build, or None if not found."""
    try:
        conn = _open_ledger(ledger_path, readonly=True)
    except sqlite3.OperationalError:
        return None

    try:
        cur = conn.execute("SELECT * FROM builds WHERE build_id = ?", (build_id,))
        row = cur.fetchone()
        result = _row_to_dict(row) if row else None
    except sqlite3.Error:
        result = None
    conn.close()
    return result


def search_ledger(
    query: str,
    outcome: Optional[str] = None,
    profile: Optional[str] = None,
    board: Optional[str] = None,
    error_signature: Optional[str] = None,
    file_touched: Optional[str] = None,
    since_hours: Optional[float] = None,
    limit: int = 50,
    ledger_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Full-text search over builds.
    query: free-text matched against summary, error, title, changed_files, decisions
    Filters can be combined freely.
    """
    try:
        conn = _open_ledger(ledger_path, readonly=True)
    except sqlite3.OperationalError:
        return []

    results: List[Dict[str, Any]] = []
    try:
        # FTS match over the virtual table
        fts_query = query.replace('"', '""')  # basic escaping
        fts_sql = """
            SELECT b.*
            FROM builds b
            JOIN builds_fts f ON b.rowid = f.rowid
            WHERE builds_fts MATCH ?
            ORDER BY b.started_at DESC
        """
        cur = conn.execute(fts_sql, (fts_query,))
        rows = [_row_to_dict(r) for r in cur.fetchall()]
    except sqlite3.OperationalError:
        # FTS table may not exist (read-only open before first write)
        rows = []
        # Fall back: simple LIKE search
        try:
            pat = f"%{query}%"
            cur = conn.execute(
                """SELECT * FROM builds
                   WHERE summary LIKE ? OR error LIKE ? OR task_title LIKE ?
                   OR changed_files LIKE ? OR decisions LIKE ?
                   ORDER BY started_at DESC""",
                (pat, pat, pat, pat, pat)
            )
            rows = [_row_to_dict(r) for r in cur.fetchall()]
        except sqlite3.Error:
            pass

    conn.close()

    # Post-filter
    if outcome:
        rows = [r for r in rows if r.get("outcome") == outcome]
    if profile:
        rows = [r for r in rows if r.get("profile") == profile]
    if board:
        rows = [r for r in rows if r.get("board") == board]
    if error_signature:
        rows = [r for r in rows if error_signature.lower() in (r.get("error_signature") or "").lower()]
    if file_touched:
        rows = [r for r in rows
                if any(file_touched in (f or "") for f in (r.get("changed_files") or []))]
    if since_hours is not None:
        since_ts = int(time.time() - since_hours * 3600)
        rows = [r for r in rows if (r.get("started_at") or 0) >= since_ts]

    return rows[:limit]


# ---------------------------------------------------------------------------
# CLI formatting helpers
# ---------------------------------------------------------------------------

def _fmt_ts(ts: Optional[int]) -> str:
    if not ts:
        return "?"
    return datetime.fromtimestamp(ts).strftime("%m-%d %H:%M")


def _fmt_dur(s: Optional[float]) -> str:
    if s is None:
        return "n/a"
    return f"{s/60:.1f}m" if s >= 60 else f"{s:.0f}s"


def _fmt_cost(v: Optional[float]) -> str:
    if v is None:
        return "n/a"
    return f"${v:.4f}"


def print_builds_list(builds: List[Dict[str, Any]]) -> None:
    if not builds:
        print("  No builds found.")
        return
    header = f"{'BUILD_ID':<18}  {'STARTED':<12}  {'BOARD':<12}  {'TASK':<12}  {'OUTCOME':<12}  {'DUR':>6}  {'COST':>7}  FLAGS"
    print(header)
    print("-" * len(header))
    for b in builds:
        flags = []
        if b.get("gate_bypass"):
            flags.append("BYPASS")
        if b.get("protocol_violation"):
            flags.append("PVIOLN")
        bid = (b.get("build_id") or "")[:18]
        board = (b.get("board") or "")[:12]
        task = (b.get("task_id") or "")[:12]
        outcome = (b.get("outcome") or "")[:12]
        print(
            f"{bid:<18}  {_fmt_ts(b.get('started_at')):<12}  {board:<12}  "
            f"{task:<12}  {outcome:<12}  {_fmt_dur(b.get('duration_s')):>6}  "
            f"{_fmt_cost(b.get('cost_usd')):>7}  {' '.join(flags)}"
        )
    print()


def print_build_detail(b: Dict[str, Any]) -> None:
    print(f"\n{'='*64}")
    print(f"  BUILD {b.get('build_id')}")
    print(f"{'='*64}")
    print(f"  Task    : {b.get('task_id')} — {b.get('task_title') or '(no title)'}")
    print(f"  Board   : {b.get('board')}")
    print(f"  Profile : {b.get('profile')}")
    print(f"  Outcome : {b.get('outcome')}")
    print(f"  Started : {_fmt_ts(b.get('started_at'))}")
    print(f"  Duration: {_fmt_dur(b.get('duration_s'))}")
    if b.get("model"):
        print(f"  Brain   : {b['model']}")
    if b.get("cost_usd") is not None:
        print(f"  Cost    : {_fmt_cost(b.get('cost_usd'))}")

    flags = []
    if b.get("gate_bypass"):
        flags.append("GATE-BYPASS")
    if b.get("protocol_violation"):
        flags.append("PROTOCOL-VIOLATION")
    if flags:
        print(f"  Flags   : {', '.join(flags)}")

    print()
    if b.get("summary"):
        print("SUMMARY:")
        print(f"  {b['summary']}")
        print()

    files = b.get("changed_files") or []
    if files:
        print("CHANGED FILES:")
        for f in files:
            print(f"  {f}")
        print()

    decisions = b.get("decisions") or []
    if decisions:
        print("DECISIONS:")
        for d in decisions:
            print(f"  - {d}")
        print()

    if b.get("tests_run", 0) > 0:
        rate = int(100 * b["tests_passed"] / b["tests_run"])
        print(f"TESTS: {b['tests_passed']}/{b['tests_run']} ({rate}%)")
        print()

    if b.get("error"):
        print("ERROR:")
        err = b["error"]
        if len(err) > 800:
            err = err[:800] + "\n... (truncated)"
        print(f"  {err}")
        print()

    if b.get("error_signature"):
        print(f"ERROR SIGNATURE: {b['error_signature'][:100]}")
        print()
