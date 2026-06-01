"""Build Tracker — aggregate task_runs + session cost data for 'shay builds'.

READ-ONLY aggregation module. Does NOT modify any run-recording path.

Data sources:
  - task_runs table: ~/.shay/kanban/boards/*/kanban.db + ~/.shay/kanban.db
  - sessions table: ~/.shay/profiles/<profile>/state.db (cost/model data)

CLI: shay builds [--since N] [--by brain] [--board SLUG] [--verbose]
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _shay_home() -> Path:
    """Resolve the real Shay home (not the profile-sandboxed one)."""
    env = os.environ.get("SHAY_HOME")
    if env:
        p = Path(env)
        # SHAY_HOME may be the profile dir; real home is one level up
        if (p / "kanban.db").exists() or (p / "kanban").is_dir():
            return p
        parent = p.parent
        if (parent / "kanban.db").exists() or (parent / "kanban").is_dir():
            return parent
        return p
    return Path.home() / ".shay"


def _all_board_dbs() -> List[Tuple[str, Path]]:
    """Return [(board_slug, db_path), ...] for all board databases."""
    home = _shay_home()
    results: List[Tuple[str, Path]] = []

    # Legacy default board
    legacy = home / "kanban.db"
    if legacy.exists():
        results.append(("default", legacy))

    # Named boards
    boards_dir = home / "kanban" / "boards"
    if boards_dir.is_dir():
        for board_dir in sorted(boards_dir.iterdir()):
            db = board_dir / "kanban.db"
            if db.exists():
                results.append((board_dir.name, db))

    return results


def _profile_state_dbs() -> Dict[str, Path]:
    """Return {profile_name: state_db_path} for all profiles."""
    home = _shay_home()
    profiles_dir = home / "profiles"
    result: Dict[str, Path] = {}
    if profiles_dir.is_dir():
        for profile_dir in sorted(profiles_dir.iterdir()):
            db = profile_dir / "state.db"
            if db.exists():
                result[profile_dir.name] = db
    return result


def _connect_ro(path: Path) -> sqlite3.Connection:
    """Open an SQLite DB in read-only mode."""
    uri = f"file:{path}?mode=ro"
    return sqlite3.connect(uri, uri=True, check_same_thread=False)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class BuildRun:
    run_id: int
    task_id: str
    board: str
    profile: str
    status: str
    outcome: Optional[str]
    started_at: int
    ended_at: Optional[int]
    duration_s: Optional[float]
    summary: Optional[str]
    metadata: dict
    error: Optional[str]
    # Parsed from metadata JSON
    tests_run: int = 0
    tests_passed: int = 0
    changed_files: List[str] = field(default_factory=list)
    # From session join
    model: Optional[str] = None
    billing_provider: Optional[str] = None
    estimated_cost_usd: Optional[float] = None
    # Computed smell flags
    gate_bypass: bool = False       # completed but tests_run == 0
    protocol_violation: bool = False  # crashed with "protocol violation" error


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_task_runs(board_slug: str, db_path: Path,
                    since_ts: Optional[int] = None) -> List[BuildRun]:
    """Load task_runs from a single board DB."""
    runs: List[BuildRun] = []
    try:
        conn = _connect_ro(db_path)
        cur = conn.cursor()
        sql = """
            SELECT id, task_id, profile, status, outcome,
                   started_at, ended_at, summary, metadata, error
            FROM task_runs
            WHERE ended_at IS NOT NULL
        """
        params: List = []
        if since_ts is not None:
            sql += " AND started_at >= ?"
            params.append(since_ts)
        sql += " ORDER BY started_at ASC"
        cur.execute(sql, params)
        for row in cur.fetchall():
            (run_id, task_id, profile, status, outcome,
             started_at, ended_at, summary, metadata_json, error) = row

            meta: dict = {}
            if metadata_json:
                try:
                    meta = json.loads(metadata_json)
                except (json.JSONDecodeError, TypeError):
                    pass

            duration = None
            if started_at and ended_at:
                duration = float(ended_at - started_at)

            tests_run = int(meta.get("tests_run") or 0)
            tests_passed = int(meta.get("tests_passed") or 0)
            changed_files = meta.get("changed_files") or []

            proto_viol = bool(
                error and "protocol violation" in error.lower()
            )
            gate_bypass = bool(
                outcome == "completed"
                and tests_run == 0
                and changed_files  # changed files but no tests
            )

            runs.append(BuildRun(
                run_id=run_id,
                task_id=task_id,
                board=board_slug,
                profile=profile or "unknown",
                status=status,
                outcome=outcome,
                started_at=started_at,
                ended_at=ended_at,
                duration_s=duration,
                summary=summary,
                metadata=meta,
                error=error,
                tests_run=tests_run,
                tests_passed=tests_passed,
                changed_files=changed_files if isinstance(changed_files, list) else [],
                gate_bypass=gate_bypass,
                protocol_violation=proto_viol,
            ))
        conn.close()
    except sqlite3.Error:
        pass
    return runs


def _load_sessions_by_profile(since_ts: Optional[int] = None) -> Dict[str, List[dict]]:
    """Return {profile: [session_row, ...]} from each profile's state.db."""
    result: Dict[str, List[dict]] = {}
    for profile, db_path in _profile_state_dbs().items():
        try:
            conn = _connect_ro(db_path)
            cur = conn.cursor()
            sql = """
                SELECT id, model, billing_provider, estimated_cost_usd,
                       input_tokens, output_tokens, started_at, ended_at
                FROM sessions
                WHERE ended_at IS NOT NULL
            """
            params: List = []
            if since_ts is not None:
                sql += " AND started_at >= ?"
                params.append(float(since_ts))
            cur.execute(sql, params)
            rows = []
            for row in cur.fetchall():
                rows.append({
                    "id": row[0],
                    "model": row[1],
                    "billing_provider": row[2],
                    "estimated_cost_usd": row[3],
                    "input_tokens": row[4],
                    "output_tokens": row[5],
                    "started_at": row[6],
                    "ended_at": row[7],
                })
            result[profile] = rows
            conn.close()
        except sqlite3.Error:
            result[profile] = []
    return result


def _join_cost(runs: List[BuildRun], sessions_by_profile: Dict[str, List[dict]]) -> None:
    """Mutate runs in-place: attach model/cost from the matching session."""
    for run in runs:
        profile_sessions = sessions_by_profile.get(run.profile, [])
        if not profile_sessions:
            continue
        # Find sessions that overlapped with this task run
        best: Optional[dict] = None
        best_overlap: float = -1.0
        for sess in profile_sessions:
            sess_start = float(sess["started_at"])
            sess_end = float(sess["ended_at"] or 0)
            run_start = float(run.started_at)
            run_end = float(run.ended_at or run.started_at)
            overlap_start = max(sess_start, run_start)
            overlap_end = min(sess_end, run_end)
            overlap = overlap_end - overlap_start
            if overlap > best_overlap:
                best_overlap = overlap
                best = sess
        if best and best_overlap > 0:
            run.model = best["model"]
            run.billing_provider = best["billing_provider"]
            run.estimated_cost_usd = best["estimated_cost_usd"]


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

@dataclass
class BrainStats:
    brain: str          # model name or billing_provider
    total: int = 0
    completed: int = 0
    protocol_violations: int = 0
    gate_bypasses: int = 0
    timeouts: int = 0
    crashes: int = 0
    gate_fails: int = 0  # blocked with "gate" in summary
    durations: List[float] = field(default_factory=list)
    costs: List[float] = field(default_factory=list)
    tests_runs: List[int] = field(default_factory=list)
    tests_passed_list: List[int] = field(default_factory=list)
    # For regression detection: ordered outcomes (1=success, 0=fail)
    outcome_series: List[int] = field(default_factory=list)
    duration_series: List[float] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return self.completed / self.total if self.total else 0.0

    @property
    def failure_rate(self) -> float:
        return 1.0 - self.success_rate

    @property
    def protocol_violation_rate(self) -> float:
        return self.protocol_violations / self.total if self.total else 0.0

    @property
    def gate_bypass_rate(self) -> float:
        return self.gate_bypasses / self.total if self.total else 0.0

    @property
    def avg_duration(self) -> Optional[float]:
        return statistics.mean(self.durations) if self.durations else None

    @property
    def p50_duration(self) -> Optional[float]:
        return statistics.median(self.durations) if self.durations else None

    @property
    def p95_duration(self) -> Optional[float]:
        if len(self.durations) < 2:
            return self.durations[0] if self.durations else None
        s = sorted(self.durations)
        idx = int(len(s) * 0.95)
        return s[min(idx, len(s) - 1)]

    @property
    def avg_cost(self) -> Optional[float]:
        return statistics.mean(self.costs) if self.costs else None

    @property
    def test_pass_rate(self) -> Optional[float]:
        total_tests = sum(self.tests_runs)
        total_passed = sum(self.tests_passed_list)
        if total_tests == 0:
            return None
        return total_passed / total_tests

    @property
    def regression_flag(self) -> bool:
        """True if recent failure rate or runtime is worse than trailing avg."""
        window = 3
        if len(self.outcome_series) < window + 2:
            return False
        recent_fail_rate = 1.0 - (sum(self.outcome_series[-window:]) / window)
        trail_fail_rate = 1.0 - (sum(self.outcome_series[:-window]) / len(self.outcome_series[:-window]))
        fail_regression = recent_fail_rate > trail_fail_rate * 1.25

        dur_regression = False
        if len(self.duration_series) >= window + 2:
            recent_dur = statistics.mean(self.duration_series[-window:])
            trail_dur = statistics.mean(self.duration_series[:-window])
            dur_regression = recent_dur > trail_dur * 1.25

        return fail_regression or dur_regression


def _classify_failure_mode(run: BuildRun) -> str:
    if run.protocol_violation:
        return "protocol-violation"
    if run.outcome == "timed_out":
        return "timeout"
    if run.outcome == "crashed":
        return "crash"
    if run.outcome == "blocked":
        summary_lower = (run.summary or "").lower()
        if "gate" in summary_lower or "test" in summary_lower:
            return "gate-fail"
        return "blocked"
    return "other"


def aggregate_by_brain(runs: List[BuildRun]) -> Dict[str, BrainStats]:
    """Group runs by brain (model), return aggregated stats."""
    stats: Dict[str, BrainStats] = {}

    for run in runs:
        brain = run.model or run.billing_provider or "unknown"
        if brain not in stats:
            stats[brain] = BrainStats(brain=brain)
        s = stats[brain]
        s.total += 1

        if run.outcome == "completed":
            s.completed += 1
            s.outcome_series.append(1)
        else:
            s.outcome_series.append(0)

        if run.protocol_violation:
            s.protocol_violations += 1
        if run.gate_bypass:
            s.gate_bypasses += 1
        if run.outcome == "timed_out":
            s.timeouts += 1
        if run.outcome == "crashed" and not run.protocol_violation:
            s.crashes += 1
        if run.outcome == "blocked":
            summary_lower = (run.summary or "").lower()
            if "gate" in summary_lower or "test" in summary_lower:
                s.gate_fails += 1

        if run.duration_s is not None:
            s.durations.append(run.duration_s)
            s.duration_series.append(run.duration_s)

        if run.estimated_cost_usd is not None:
            s.costs.append(run.estimated_cost_usd)

        if run.tests_run > 0:
            s.tests_runs.append(run.tests_run)
            s.tests_passed_list.append(run.tests_passed)

    return stats


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_all_runs(since_hours: Optional[float] = None,
                  board_filter: Optional[str] = None) -> List[BuildRun]:
    """Load and return all BuildRun records, optionally filtered."""
    since_ts: Optional[int] = None
    if since_hours is not None:
        since_ts = int(time.time() - since_hours * 3600)

    all_runs: List[BuildRun] = []
    for board_slug, db_path in _all_board_dbs():
        if board_filter and board_slug != board_filter:
            continue
        runs = _load_task_runs(board_slug, db_path, since_ts=since_ts)
        all_runs.extend(runs)

    sessions_by_profile = _load_sessions_by_profile(since_ts=since_ts)
    _join_cost(all_runs, sessions_by_profile)
    return all_runs


def summary(since_hours: Optional[float] = None,
            brain_filter: Optional[str] = None,
            board_filter: Optional[str] = None) -> Dict:
    """Return a structured summary dict (machine-readable)."""
    runs = load_all_runs(since_hours=since_hours, board_filter=board_filter)
    if brain_filter:
        runs = [r for r in runs if (r.model or r.billing_provider or "unknown") == brain_filter]

    stats = aggregate_by_brain(runs)
    gate_bypasses = [r for r in runs if r.gate_bypass]

    return {
        "total_runs": len(runs),
        "since_hours": since_hours,
        "brains": {brain: _brain_to_dict(s) for brain, s in stats.items()},
        "gate_bypass_smells": [
            {
                "run_id": r.run_id,
                "task_id": r.task_id,
                "board": r.board,
                "profile": r.profile,
                "outcome": r.outcome,
                "changed_files": r.changed_files,
                "started_at": r.started_at,
            }
            for r in gate_bypasses
        ],
    }


def _brain_to_dict(s: BrainStats) -> dict:
    return {
        "total": s.total,
        "completed": s.completed,
        "success_rate": s.success_rate,
        "failure_rate": s.failure_rate,
        "protocol_violation_rate": s.protocol_violation_rate,
        "gate_bypass_rate": s.gate_bypass_rate,
        "failure_modes": {
            "protocol_violations": s.protocol_violations,
            "gate_bypasses": s.gate_bypasses,
            "timeouts": s.timeouts,
            "crashes": s.crashes,
            "gate_fails": s.gate_fails,
        },
        "runtime": {
            "avg_s": s.avg_duration,
            "p50_s": s.p50_duration,
            "p95_s": s.p95_duration,
        },
        "cost": {
            "avg_per_build": s.avg_cost,
        },
        "tests": {
            "pass_rate": s.test_pass_rate,
        },
        "regression": s.regression_flag,
    }


# ---------------------------------------------------------------------------
# CLI output
# ---------------------------------------------------------------------------

def _fmt_pct(v: Optional[float], decimals: int = 1) -> str:
    if v is None:
        return "n/a"
    return f"{v * 100:.{decimals}f}%"


def _fmt_dur(s: Optional[float]) -> str:
    if s is None:
        return "n/a"
    if s < 60:
        return f"{s:.0f}s"
    return f"{s/60:.1f}m"


def _fmt_cost(v: Optional[float]) -> str:
    if v is None:
        return "n/a"
    return f"${v:.4f}"


def print_summary(runs: List[BuildRun], verbose: bool = False) -> None:
    stats = aggregate_by_brain(runs)
    gate_bypasses = [r for r in runs if r.gate_bypass]
    proto_violations = [r for r in runs if r.protocol_violation]

    since_label = ""

    total = len(runs)
    completed = sum(1 for r in runs if r.outcome == "completed")
    failed = total - completed

    print(f"\n{'='*64}")
    print(f"  SHAY BUILDS SUMMARY  |  {total} runs, {completed} passed, {failed} failed")
    print(f"{'='*64}")
    print()

    if not stats:
        print("  No completed build runs found.")
        print()
        return

    # Per-brain table
    header = f"{'BRAIN':<30}  {'RUNS':>4}  {'OK%':>6}  {'PVIOLN':>6}  " \
             f"{'AVG':>6}  {'P95':>6}  {'$/BLD':>7}  {'TST%':>6}  {'FLAGS'}"
    print(header)
    print("-" * len(header))

    for brain, s in sorted(stats.items(), key=lambda x: -x[1].total):
        flags = []
        if s.regression_flag:
            flags.append("REGRESS!")
        if s.gate_bypass_rate > 0:
            flags.append(f"BYPASS:{s.gate_bypasses}")
        if s.protocol_violation_rate > 0.5:
            flags.append("PVIOLN-HEAVY")
        flag_str = " ".join(flags)

        brain_display = brain if len(brain) <= 30 else brain[:27] + "..."
        print(
            f"{brain_display:<30}  {s.total:>4}  {_fmt_pct(s.success_rate):>6}  "
            f"{_fmt_pct(s.protocol_violation_rate):>6}  "
            f"{_fmt_dur(s.avg_duration):>6}  {_fmt_dur(s.p95_duration):>6}  "
            f"{_fmt_cost(s.avg_cost):>7}  {_fmt_pct(s.test_pass_rate):>6}  "
            f"{flag_str}"
        )

    print()

    # Failure mode breakdown
    print("FAILURE MODES (all brains):")
    print(f"  protocol-violations : {len(proto_violations)}")
    total_timeout = sum(1 for r in runs if r.outcome == "timed_out")
    total_crash = sum(1 for r in runs if r.outcome == "crashed" and not r.protocol_violation)
    total_gate = sum(1 for r in runs if r.outcome == "blocked" and
                     ("gate" in (r.summary or "").lower() or "test" in (r.summary or "").lower()))
    total_blocked_other = sum(1 for r in runs if r.outcome == "blocked" and
                               "gate" not in (r.summary or "").lower() and
                               "test" not in (r.summary or "").lower())
    print(f"  timeouts            : {total_timeout}")
    print(f"  crashes             : {total_crash}")
    print(f"  gate-fails (blocked): {total_gate}")
    print(f"  blocked (other)     : {total_blocked_other}")
    print()

    # GATE-BYPASS smell report
    if gate_bypasses:
        print(f"GATE-BYPASS SMELL ({len(gate_bypasses)} run(s) completed with tests_run=0 but changed files):")
        for r in gate_bypasses:
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(r.started_at))
            files = ", ".join(r.changed_files[:3])
            if len(r.changed_files) > 3:
                files += f" +{len(r.changed_files)-3} more"
            print(f"  [{ts}] run#{r.run_id} task={r.task_id} board={r.board}")
            print(f"    changed: {files}")
        print()
    else:
        print("GATE-BYPASS SMELL: none detected")
        print()

    # Regression details
    regressions = [(brain, s) for brain, s in stats.items() if s.regression_flag]
    if regressions:
        print("REGRESSION FLAGS:")
        for brain, s in regressions:
            print(f"  {brain}: recent failure rate or runtime trending up vs trailing avg")
        print()

    if verbose:
        print("ALL RUNS (recent first):")
        print(f"  {'TS':<16}  {'BOARD':<12}  {'TASK':<12}  {'OUTCOME':<16}  {'DUR':>6}  {'COST':>7}  {'FLAGS'}")
        print(f"  {'-'*16}  {'-'*12}  {'-'*12}  {'-'*16}  {'-'*6}  {'-'*7}  {'-'*20}")
        for r in sorted(runs, key=lambda x: -(x.started_at or 0)):
            ts = time.strftime("%m-%d %H:%M", time.localtime(r.started_at)) if r.started_at else "?"
            outcome = r.outcome or r.status
            flags = []
            if r.gate_bypass:
                flags.append("BYPASS")
            if r.protocol_violation:
                flags.append("PVIOLN")
            flag_str = " ".join(flags)
            print(
                f"  {ts:<16}  {r.board:<12}  {r.task_id[:12]:<12}  {outcome:<16}  "
                f"{_fmt_dur(r.duration_s):>6}  {_fmt_cost(r.estimated_cost_usd):>7}  {flag_str}"
            )
        print()


# ---------------------------------------------------------------------------
# CLI subcommand wiring
# ---------------------------------------------------------------------------

def build_parser(parent_subparsers: "argparse._SubParsersAction") -> argparse.ArgumentParser:
    """Attach 'builds' subcommand to an existing subparsers action."""
    p = parent_subparsers.add_parser(
        "builds",
        help="Build tracker — durable ledger, search, and per-brain summary",
        description=(
            "BT-2: durable build ledger + search. Subcommands: summary (default), "
            "list, show, search, capture."
        ),
    )
    p.add_argument(
        "--since",
        metavar="HOURS",
        type=float,
        default=None,
        help="Only include runs started in the last N hours (e.g. --since 24)",
    )
    p.add_argument(
        "--by",
        metavar="BRAIN",
        default=None,
        help="Filter to a specific model/brain name",
    )
    p.add_argument(
        "--board",
        metavar="SLUG",
        default=None,
        help="Restrict to a single board slug (e.g. masterplan)",
    )
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Also list individual runs",
    )
    p.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output machine-readable JSON instead of table",
    )

    subs = p.add_subparsers(dest="builds_subcommand")

    # --- capture ---
    cap = subs.add_parser(
        "capture",
        help="Mirror all completed runs into ~/.shay/build-ledger.db + vault notes",
    )
    cap.add_argument("--ledger", metavar="PATH", default=None,
                     help="Override ledger DB path")

    # --- list ---
    lst = subs.add_parser(
        "list",
        help="List builds from the durable ledger",
    )
    lst.add_argument("--since", metavar="HOURS", type=float, default=None)
    lst.add_argument("--outcome", metavar="OUTCOME", default=None,
                     help="Filter by outcome (completed, blocked, crashed, timed_out)")
    lst.add_argument("--by", metavar="PROFILE", default=None)
    lst.add_argument("--board", metavar="SLUG", default=None)
    lst.add_argument("--limit", type=int, default=50)
    lst.add_argument("--json", action="store_true", default=False)

    # --- show ---
    shw = subs.add_parser(
        "show",
        help="Full drilldown for a single build by build_id",
    )
    shw.add_argument("build_id", help="build_id (b_<hex>) from 'shay builds list'")
    shw.add_argument("--json", action="store_true", default=False)

    # --- search ---
    srch = subs.add_parser(
        "search",
        help="Full-text + filter search across all builds in the ledger",
    )
    srch.add_argument("query", help="Search terms (FTS5 or LIKE fallback)")
    srch.add_argument("--outcome", metavar="OUTCOME", default=None)
    srch.add_argument("--by", metavar="PROFILE", default=None)
    srch.add_argument("--board", metavar="SLUG", default=None)
    srch.add_argument("--error-sig", metavar="SIG", default=None,
                      help="Filter by normalized error signature substring")
    srch.add_argument("--file", metavar="FILENAME", default=None,
                      help="Only builds that touched this file")
    srch.add_argument("--since", metavar="HOURS", type=float, default=None)
    srch.add_argument("--limit", type=int, default=50)
    srch.add_argument("--json", action="store_true", default=False)

    return p


def builds_command(args: argparse.Namespace) -> int:
    """Handler for 'shay builds' subcommand (and sub-subcommands)."""
    import json as _json

    sub = getattr(args, "builds_subcommand", None)

    # ------------------------------------------------------------------ capture
    if sub == "capture":
        from shay_cli.build_ledger import capture_all
        from pathlib import Path as _Path
        ledger = _Path(args.ledger) if getattr(args, "ledger", None) else None
        result = capture_all(ledger_path=ledger)
        print(f"Captured {result['new']} new builds, skipped {result['skipped']} already-present.")
        return 0

    # ------------------------------------------------------------------ list
    if sub == "list":
        from shay_cli.build_ledger import list_builds, print_builds_list
        builds = list_builds(
            since_hours=getattr(args, "since", None),
            outcome=getattr(args, "outcome", None),
            profile=getattr(args, "by", None),
            board=getattr(args, "board", None),
            limit=getattr(args, "limit", 50),
        )
        if getattr(args, "json", False):
            print(_json.dumps(builds, indent=2, default=str))
        else:
            print(f"\nDURABLE LEDGER — {len(builds)} build(s)\n")
            print_builds_list(builds)
        return 0

    # ------------------------------------------------------------------ show
    if sub == "show":
        from shay_cli.build_ledger import show_build, print_build_detail
        build = show_build(args.build_id)
        if build is None:
            print(f"Build not found: {args.build_id}")
            print("Run 'shay builds capture' first, then 'shay builds list' to find IDs.")
            return 1
        if getattr(args, "json", False):
            print(_json.dumps(build, indent=2, default=str))
        else:
            print_build_detail(build)
        return 0

    # ------------------------------------------------------------------ search
    if sub == "search":
        from shay_cli.build_ledger import search_ledger, print_builds_list, print_build_detail
        results = search_ledger(
            query=args.query,
            outcome=getattr(args, "outcome", None),
            profile=getattr(args, "by", None),
            board=getattr(args, "board", None),
            error_signature=getattr(args, "error_sig", None),
            file_touched=getattr(args, "file", None),
            since_hours=getattr(args, "since", None),
            limit=getattr(args, "limit", 50),
        )
        if getattr(args, "json", False):
            print(_json.dumps(results, indent=2, default=str))
        else:
            print(f"\nSEARCH: '{args.query}' — {len(results)} result(s)\n")
            print_builds_list(results)
        return 0

    # ------------------------------------------------------------------ default summary
    since_hours: Optional[float] = getattr(args, "since", None)
    brain_filter: Optional[str] = getattr(args, "by", None)
    board_filter: Optional[str] = getattr(args, "board", None)
    verbose: bool = getattr(args, "verbose", False)
    as_json: bool = getattr(args, "json", False)

    runs = load_all_runs(since_hours=since_hours, board_filter=board_filter)

    if brain_filter:
        runs = [r for r in runs if (r.model or r.billing_provider or "unknown") == brain_filter]

    if as_json:
        stats = aggregate_by_brain(runs)
        gate_bypasses = [r for r in runs if r.gate_bypass]
        out = {
            "total_runs": len(runs),
            "since_hours": since_hours,
            "brains": {brain: _brain_to_dict(s) for brain, s in stats.items()},
            "gate_bypass_smells": [
                {
                    "run_id": r.run_id,
                    "task_id": r.task_id,
                    "board": r.board,
                    "profile": r.profile,
                    "outcome": r.outcome,
                    "changed_files": r.changed_files,
                }
                for r in gate_bypasses
            ],
        }
        print(_json.dumps(out, indent=2))
    else:
        print_summary(runs, verbose=verbose)

    return 0
