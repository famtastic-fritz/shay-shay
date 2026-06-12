#!/usr/bin/env python3
"""Read-only audit of legacy Shay session JSON artifacts.

Inspects:
- ~/.shay/sessions/*.json
- ~/.shay/sessions/*.jsonl
- ~/.shay/sessions/sessions.json
- ~/.shay/state.db (read-only)

This script never writes to ~/.shay/sessions/, state.db, or shay.db.
It prints a JSON summary to stdout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PRIVATE_REDACTION_KEYS = {"authorization", "api_key", "token", "headers", "body", "system_prompt", "messages"}
SESSION_ID_RE = re.compile(r"(\d{8}_\d{6}_[0-9a-f]{6,8})")

CLASSIFICATIONS = [
    "active bookkeeping candidate",
    "raw archive candidate",
    "migration candidate",
    "summarize-then-archive candidate",
    "prune candidate",
    "corrupt/unreadable candidate",
    "duplicate candidate",
    "unknown / needs manual review",
]


@dataclass
class StateDbInfo:
    path: str
    exists: bool
    session_count: int
    message_count: int
    session_ids: set[str]
    message_counts: dict[str, int]
    schema_ok: bool
    error: str | None = None


@dataclass
class ArtifactResult:
    path: str
    name: str
    extension: str
    size_bytes: int
    classification: str
    reasons: list[str]
    kind: str
    parse_status: str
    session_ids: list[str]
    represented_in_state_db: bool | None
    matched_state_db_session_ids: list[str]
    extra: dict[str, Any]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_json_file(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(safe_read_text(path)), None
    except Exception as exc:
        return None, f"json_parse_error: {exc}"


def parse_jsonl_file(path: Path) -> tuple[list[Any] | None, str | None]:
    try:
        rows = []
        for idx, line in enumerate(safe_read_text(path).splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception as exc:
                return None, f"jsonl_parse_error line {idx}: {exc}"
        return rows, None
    except Exception as exc:
        return None, f"jsonl_read_error: {exc}"


def extract_session_ids_from_obj(obj: Any) -> list[str]:
    found: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                if k == "session_id" and isinstance(v, str):
                    found.add(v)
                elif k in {"messages", "conversation_history", "request", "error", "system_prompt", "content", "body", "headers"}:
                    continue
                else:
                    walk(v)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(obj)
    return sorted(found)


def extract_filename_session_id(path: Path) -> str | None:
    match = SESSION_ID_RE.search(path.stem)
    return match.group(1) if match else None


def load_state_db(db_path: Path) -> StateDbInfo:
    if not db_path.exists():
        return StateDbInfo(
            path=str(db_path),
            exists=False,
            session_count=0,
            message_count=0,
            session_ids=set(),
            message_counts={},
            schema_ok=False,
            error="state.db not found",
        )

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cur = conn.cursor()
        table_names = {row[0] for row in cur.execute("select name from sqlite_master where type='table'")}
        if "sessions" not in table_names or "messages" not in table_names:
            conn.close()
            return StateDbInfo(
                path=str(db_path),
                exists=True,
                session_count=0,
                message_count=0,
                session_ids=set(),
                message_counts={},
                schema_ok=False,
                error="missing required tables",
            )

        session_ids = {row[0] for row in cur.execute("select id from sessions")}
        session_count = len(session_ids)
        message_count = cur.execute("select count(*) from messages").fetchone()[0]
        message_counts = {
            row[0]: row[1]
            for row in cur.execute("select session_id, count(*) from messages group by session_id")
        }
        conn.close()
        return StateDbInfo(
            path=str(db_path),
            exists=True,
            session_count=session_count,
            message_count=message_count,
            session_ids=session_ids,
            message_counts=message_counts,
            schema_ok=True,
            error=None,
        )
    except Exception as exc:
        return StateDbInfo(
            path=str(db_path),
            exists=True,
            session_count=0,
            message_count=0,
            session_ids=set(),
            message_counts={},
            schema_ok=False,
            error=f"state.db read error: {exc}",
        )


def classify_sessions_index(path: Path, obj: Any, state_db: StateDbInfo) -> ArtifactResult:
    reasons: list[str] = []
    session_ids = extract_session_ids_from_obj(obj)
    represented = any(sid in state_db.session_ids for sid in session_ids) if session_ids else None
    entry_count = len(obj) if isinstance(obj, dict) else None
    valid_shape = isinstance(obj, dict) and all(isinstance(v, dict) for v in obj.values())
    if valid_shape:
        reasons.append("dict keyed by session_key with per-session metadata entries")
        reasons.append("runtime docs/code reference sessions.json as gateway bookkeeping")
        classification = "active bookkeeping candidate"
        parse_status = "ok"
    else:
        classification = "unknown / needs manual review"
        parse_status = "ok"
        reasons.append("sessions.json exists but shape is not the expected gateway mapping dict")
    return ArtifactResult(
        path=str(path),
        name=path.name,
        extension=path.suffix,
        size_bytes=path.stat().st_size,
        classification=classification,
        reasons=reasons,
        kind="sessions_index",
        parse_status=parse_status,
        session_ids=session_ids,
        represented_in_state_db=represented,
        matched_state_db_session_ids=[sid for sid in session_ids if sid in state_db.session_ids],
        extra={"entry_count": entry_count},
    )


def classify_json_snapshot(path: Path, obj: Any, state_db: StateDbInfo) -> ArtifactResult:
    reasons: list[str] = []
    top_level_session_id = obj.get("session_id") if isinstance(obj, dict) and isinstance(obj.get("session_id"), str) else None
    filename_session_id = extract_filename_session_id(path)
    session_ids = [sid for sid in [top_level_session_id, filename_session_id] if sid]
    session_ids = list(dict.fromkeys(session_ids))
    represented_ids = [sid for sid in session_ids if sid in state_db.session_ids]
    represented = bool(represented_ids) if session_ids else None
    message_count = None
    if isinstance(obj, dict):
        mc = obj.get("message_count")
        if isinstance(mc, int):
            message_count = mc
        elif isinstance(obj.get("messages"), list):
            message_count = len(obj["messages"])

    classification = "unknown / needs manual review"
    kind = "session_snapshot_json"

    if represented_ids:
        classification = "duplicate candidate"
        reasons.append("session_id is already present in state.db")
        reasons.append("file appears to be a legacy per-session transcript snapshot")
    elif session_ids and message_count and message_count > 0:
        classification = "migration candidate"
        reasons.append("session transcript exists on disk but matching state.db session_id was not found")
    elif session_ids and (message_count == 0 or message_count is None):
        classification = "raw archive candidate"
        reasons.append("session-shaped artifact exists but has no strong sign of active canonical use")
    else:
        reasons.append("unrecognized session snapshot shape")

    return ArtifactResult(
        path=str(path),
        name=path.name,
        extension=path.suffix,
        size_bytes=path.stat().st_size,
        classification=classification,
        reasons=reasons,
        kind=kind,
        parse_status="ok",
        session_ids=session_ids,
        represented_in_state_db=represented,
        matched_state_db_session_ids=represented_ids,
        extra={"message_count": message_count},
    )


def classify_request_dump(path: Path, obj: Any, state_db: StateDbInfo) -> ArtifactResult:
    reasons: list[str] = []
    top_level_session_id = obj.get("session_id") if isinstance(obj, dict) and isinstance(obj.get("session_id"), str) else None
    filename_session_id = extract_filename_session_id(path)
    session_ids = [sid for sid in [top_level_session_id, filename_session_id] if sid]
    session_ids = list(dict.fromkeys(session_ids))
    represented_ids = [sid for sid in session_ids if sid in state_db.session_ids]
    represented = bool(represented_ids) if session_ids else None
    classification = "summarize-then-archive candidate"
    reasons.append("request dump appears diagnostic/error-oriented rather than canonical recall")
    reasons.append("may contain sensitive request payload fragments; summarize before any archive/prune decision")
    return ArtifactResult(
        path=str(path),
        name=path.name,
        extension=path.suffix,
        size_bytes=path.stat().st_size,
        classification=classification,
        reasons=reasons,
        kind="request_dump_json",
        parse_status="ok",
        session_ids=session_ids,
        represented_in_state_db=represented,
        matched_state_db_session_ids=represented_ids,
        extra={"keys": list(obj.keys())[:10] if isinstance(obj, dict) else None},
    )


def classify_jsonl(path: Path, rows: list[Any], state_db: StateDbInfo) -> ArtifactResult:
    reasons: list[str] = []
    meta_session_id = None
    if rows and isinstance(rows[0], dict):
        meta_session_id = rows[0].get("session_id") if isinstance(rows[0].get("session_id"), str) else None
    filename_session_id = extract_filename_session_id(path)
    session_ids = [sid for sid in [meta_session_id, filename_session_id] if sid]
    session_ids = list(dict.fromkeys(session_ids))
    represented_ids = [sid for sid in session_ids if sid in state_db.session_ids]
    represented = bool(represented_ids) if session_ids else None
    classification = "unknown / needs manual review"
    if represented_ids:
        classification = "raw archive candidate"
        reasons.append("jsonl fragment shape appears legacy and matching session_id exists in state.db")
    elif session_ids:
        classification = "migration candidate"
        reasons.append("jsonl fragment references session_id not found in state.db")
    else:
        reasons.append("jsonl fragment has no extractable session_id")
    return ArtifactResult(
        path=str(path),
        name=path.name,
        extension=path.suffix,
        size_bytes=path.stat().st_size,
        classification=classification,
        reasons=reasons,
        kind="jsonl_fragment",
        parse_status="ok",
        session_ids=session_ids,
        represented_in_state_db=represented,
        matched_state_db_session_ids=represented_ids,
        extra={"line_count": len(rows)},
    )


def classify_other_json(path: Path, obj: Any, state_db: StateDbInfo) -> ArtifactResult:
    session_ids = extract_session_ids_from_obj(obj)
    represented_ids = [sid for sid in session_ids if sid in state_db.session_ids]
    represented = bool(represented_ids) if session_ids else None
    reasons = ["json artifact did not match known session snapshot, request dump, or sessions index patterns"]
    return ArtifactResult(
        path=str(path),
        name=path.name,
        extension=path.suffix,
        size_bytes=path.stat().st_size,
        classification="unknown / needs manual review",
        reasons=reasons,
        kind="other_json",
        parse_status="ok",
        session_ids=session_ids,
        represented_in_state_db=represented,
        matched_state_db_session_ids=represented_ids,
        extra={},
    )


def classify_artifact(path: Path, state_db: StateDbInfo) -> ArtifactResult:
    if path.name == "sessions.json":
        obj, err = parse_json_file(path)
        if err:
            return ArtifactResult(
                path=str(path),
                name=path.name,
                extension=path.suffix,
                size_bytes=path.stat().st_size,
                classification="corrupt/unreadable candidate",
                reasons=[err],
                kind="sessions_index",
                parse_status="error",
                session_ids=[],
                represented_in_state_db=None,
                matched_state_db_session_ids=[],
                extra={},
            )
        return classify_sessions_index(path, obj, state_db)

    if path.suffix == ".jsonl":
        rows, err = parse_jsonl_file(path)
        if err:
            return ArtifactResult(
                path=str(path),
                name=path.name,
                extension=path.suffix,
                size_bytes=path.stat().st_size,
                classification="corrupt/unreadable candidate",
                reasons=[err],
                kind="jsonl_fragment",
                parse_status="error",
                session_ids=[],
                represented_in_state_db=None,
                matched_state_db_session_ids=[],
                extra={},
            )
        return classify_jsonl(path, rows or [], state_db)

    obj, err = parse_json_file(path)
    if err:
        return ArtifactResult(
            path=str(path),
            name=path.name,
            extension=path.suffix,
            size_bytes=path.stat().st_size,
            classification="corrupt/unreadable candidate",
            reasons=[err],
            kind="json",
            parse_status="error",
            session_ids=[],
            represented_in_state_db=None,
            matched_state_db_session_ids=[],
            extra={},
        )

    if path.name.startswith("request_dump_"):
        return classify_request_dump(path, obj, state_db)

    if path.name.startswith("session_") and isinstance(obj, dict):
        return classify_json_snapshot(path, obj, state_db)

    return classify_other_json(path, obj, state_db)


def choose_sample_session_snapshots(results: list[ArtifactResult], sample_size: int) -> list[ArtifactResult]:
    snapshots = [
        r for r in results
        if r.kind == "session_snapshot_json"
    ]
    snapshots.sort(key=lambda r: r.name)
    if sample_size <= 0 or len(snapshots) <= sample_size:
        return snapshots
    if sample_size == 1:
        return [snapshots[len(snapshots) // 2]]

    step = (len(snapshots) - 1) / (sample_size - 1)
    picked = []
    seen = set()
    for i in range(sample_size):
        idx = round(i * step)
        if idx not in seen:
            picked.append(snapshots[idx])
            seen.add(idx)
    return picked


def summarize_examples(results: list[ArtifactResult], per_class: int = 3) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = defaultdict(list)
    for r in sorted(results, key=lambda x: x.name):
        if len(buckets[r.classification]) < per_class:
            buckets[r.classification].append(r.name)
    return dict(buckets)


def build_summary(results: list[ArtifactResult], state_db: StateDbInfo, sessions_dir: Path, sample_size: int) -> dict[str, Any]:
    ext_counts = Counter(r.extension for r in results)
    class_counts = Counter(r.classification for r in results)
    kind_counts = Counter(r.kind for r in results)
    sample = choose_sample_session_snapshots(results, sample_size)
    sample_rows = []
    represented_hits = 0
    for r in sample:
        represented = bool(r.matched_state_db_session_ids)
        if represented:
            represented_hits += 1
        sid = r.session_ids[0] if r.session_ids else None
        sample_rows.append({
            "file": r.name,
            "session_id": sid,
            "represented_in_state_db": represented,
            "state_db_message_count": state_db.message_counts.get(sid) if sid else None,
            "classification": r.classification,
        })

    sessions_json_result = next((r for r in results if r.name == "sessions.json"), None)

    return {
        "generated_at": utc_now_iso(),
        "read_only": True,
        "sessions_dir": str(sessions_dir),
        "total_files_found": len(results),
        "counts_by_extension": dict(sorted(ext_counts.items())),
        "counts_by_classification": {k: class_counts.get(k, 0) for k in CLASSIFICATIONS},
        "counts_by_kind": dict(sorted(kind_counts.items())),
        "sessions_json": {
            "present": sessions_json_result is not None,
            "classification": sessions_json_result.classification if sessions_json_result else None,
            "appears_active_bookkeeping": bool(
                sessions_json_result and sessions_json_result.classification == "active bookkeeping candidate"
            ),
            "reasons": sessions_json_result.reasons if sessions_json_result else [],
            "entry_count": (sessions_json_result.extra.get("entry_count") if sessions_json_result else None),
        },
        "state_db": {
            "path": state_db.path,
            "exists": state_db.exists,
            "schema_ok": state_db.schema_ok,
            "session_count": state_db.session_count,
            "message_count": state_db.message_count,
            "error": state_db.error,
        },
        "sampled_session_json_representation": {
            "sample_size": len(sample_rows),
            "represented_count": represented_hits,
            "rows": sample_rows,
        },
        "example_files_by_classification": summarize_examples(results),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only audit of Shay legacy session JSON artifacts")
    parser.add_argument("--sessions-dir", default=os.path.expanduser("~/.shay/sessions"))
    parser.add_argument("--state-db", default=os.path.expanduser("~/.shay/state.db"))
    parser.add_argument("--sample-size", type=int, default=10)
    args = parser.parse_args()

    sessions_dir = Path(args.sessions_dir).expanduser()
    state_db_path = Path(args.state_db).expanduser()

    if not sessions_dir.exists() or not sessions_dir.is_dir():
        print(json.dumps({
            "error": f"sessions directory not found: {sessions_dir}",
            "read_only": True,
        }, indent=2))
        return 1

    state_db = load_state_db(state_db_path)
    files = sorted([
        *sessions_dir.glob("*.json"),
        *sessions_dir.glob("*.jsonl"),
    ])

    results = [classify_artifact(path, state_db) for path in files]
    summary = build_summary(results, state_db, sessions_dir, args.sample_size)

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
