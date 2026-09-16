#!/usr/bin/env python3
"""Read-only reconciliation gate for the Shay enhancement ledger.

The repository trace is phase-local evidence; the external JSONL ledger and
Kanban database are the lifecycle authority.  This command deliberately does
not import Shay's mutating database helpers and opens the board with SQLite's
immutable/query-only URI.  It emits a deterministic report and exits non-zero
when any orphan, stale branch, or cross-store mismatch is observed.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Iterable

PROGRAM_ID = "SHAY-AGENT-ENHANCEMENT-2026-09-13"
DEFAULT_LEDGER = Path("/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/evidence/execution-events.jsonl")
DEFAULT_LOCK = Path("/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/evidence/execution-events.lock")
DEFAULT_BOARD_DB = Path("/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/kanban/boards/shay-agent-enhancement-2026-09-13/kanban.db")
REQUIREMENTS = tuple(f"SHAY-AGENT-R{i}" for i in range(9))
TASK_IDS = {
    "SHAY-AGENT-R0": "t_a87e0383", "SHAY-AGENT-R1": "t_b9500d49",
    "SHAY-AGENT-R2": "t_77168057", "SHAY-AGENT-R3": "t_1e889bd1",
    "SHAY-AGENT-R4": "t_3be22fbc", "SHAY-AGENT-R5": "t_aa326c83",
    "SHAY-AGENT-R6": "t_782fa6d4", "SHAY-AGENT-R7": "t_6157bc92",
    "SHAY-AGENT-R8": "t_c69ad3e0",
}
TASK_TITLES = {
    "SHAY-AGENT-R0": "R0 - capability contract and trace freeze",
    "SHAY-AGENT-R1": "R1 - baseline and complete E2E stress gate",
    "SHAY-AGENT-R2": "R2 - read-only anti-drift reconciler",
    "SHAY-AGENT-R3": "R3 - durable lifecycle and API adapter",
    "SHAY-AGENT-R4": "R4 - typed safety and approval seam",
    "SHAY-AGENT-R5": "R5 - memory provenance and promotion",
    "SHAY-AGENT-R6": "R6 - shared client domain contract",
    "SHAY-AGENT-R7": "R7 - operator CLI and doctor UX",
    "SHAY-AGENT-R8": "R8 - canonical acceptance and finalization",
}
EXPECTED_LINKS = {
    (TASK_IDS["SHAY-AGENT-R0"], TASK_IDS["SHAY-AGENT-R1"]),
    (TASK_IDS["SHAY-AGENT-R1"], TASK_IDS["SHAY-AGENT-R2"]),
    (TASK_IDS["SHAY-AGENT-R2"], TASK_IDS["SHAY-AGENT-R3"]),
    (TASK_IDS["SHAY-AGENT-R2"], TASK_IDS["SHAY-AGENT-R4"]),
    (TASK_IDS["SHAY-AGENT-R3"], TASK_IDS["SHAY-AGENT-R5"]),
    (TASK_IDS["SHAY-AGENT-R3"], TASK_IDS["SHAY-AGENT-R6"]),
    (TASK_IDS["SHAY-AGENT-R4"], TASK_IDS["SHAY-AGENT-R5"]),
    (TASK_IDS["SHAY-AGENT-R4"], TASK_IDS["SHAY-AGENT-R6"]),
    (TASK_IDS["SHAY-AGENT-R6"], TASK_IDS["SHAY-AGENT-R7"]),
    (TASK_IDS["SHAY-AGENT-R5"], TASK_IDS["SHAY-AGENT-R8"]),
    (TASK_IDS["SHAY-AGENT-R7"], TASK_IDS["SHAY-AGENT-R8"]),
}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
COMMENT_START = re.compile(r"^phase_gate=start requirement_id=(SHAY-AGENT-R[0-8]) attempt_id=([A-Za-z0-9_.:-]+)$")
COMMENT_REVIEW = re.compile(r"^phase_gate=review candidate_tree_sha=([0-9a-f]{40}) diff_sha256=([0-9a-f]{64})$")


class ReconciliationError(Exception):
    """Raised only for unrecoverable input/transport errors."""


def _json_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_jsonl(path: Path, *, require_final_newline: bool = True) -> tuple[list[dict[str, Any]], bytes]:
    """Read strict UTF-8 JSONL without normalising or mutating the source."""
    raw = path.read_bytes()
    if require_final_newline and raw and not raw.endswith(b"\n"):
        raise ValueError(f"{path}: missing final newline")
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            raise ValueError(f"{path}: blank line {index}")
        value = json.loads(line.decode("utf-8"), object_pairs_hook=_json_pairs)
        if not isinstance(value, dict):
            raise ValueError(f"{path}: line {index} is not an object")
        rows.append(value)
    return rows, raw


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _add(errors: list[str], message: str) -> None:
    if message not in errors:
        errors.append(message)


def _load_phase_paths(repo: Path) -> dict[str, Path]:
    """Use the contract path map, with a safe static fallback for portability."""
    paths = {r: repo / "docs/architecture/evidence" / f"shay-agent-{r.split('-')[-1].lower()}-events.jsonl" for r in REQUIREMENTS[1:]}
    contract = repo / "docs/architecture/shay-custom-capability-contract.yaml"
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(contract.read_text(encoding="utf-8"))
        for requirement, path in data["phase_local_evidence_contract"]["path_map"].items():
            paths[requirement] = repo / path
    except (OSError, KeyError, TypeError, ValueError, ImportError):
        pass
    return paths


def _check_chain(rows: list[dict[str, Any]], errors: list[str], *, ledger: bool) -> None:
    seen_ids: set[str] = set()
    prior_line = b""
    for index, row in enumerate(rows, 1):
        event_id = row.get("event_id")
        if not isinstance(event_id, str) or not event_id or event_id in seen_ids:
            _add(errors, f"ledger duplicate/missing event_id at line {index}")
        seen_ids.add(str(event_id))
        if ledger:
            if row.get("event_sequence") != index:
                _add(errors, f"ledger event_sequence mismatch at line {index}")
            expected_prior = None if index == 1 else _sha(prior_line)
            if row.get("prior_line_sha256") != expected_prior:
                _add(errors, f"ledger hash-chain mismatch at line {index}")
            if index > 1 and row.get("prior_event_id") != rows[index - 2].get("event_id"):
                _add(errors, f"ledger prior_event_id mismatch at line {index}")
            if row.get("program_id") != PROGRAM_ID:
                _add(errors, f"ledger program mismatch at line {index}")
        prior_line = json.dumps(row, sort_keys=True, separators=(",", ":")).encode() if not ledger else b""


def _check_ledger_schema(rows: list[dict[str, Any]], errors: list[str]) -> None:
    required = {"schema_version", "contract_revision", "setup_attempt_id", "event_id", "event_sequence", "prior_event_id", "prior_line_sha256", "program_id", "requirement_id", "event_type", "recorded_at", "actor_role", "idempotency_key", "implementation_base_sha", "integration_base_sha", "candidate_binding", "review_result", "commit_ref", "remote_ref", "kanban_ref", "reconciliation_ref", "r8_snapshot_ref", "outcome"}
    allowed_types = {"execution_ledger_initialized", "verification_review", "anti_pattern_review", "quality_review", "candidate_superseded", "review_set_superseded", "implementation_commit_recorded", "ci_verification_failed", "feature_branch_bootstrap_verified", "feature_branch_push_verified", "kanban_completed", "reconciliation_recorded", "program_finalization_query_issued", "program_finalization_query_started", "program_finalization_query_result", "program_finalization_query_attempt_failed", "program_finalization_retry_exhausted", "program_finalization_retry_budget_exhausted", "program_finalization_abandoned", "program_finalized"}
    for i, row in enumerate(rows, 1):
        if set(row) != required:
            _add(errors, f"ledger schema keys mismatch at line {i}")
        if row.get("schema_version") != 2 or row.get("contract_revision") != "non-synced-v3" or row.get("setup_attempt_id") != "local-state-v3":
            _add(errors, f"ledger schema identity mismatch at line {i}")
        if row.get("event_type") not in allowed_types:
            _add(errors, f"ledger invalid event_type at line {i}")
        req = row.get("requirement_id")
        if req is not None and req not in REQUIREMENTS:
            _add(errors, f"ledger invalid requirement_id at line {i}")
        key = row.get("idempotency_key")
        if not isinstance(key, str) or not key:
            _add(errors, f"ledger empty idempotency_key at line {i}")


def _parse_board(path: Path, errors: list[str]) -> dict[str, Any]:
    uri = f"file:{path}?immutable=1"
    try:
        conn = sqlite3.connect(uri, uri=True)
        conn.execute("PRAGMA query_only=ON")
        conn.row_factory = sqlite3.Row
        tasks = [dict(row) for row in conn.execute("SELECT * FROM tasks ORDER BY created_at, id").fetchall()]
        links = {tuple(r) for r in conn.execute("SELECT parent_id, child_id FROM task_links").fetchall()}
        comments = [dict(row) for row in conn.execute("SELECT * FROM task_comments ORDER BY id").fetchall()]
        events = [dict(row) for row in conn.execute("SELECT * FROM task_events ORDER BY id").fetchall()]
        runs = [dict(row) for row in conn.execute("SELECT * FROM task_runs ORDER BY id").fetchall()]
        conn.close()
    except sqlite3.Error as exc:
        _add(errors, f"board read failed: {exc}")
        return {"tasks": [], "links": set(), "comments": [], "events": [], "runs": []}
    actual_ids = {r.get("id") for r in tasks}
    if actual_ids != set(TASK_IDS.values()):
        _add(errors, "board task IDs mismatch")
    for req, task_id in TASK_IDS.items():
        row = next((r for r in tasks if r.get("id") == task_id), None)
        if row is None:
            continue
        expected_key = f"{PROGRAM_ID}:{req[-2:]}"
        if row.get("title") != TASK_TITLES[req]:
            _add(errors, f"board title mismatch for {req}")
        if row.get("idempotency_key") != expected_key:
            _add(errors, f"board idempotency key mismatch for {req}")
    if links != EXPECTED_LINKS:
        _add(errors, "board dependency links mismatch")
    for comment in comments:
        body = comment.get("body", "")
        if not COMMENT_START.fullmatch(body) and not COMMENT_REVIEW.fullmatch(body):
            _add(errors, f"illegal board comment id {comment.get('id')}")
    task_ids = actual_ids
    expected_created = set(TASK_IDS.values())
    seen_created: set[str] = set()
    for run in runs:
        if run.get("task_id") not in task_ids:
            _add(errors, f"orphan task_run id {run.get('id')}")
        if run.get("status") == "running":
            if run.get("ended_at") is not None:
                _add(errors, f"open task_run {run.get('id')} has ended_at")
        elif run.get("ended_at") is None:
            _add(errors, f"closed task_run {run.get('id')} missing ended_at")
    for event in events:
        task_id = event.get("task_id")
        if task_id not in task_ids:
            _add(errors, f"orphan task_event id {event.get('id')}")
        kind = event.get("kind")
        if kind == "created":
            seen_created.add(str(task_id))
        elif kind not in {"promoted", "commented", "completed", "blocked"}:
            _add(errors, f"unknown task_event kind at id {event.get('id')}")
    if seen_created != expected_created:
        _add(errors, "board created task event set mismatch")
    return {"tasks": tasks, "links": links, "comments": comments, "events": events, "runs": runs}


def _phase_errors(repo: Path, errors: list[str]) -> tuple[dict[str, Any], dict[str, str]]:
    paths = _load_phase_paths(repo)
    phase_required = {
        "all_unlisted_paths_forbidden", "allowed_paths", "branch", "changed_paths", "commit_ref",
        "contract_revision", "dependency_refs", "event_id", "event_revision", "event_type", "evidence",
        "existing_owner", "finalization_ref", "forbidden_paths", "implementation_approval", "implementation_base_sha",
        "integration_base_sha", "kanban_ref", "merge_approval", "phase_evidence_path", "plan_ref", "planned_target",
        "planning_anchor_sha", "prior_event_id", "protected_custom_manifest_id", "recorded_at", "recommendation_ref",
        "release_ref", "requirement_id", "research_source", "review_refs", "review_results", "setup_attempt_id",
        "status", "test_results", "tests", "timing_status", "verification_refs", "worktree",
    }
    rows_by_req: dict[str, Any] = {}
    hashes: dict[str, str] = {}
    for req, path in paths.items():
        if not path.exists():
            rows_by_req[req] = []
            continue
        try:
            rows, raw = read_jsonl(path)
            rows_by_req[req] = rows
            hashes[req] = _sha(raw)
            _check_chain(rows, errors, ledger=False)
            for index, row in enumerate(rows):
                if set(row) != phase_required:
                    _add(errors, f"phase evidence schema keys mismatch in {req} line {index + 1}")
                if row.get("requirement_id") != req:
                    _add(errors, f"phase evidence requirement mismatch in {req}")
                if row.get("contract_revision") != "non-synced-v3" or row.get("setup_attempt_id") != "local-state-v3":
                    _add(errors, f"phase evidence contract identity mismatch in {req} line {index + 1}")
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            _add(errors, f"phase evidence unreadable {req}: {exc}")
    return rows_by_req, hashes


def _read_canonical_trace(repo: Path, errors: list[str]) -> tuple[list[dict[str, Any]], str | None]:
    path = repo / "docs/architecture/shay-agent-enhancement-trace.jsonl"
    try:
        rows, raw = read_jsonl(path)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        _add(errors, f"canonical trace unreadable: {exc}")
        return [], None
    seen: set[str] = set()
    latest: dict[str, int] = {}
    for index, row in enumerate(rows, 1):
        event_id = row.get("event_id")
        requirement = row.get("requirement_id")
        if not isinstance(event_id, str) or event_id in seen:
            _add(errors, f"canonical trace duplicate/missing event_id at line {index}")
        seen.add(str(event_id))
        if requirement not in REQUIREMENTS:
            _add(errors, f"canonical trace invalid requirement at line {index}")
            continue
        revision = row.get("event_revision")
        expected = latest.get(requirement, 0) + 1
        # The archived prefix is intentionally historical, but each current
        # requirement chain still has monotonically increasing revisions.
        if not isinstance(revision, int) or revision < expected:
            _add(errors, f"canonical trace revision regression for {requirement} at line {index}")
        latest[requirement] = max(latest.get(requirement, 0), revision if isinstance(revision, int) else 0)
    return rows, _sha(raw)


def reconcile(*, repo: Path, ledger_path: Path = DEFAULT_LEDGER, lock_path: Path = DEFAULT_LOCK, board_db: Path = DEFAULT_BOARD_DB) -> dict[str, Any]:
    """Return a stable report.  No input is written, including lock files."""
    errors: list[str] = []
    ledger_rows: list[dict[str, Any]] = []
    ledger_hash = None
    try:
        with lock_path.open("rb") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_SH)
            ledger_rows, raw = read_jsonl(ledger_path)
            ledger_hash = _sha(raw)
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        _add(errors, f"ledger unreadable: {exc}")
    if ledger_rows:
        _check_ledger_schema(ledger_rows, errors)
        # Recompute the hash chain from original bytes, not re-serialised JSON.
        try:
            raw_lines = ledger_path.read_bytes().splitlines()
            seen: set[str] = set()
            for i, (row, raw_line) in enumerate(zip(ledger_rows, raw_lines), 1):
                if row.get("event_id") in seen:
                    _add(errors, f"ledger duplicate event_id {row.get('event_id')}")
                seen.add(str(row.get("event_id")))
                prior = None if i == 1 else _sha(raw_lines[i - 2])
                if row.get("prior_line_sha256") != prior:
                    _add(errors, f"ledger hash-chain mismatch at line {i}")
                if row.get("event_sequence") != i:
                    _add(errors, f"ledger event_sequence mismatch at line {i}")
                if i > 1 and row.get("prior_event_id") != ledger_rows[i - 2].get("event_id"):
                    _add(errors, f"ledger prior_event_id mismatch at line {i}")
        except OSError as exc:
            _add(errors, f"ledger reread failed: {exc}")
    board = _parse_board(board_db, errors)
    canonical_rows, canonical_hash = _read_canonical_trace(repo, errors)
    phases, phase_hashes = _phase_errors(repo, errors)

    # Cross-store lifecycle projection.  Every external record must name a
    # known requirement and every branch-bearing record must agree with the
    # phase's declared branch when one is available.
    ledger_reqs = {r.get("requirement_id") for r in ledger_rows if r.get("requirement_id") is not None}
    for req in sorted(ledger_reqs - set(REQUIREMENTS)):
        _add(errors, f"orphan ledger requirement {req}")
    for req, rows in phases.items():
        if rows and req not in ledger_reqs and any(r.get("event_type") in {"implementation_started", "implementation_evidence", "verification"} for r in rows):
            _add(errors, f"orphan phase evidence without ledger lifecycle {req}")
    for row in ledger_rows:
        binding = row.get("candidate_binding")
        if isinstance(binding, dict):
            branch = binding.get("attempt_authority", {}).get("feature_branch") if isinstance(binding.get("attempt_authority"), dict) else None
            phase_rows = phases.get(row.get("requirement_id"), [])
            declared = next((p.get("branch") for p in reversed(phase_rows) if p.get("branch")), None)
            if branch and declared and branch != declared:
                _add(errors, f"stale branch for {row.get('requirement_id')}: {branch} != {declared}")
        remote = row.get("remote_ref")
        commit = row.get("commit_ref")
        if isinstance(remote, dict) and isinstance(commit, dict) and remote.get("sha") != commit.get("sha"):
            _add(errors, f"remote/commit mismatch for {row.get('requirement_id')}")

    # Report sorted lists so repeated runs are byte-identical.
    errors = sorted(errors)
    report = {
        "schema_version": 1,
        "status": "passed" if not errors else "failed",
        "repo": str(repo),
        "ledger": {"path": str(ledger_path), "sha256": ledger_hash, "events": len(ledger_rows)},
        "canonical_trace": {"path": str(repo / "docs/architecture/shay-agent-enhancement-trace.jsonl"), "sha256": canonical_hash, "events": len(canonical_rows)},
        "board": {"path": str(board_db), "tasks": len(board["tasks"]), "links": len(board["links"]), "comments": len(board["comments"]), "events": len(board["events"]), "runs": len(board["runs"])},
        "phase_evidence": {req: {"path": str(path), "sha256": phase_hashes.get(req), "events": len(phases.get(req, []))} for req, path in sorted(_load_phase_paths(repo).items())},
        "drift": {"orphans": [e for e in errors if "orphan" in e], "stale_branches": [e for e in errors if "stale branch" in e], "mismatches": [e for e in errors if "orphan" not in e and "stale branch" not in e]},
        "errors": errors,
    }
    report["counts"] = {"orphans": len(report["drift"]["orphans"]), "stale_branches": len(report["drift"]["stale_branches"]), "mismatches": len(report["drift"]["mismatches"]), "total": len(errors)}
    return report


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--board-db", type=Path, default=DEFAULT_BOARD_DB)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        report = reconcile(repo=args.repo.resolve(), ledger_path=args.ledger, lock_path=args.lock, board_db=args.board_db)
    except (OSError, ValueError, sqlite3.Error) as exc:
        report = {"schema_version": 1, "status": "failed", "errors": [str(exc)], "counts": {"orphans": 0, "stale_branches": 0, "mismatches": 1, "total": 1}}
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
