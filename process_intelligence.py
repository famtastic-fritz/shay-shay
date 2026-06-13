#!/usr/bin/env python3
"""Machine-written process-intelligence storage and runtime recorder.

Phase 2 goal: durable, queryable run/decision/tool/artifact/tracker records
generated from live agent execution, with explicit evidence-bound state changes.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import re
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, TypeVar

from shay_constants import get_shay_home
from shay_state import apply_wal_with_fallback

logger = logging.getLogger(__name__)

T = TypeVar("T")

DEFAULT_DB_PATH = get_shay_home() / "process_intelligence.db"
_WRITE_MAX_RETRIES = 5
_WRITE_RETRY_MIN_S = 0.02
_WRITE_RETRY_MAX_S = 0.15
_CHECKPOINT_EVERY_N_WRITES = 250
_MAX_SUMMARY_CHARS = 700
_SECRET_KEY_RE = re.compile(r"(secret|password|passwd|token|api[_-]?key|authorization|cookie)", re.I)
_SECRET_VALUE_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{12,}|xox[baprs]-[A-Za-z0-9-]{10,}|ghp_[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9._=-]{12,})"
)
_PATH_VALUE_RE = re.compile(r"(?:^|\s)(/[^\s'\"]+)" )
_VALIDATION_CMD_RE = re.compile(
    r"\b(pytest|unittest|nose2?|playwright|jest|vitest|npm\s+test|pnpm\s+test|yarn\s+test|cargo\s+test|go\s+test|doctor|health|status|check|verify|curl\s+.+health)\b",
    re.I,
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS run_ledger (
    run_id TEXT PRIMARY KEY,
    session_id TEXT,
    parent_session_id TEXT,
    task_id TEXT,
    source TEXT,
    platform TEXT,
    user_id TEXT,
    chat_id TEXT,
    thread_id TEXT,
    model TEXT,
    provider TEXT,
    base_url TEXT,
    instruction_summary TEXT,
    instruction_hash TEXT,
    status TEXT,
    outcome TEXT,
    started_at REAL NOT NULL,
    ended_at REAL,
    turn_exit_reason TEXT,
    api_calls INTEGER DEFAULT 0,
    message_count INTEGER DEFAULT 0,
    tool_call_count INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    estimated_cost_usd REAL,
    final_response_summary TEXT,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS tool_agent_ledger (
    activity_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    session_id TEXT,
    task_id TEXT,
    tool_call_id TEXT,
    tool_name TEXT NOT NULL,
    status TEXT,
    action_summary TEXT,
    output_summary TEXT,
    touched_paths TEXT,
    started_at REAL,
    ended_at REAL,
    duration_ms INTEGER,
    metadata TEXT,
    FOREIGN KEY (run_id) REFERENCES run_ledger(run_id)
);

CREATE TABLE IF NOT EXISTS artifact_ledger (
    artifact_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    session_id TEXT,
    task_id TEXT,
    tool_activity_id TEXT,
    tool_name TEXT,
    path TEXT,
    artifact_type TEXT,
    operation TEXT,
    summary TEXT,
    evidence_hash TEXT,
    recorded_at REAL NOT NULL,
    metadata TEXT,
    FOREIGN KEY (run_id) REFERENCES run_ledger(run_id),
    FOREIGN KEY (tool_activity_id) REFERENCES tool_agent_ledger(activity_id)
);

CREATE TABLE IF NOT EXISTS validation_ledger (
    validation_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    session_id TEXT,
    task_id TEXT,
    tool_activity_id TEXT,
    validator TEXT,
    validation_type TEXT,
    command_summary TEXT,
    status TEXT,
    summary TEXT,
    recorded_at REAL NOT NULL,
    metadata TEXT,
    FOREIGN KEY (run_id) REFERENCES run_ledger(run_id),
    FOREIGN KEY (tool_activity_id) REFERENCES tool_agent_ledger(activity_id)
);

CREATE TABLE IF NOT EXISTS decision_ledger (
    decision_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    session_id TEXT,
    task_id TEXT,
    lane_id TEXT,
    decision_type TEXT,
    summary TEXT,
    status TEXT,
    rationale TEXT,
    evidence_refs TEXT,
    artifact_refs TEXT,
    blocker_item_id TEXT,
    autonomy_zone TEXT,
    approval_state TEXT,
    impact_level TEXT,
    reversibility TEXT,
    recorded_at REAL NOT NULL,
    metadata TEXT,
    FOREIGN KEY (run_id) REFERENCES run_ledger(run_id)
);

CREATE TABLE IF NOT EXISTS tracker_transition_ledger (
    transition_id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL,
    run_id TEXT,
    decision_id TEXT,
    from_state TEXT,
    to_state TEXT,
    summary TEXT,
    evidence_refs TEXT,
    recorded_at REAL NOT NULL,
    metadata TEXT,
    FOREIGN KEY (run_id) REFERENCES run_ledger(run_id),
    FOREIGN KEY (decision_id) REFERENCES decision_ledger(decision_id)
);

CREATE INDEX IF NOT EXISTS idx_run_ledger_started ON run_ledger(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_run_ledger_session ON run_ledger(session_id);
CREATE INDEX IF NOT EXISTS idx_run_ledger_task ON run_ledger(task_id);
CREATE INDEX IF NOT EXISTS idx_tool_agent_run ON tool_agent_ledger(run_id, started_at);
CREATE INDEX IF NOT EXISTS idx_tool_agent_tool ON tool_agent_ledger(tool_name, status);
CREATE INDEX IF NOT EXISTS idx_artifact_run ON artifact_ledger(run_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_artifact_path ON artifact_ledger(path);
CREATE INDEX IF NOT EXISTS idx_validation_run ON validation_ledger(run_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_decision_run ON decision_ledger(run_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_decision_blocker ON decision_ledger(blocker_item_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_tracker_item ON tracker_transition_ledger(item_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_tracker_run ON tracker_transition_ledger(run_id, recorded_at);
"""


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=_json_default)


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(_json_dumps(value).encode("utf-8", errors="replace")).hexdigest()


def _clip(text: str, limit: int = _MAX_SUMMARY_CHARS) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _redact_string(text: str) -> str:
    if not text:
        return text
    text = _SECRET_VALUE_RE.sub("[REDACTED]", text)
    return text


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: Dict[str, Any] = {}
        for key, inner in value.items():
            if _SECRET_KEY_RE.search(str(key)):
                cleaned[str(key)] = "[REDACTED]"
            else:
                cleaned[str(key)] = _redact_value(inner)
        return cleaned
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    if isinstance(value, tuple):
        return [_redact_value(v) for v in value]
    if isinstance(value, str):
        return _redact_string(value)
    return value


def _summarize_value(value: Any, *, limit: int = _MAX_SUMMARY_CHARS) -> str:
    redacted = _redact_value(value)
    if isinstance(redacted, str):
        return _clip(redacted, limit)
    try:
        return _clip(_json_dumps(redacted), limit)
    except Exception:
        return _clip(str(redacted), limit)


def _candidate_paths_from_args(tool_name: str, args: Dict[str, Any]) -> List[str]:
    keys = (
        "path",
        "file_path",
        "output_path",
        "image_url",
        "workdir",
        "script",
    )
    results: List[str] = []
    for key in keys:
        value = args.get(key)
        if isinstance(value, str) and (value.startswith("/") or value.startswith("~/")):
            results.append(os.path.expanduser(value))
    if tool_name == "patch":
        patch_blob = args.get("patch")
        if isinstance(patch_blob, str):
            for line in patch_blob.splitlines():
                if line.startswith("*** Update File: ") or line.startswith("*** Add File: "):
                    maybe_path = line.split(":", 1)[1].strip()
                    if maybe_path:
                        results.append(os.path.expanduser(maybe_path))
    return sorted(set(results))


def _candidate_paths_from_result(result: Any) -> List[str]:
    text = _summarize_value(result, limit=2000)
    found = []
    for match in _PATH_VALUE_RE.findall(text):
        path = match.strip()
        if path.startswith("/"):
            found.append(path)
    return sorted(set(found))


def _artifact_type_for_path(path: str) -> str:
    lower = path.lower()
    if lower.endswith((".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".py", ".js", ".ts", ".tsx", ".html", ".css")):
        return "file"
    if lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".mp3", ".wav", ".mp4", ".mov")):
        return "media"
    return "path"


def _operation_for_tool(tool_name: str) -> str:
    mapping = {
        "write_file": "write",
        "patch": "patch",
        "terminal": "command",
        "process": "process",
        "browser_vision": "capture",
        "browser_get_images": "inspect",
    }
    return mapping.get(tool_name, "tool")


def _is_validation(tool_name: str, args: Dict[str, Any]) -> Optional[Dict[str, str]]:
    if tool_name == "terminal":
        command = str(args.get("command") or "")
        if _VALIDATION_CMD_RE.search(command):
            return {
                "validator": "terminal",
                "validation_type": "command",
                "command_summary": _clip(_redact_string(command), 500),
            }
    if tool_name == "process":
        action = str(args.get("action") or "")
        if action in {"poll", "wait", "log"}:
            return {
                "validator": "process",
                "validation_type": action,
                "command_summary": f"process:{action}",
            }
    if tool_name == "browser_console":
        expression = str(args.get("expression") or "")
        if expression:
            return {
                "validator": "browser_console",
                "validation_type": "expression",
                "command_summary": _clip(_redact_string(expression), 500),
            }
    return None


class ProcessIntelligenceDB:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._write_count = 0
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=1.0,
            isolation_level=None,
        )
        self._conn.row_factory = sqlite3.Row
        apply_wal_with_fallback(self._conn, db_label="process_intelligence.db")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()

    def _execute_write(self, fn: Callable[[sqlite3.Connection], T]) -> T:
        last_err: Optional[Exception] = None
        for attempt in range(_WRITE_MAX_RETRIES):
            try:
                with self._lock:
                    self._conn.execute("BEGIN IMMEDIATE")
                    try:
                        result = fn(self._conn)
                        self._conn.commit()
                    except BaseException:
                        try:
                            self._conn.rollback()
                        except Exception:
                            pass
                        raise
                self._write_count += 1
                if self._write_count % _CHECKPOINT_EVERY_N_WRITES == 0:
                    self._try_checkpoint()
                return result
            except sqlite3.OperationalError as exc:
                err = str(exc).lower()
                if ("locked" in err or "busy" in err) and attempt < _WRITE_MAX_RETRIES - 1:
                    last_err = exc
                    time.sleep(random.uniform(_WRITE_RETRY_MIN_S, _WRITE_RETRY_MAX_S))
                    continue
                raise
        if last_err:
            raise last_err
        raise RuntimeError("process intelligence write failed")

    def _try_checkpoint(self) -> None:
        try:
            with self._lock:
                self._conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
        except Exception:
            logger.debug("process intelligence checkpoint failed", exc_info=True)

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def upsert_run(self, payload: Dict[str, Any]) -> str:
        def _write(conn: sqlite3.Connection) -> str:
            conn.execute(
                """
                INSERT INTO run_ledger (
                    run_id, session_id, parent_session_id, task_id, source, platform,
                    user_id, chat_id, thread_id, model, provider, base_url,
                    instruction_summary, instruction_hash, status, outcome,
                    started_at, ended_at, turn_exit_reason, api_calls, message_count,
                    tool_call_count, input_tokens, output_tokens, total_tokens,
                    estimated_cost_usd, final_response_summary, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    session_id=excluded.session_id,
                    parent_session_id=excluded.parent_session_id,
                    task_id=excluded.task_id,
                    source=excluded.source,
                    platform=excluded.platform,
                    user_id=excluded.user_id,
                    chat_id=excluded.chat_id,
                    thread_id=excluded.thread_id,
                    model=excluded.model,
                    provider=excluded.provider,
                    base_url=excluded.base_url,
                    instruction_summary=excluded.instruction_summary,
                    instruction_hash=excluded.instruction_hash,
                    status=excluded.status,
                    outcome=excluded.outcome,
                    started_at=excluded.started_at,
                    ended_at=COALESCE(excluded.ended_at, run_ledger.ended_at),
                    turn_exit_reason=excluded.turn_exit_reason,
                    api_calls=excluded.api_calls,
                    message_count=excluded.message_count,
                    tool_call_count=excluded.tool_call_count,
                    input_tokens=excluded.input_tokens,
                    output_tokens=excluded.output_tokens,
                    total_tokens=excluded.total_tokens,
                    estimated_cost_usd=excluded.estimated_cost_usd,
                    final_response_summary=COALESCE(excluded.final_response_summary, run_ledger.final_response_summary),
                    metadata=excluded.metadata
                """,
                (
                    payload["run_id"],
                    payload.get("session_id"),
                    payload.get("parent_session_id"),
                    payload.get("task_id"),
                    payload.get("source"),
                    payload.get("platform"),
                    payload.get("user_id"),
                    payload.get("chat_id"),
                    payload.get("thread_id"),
                    payload.get("model"),
                    payload.get("provider"),
                    payload.get("base_url"),
                    payload.get("instruction_summary"),
                    payload.get("instruction_hash"),
                    payload.get("status"),
                    payload.get("outcome"),
                    payload.get("started_at"),
                    payload.get("ended_at"),
                    payload.get("turn_exit_reason"),
                    int(payload.get("api_calls") or 0),
                    int(payload.get("message_count") or 0),
                    int(payload.get("tool_call_count") or 0),
                    int(payload.get("input_tokens") or 0),
                    int(payload.get("output_tokens") or 0),
                    int(payload.get("total_tokens") or 0),
                    payload.get("estimated_cost_usd"),
                    payload.get("final_response_summary"),
                    _json_dumps(payload.get("metadata") or {}),
                ),
            )
            return payload["run_id"]
        return self._execute_write(_write)

    def record_tool_activity(self, payload: Dict[str, Any]) -> str:
        def _write(conn: sqlite3.Connection) -> str:
            conn.execute(
                """
                INSERT INTO tool_agent_ledger (
                    activity_id, run_id, session_id, task_id, tool_call_id, tool_name,
                    status, action_summary, output_summary, touched_paths,
                    started_at, ended_at, duration_ms, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["activity_id"],
                    payload["run_id"],
                    payload.get("session_id"),
                    payload.get("task_id"),
                    payload.get("tool_call_id"),
                    payload.get("tool_name"),
                    payload.get("status"),
                    payload.get("action_summary"),
                    payload.get("output_summary"),
                    _json_dumps(payload.get("touched_paths") or []),
                    payload.get("started_at"),
                    payload.get("ended_at"),
                    payload.get("duration_ms"),
                    _json_dumps(payload.get("metadata") or {}),
                ),
            )
            return payload["activity_id"]
        return self._execute_write(_write)

    def record_artifact(self, payload: Dict[str, Any]) -> str:
        def _write(conn: sqlite3.Connection) -> str:
            conn.execute(
                """
                INSERT INTO artifact_ledger (
                    artifact_id, run_id, session_id, task_id, tool_activity_id, tool_name,
                    path, artifact_type, operation, summary, evidence_hash, recorded_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["artifact_id"],
                    payload["run_id"],
                    payload.get("session_id"),
                    payload.get("task_id"),
                    payload.get("tool_activity_id"),
                    payload.get("tool_name"),
                    payload.get("path"),
                    payload.get("artifact_type"),
                    payload.get("operation"),
                    payload.get("summary"),
                    payload.get("evidence_hash"),
                    payload.get("recorded_at"),
                    _json_dumps(payload.get("metadata") or {}),
                ),
            )
            return payload["artifact_id"]
        return self._execute_write(_write)

    def record_validation(self, payload: Dict[str, Any]) -> str:
        def _write(conn: sqlite3.Connection) -> str:
            conn.execute(
                """
                INSERT INTO validation_ledger (
                    validation_id, run_id, session_id, task_id, tool_activity_id,
                    validator, validation_type, command_summary, status, summary,
                    recorded_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["validation_id"],
                    payload["run_id"],
                    payload.get("session_id"),
                    payload.get("task_id"),
                    payload.get("tool_activity_id"),
                    payload.get("validator"),
                    payload.get("validation_type"),
                    payload.get("command_summary"),
                    payload.get("status"),
                    payload.get("summary"),
                    payload.get("recorded_at"),
                    _json_dumps(payload.get("metadata") or {}),
                ),
            )
            return payload["validation_id"]
        return self._execute_write(_write)

    def record_decision(self, payload: Dict[str, Any]) -> str:
        def _write(conn: sqlite3.Connection) -> str:
            conn.execute(
                """
                INSERT INTO decision_ledger (
                    decision_id, run_id, session_id, task_id, lane_id, decision_type,
                    summary, status, rationale, evidence_refs, artifact_refs,
                    blocker_item_id, autonomy_zone, approval_state, impact_level,
                    reversibility, recorded_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["decision_id"],
                    payload["run_id"],
                    payload.get("session_id"),
                    payload.get("task_id"),
                    payload.get("lane_id"),
                    payload.get("decision_type"),
                    payload.get("summary"),
                    payload.get("status"),
                    payload.get("rationale"),
                    _json_dumps(payload.get("evidence_refs") or []),
                    _json_dumps(payload.get("artifact_refs") or []),
                    payload.get("blocker_item_id"),
                    payload.get("autonomy_zone"),
                    payload.get("approval_state"),
                    payload.get("impact_level"),
                    payload.get("reversibility"),
                    payload.get("recorded_at"),
                    _json_dumps(payload.get("metadata") or {}),
                ),
            )
            return payload["decision_id"]
        return self._execute_write(_write)

    def record_tracker_transition(self, payload: Dict[str, Any]) -> str:
        def _write(conn: sqlite3.Connection) -> str:
            conn.execute(
                """
                INSERT INTO tracker_transition_ledger (
                    transition_id, item_id, run_id, decision_id, from_state, to_state,
                    summary, evidence_refs, recorded_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["transition_id"],
                    payload["item_id"],
                    payload.get("run_id"),
                    payload.get("decision_id"),
                    payload.get("from_state"),
                    payload.get("to_state"),
                    payload.get("summary"),
                    _json_dumps(payload.get("evidence_refs") or []),
                    payload.get("recorded_at"),
                    _json_dumps(payload.get("metadata") or {}),
                ),
            )
            return payload["transition_id"]
        return self._execute_write(_write)

    def list_runs(self, *, limit: int = 20, status: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM run_ledger"
        params: List[Any] = []
        if status:
            sql += " WHERE status = ?"
            params.append(status)
        sql += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)
        rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_run_timeline(self, run_id: str) -> List[Dict[str, Any]]:
        timeline: List[Dict[str, Any]] = []
        for row in self._conn.execute(
            "SELECT activity_id as id, started_at as ts, tool_name as label, status, 'tool' as kind FROM tool_agent_ledger WHERE run_id = ?",
            (run_id,),
        ).fetchall():
            timeline.append(dict(row))
        for row in self._conn.execute(
            "SELECT artifact_id as id, recorded_at as ts, path as label, operation as status, 'artifact' as kind FROM artifact_ledger WHERE run_id = ?",
            (run_id,),
        ).fetchall():
            timeline.append(dict(row))
        for row in self._conn.execute(
            "SELECT validation_id as id, recorded_at as ts, command_summary as label, status, 'validation' as kind FROM validation_ledger WHERE run_id = ?",
            (run_id,),
        ).fetchall():
            timeline.append(dict(row))
        for row in self._conn.execute(
            "SELECT decision_id as id, recorded_at as ts, summary as label, status, 'decision' as kind FROM decision_ledger WHERE run_id = ?",
            (run_id,),
        ).fetchall():
            timeline.append(dict(row))
        timeline.sort(key=lambda item: item.get("ts") or 0)
        return timeline

    def get_run_artifacts(self, run_id: str) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM artifact_ledger WHERE run_id = ? ORDER BY recorded_at ASC, path ASC",
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_run_decisions(self, run_id: str) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM decision_ledger WHERE run_id = ? ORDER BY recorded_at ASC, decision_id ASC",
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_item_blockers(self, item_id: str) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM decision_ledger WHERE blocker_item_id = ? ORDER BY recorded_at DESC",
            (item_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_tracker_transitions(self, item_id: str) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM tracker_transition_ledger WHERE item_id = ? ORDER BY recorded_at ASC",
            (item_id,),
        ).fetchall()
        return [dict(r) for r in rows]


class ProcessIntelligenceRecorder:
    def __init__(self, db: Optional[ProcessIntelligenceDB] = None, *, enabled: bool = True):
        self._enabled = enabled
        self._db = db if enabled else None
        self._current: Optional[Dict[str, Any]] = None
        self._lock = threading.Lock()

    @classmethod
    def default(cls, *, enabled: bool = True) -> "ProcessIntelligenceRecorder":
        if not enabled:
            return cls(enabled=False)
        try:
            return cls(ProcessIntelligenceDB(), enabled=True)
        except Exception:
            logger.warning("process intelligence disabled after init failure", exc_info=True)
            return cls(enabled=False)

    @property
    def enabled(self) -> bool:
        return self._enabled and self._db is not None

    def start_run(self, **kwargs: Any) -> Optional[str]:
        if not self.enabled:
            return None
        run_id = uuid.uuid4().hex
        payload = {
            "run_id": run_id,
            "session_id": kwargs.get("session_id"),
            "parent_session_id": kwargs.get("parent_session_id"),
            "task_id": kwargs.get("task_id"),
            "source": kwargs.get("source") or kwargs.get("platform") or "unknown",
            "platform": kwargs.get("platform"),
            "user_id": kwargs.get("user_id"),
            "chat_id": kwargs.get("chat_id"),
            "thread_id": kwargs.get("thread_id"),
            "model": kwargs.get("model"),
            "provider": kwargs.get("provider"),
            "base_url": kwargs.get("base_url"),
            "instruction_summary": _summarize_value(kwargs.get("user_message"), limit=500),
            "instruction_hash": _stable_hash(kwargs.get("user_message")),
            "status": "running",
            "outcome": None,
            "started_at": time.time(),
            "ended_at": None,
            "turn_exit_reason": None,
            "api_calls": 0,
            "message_count": int(kwargs.get("message_count") or 0),
            "tool_call_count": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": None,
            "final_response_summary": None,
            "metadata": {
                "history_count": int(kwargs.get("history_count") or 0),
                "max_iterations": kwargs.get("max_iterations"),
            },
        }
        with self._lock:
            self._current = {
                "run_id": run_id,
                "session_id": payload.get("session_id"),
                "task_id": payload.get("task_id"),
                "started_at": payload["started_at"],
            }
        self._db.upsert_run(payload)
        return run_id

    def persist_snapshot(self, *, message_count: int, tool_call_count: int) -> None:
        if not self.enabled or not self._current:
            return
        self._db.upsert_run(
            {
                "run_id": self._current["run_id"],
                "session_id": self._current.get("session_id"),
                "task_id": self._current.get("task_id"),
                "status": "running",
                "started_at": self._current["started_at"],
                "message_count": int(message_count),
                "tool_call_count": int(tool_call_count),
                "metadata": {"snapshot": True},
            }
        )

    def record_tool_outcome(
        self,
        *,
        tool_name: str,
        args: Dict[str, Any],
        result: Any,
        tool_call_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
        started_at: Optional[float] = None,
        ended_at: Optional[float] = None,
        blocked: bool = False,
    ) -> None:
        if not self.enabled or not self._current:
            return
        touched = sorted(set(_candidate_paths_from_args(tool_name, args) + _candidate_paths_from_result(result)))
        activity_id = uuid.uuid4().hex
        status = "blocked" if blocked else "completed"
        output_summary = _summarize_value(result)
        action_summary = _summarize_value(args, limit=500)
        self._db.record_tool_activity(
            {
                "activity_id": activity_id,
                "run_id": self._current["run_id"],
                "session_id": self._current.get("session_id"),
                "task_id": self._current.get("task_id"),
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "status": status,
                "action_summary": action_summary,
                "output_summary": output_summary,
                "touched_paths": touched,
                "started_at": started_at,
                "ended_at": ended_at or time.time(),
                "duration_ms": duration_ms,
                "metadata": {"blocked": blocked},
            }
        )
        for path in touched:
            self._db.record_artifact(
                {
                    "artifact_id": uuid.uuid4().hex,
                    "run_id": self._current["run_id"],
                    "session_id": self._current.get("session_id"),
                    "task_id": self._current.get("task_id"),
                    "tool_activity_id": activity_id,
                    "tool_name": tool_name,
                    "path": path,
                    "artifact_type": _artifact_type_for_path(path),
                    "operation": _operation_for_tool(tool_name),
                    "summary": output_summary,
                    "evidence_hash": _stable_hash({"tool": tool_name, "path": path, "result": output_summary}),
                    "recorded_at": time.time(),
                    "metadata": {"args_summary": action_summary},
                }
            )
        validation = _is_validation(tool_name, args)
        if validation:
            validation_status = "failed" if isinstance(result, str) and "error" in result.lower() else "completed"
            self._db.record_validation(
                {
                    "validation_id": uuid.uuid4().hex,
                    "run_id": self._current["run_id"],
                    "session_id": self._current.get("session_id"),
                    "task_id": self._current.get("task_id"),
                    "tool_activity_id": activity_id,
                    **validation,
                    "status": validation_status,
                    "summary": output_summary,
                    "recorded_at": time.time(),
                    "metadata": {"tool_name": tool_name},
                }
            )

    def record_decision(
        self,
        *,
        decision_type: str,
        summary: str,
        rationale: str,
        evidence_refs: Optional[Sequence[str]] = None,
        artifact_refs: Optional[Sequence[str]] = None,
        blocker_item_id: Optional[str] = None,
        status: str = "accepted",
        lane_id: Optional[str] = None,
        autonomy_zone: str = "green",
        approval_state: str = "not_required",
        impact_level: str = "medium",
        reversibility: str = "easy",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        if not self.enabled or not self._current:
            return None
        decision_id = uuid.uuid4().hex
        self._db.record_decision(
            {
                "decision_id": decision_id,
                "run_id": self._current["run_id"],
                "session_id": self._current.get("session_id"),
                "task_id": self._current.get("task_id"),
                "lane_id": lane_id,
                "decision_type": decision_type,
                "summary": _clip(summary, 500),
                "status": status,
                "rationale": _clip(rationale, 700),
                "evidence_refs": list(evidence_refs or []),
                "artifact_refs": list(artifact_refs or []),
                "blocker_item_id": blocker_item_id,
                "autonomy_zone": autonomy_zone,
                "approval_state": approval_state,
                "impact_level": impact_level,
                "reversibility": reversibility,
                "recorded_at": time.time(),
                "metadata": metadata or {},
            }
        )
        return decision_id

    def finish_run(self, *, result: Dict[str, Any], message_count: int, tool_call_count: int) -> None:
        if not self.enabled or not self._current:
            return
        interrupted = bool(result.get("interrupted"))
        completed = bool(result.get("completed"))
        outcome = "interrupted" if interrupted else ("completed" if completed else "partial")
        status = "finished"
        guardrail = result.get("guardrail") if isinstance(result.get("guardrail"), dict) else None
        if guardrail:
            self.record_decision(
                decision_type="risk",
                summary=f"Tool guardrail halted repeated calls to {guardrail.get('tool_name') or 'unknown tool'}",
                rationale=guardrail.get("message") or guardrail.get("code") or "tool-call guardrail stop",
                evidence_refs=[],
                status="accepted",
                lane_id="tool-guardrails",
                autonomy_zone="yellow",
                approval_state="not_required",
                impact_level="medium",
                reversibility="easy",
                metadata={"guardrail": guardrail},
            )
        elif interrupted:
            self.record_decision(
                decision_type="escalation",
                summary="Run ended early due to interrupt",
                rationale=result.get("turn_exit_reason") or "user interrupt",
                evidence_refs=[],
                status="accepted",
                lane_id="runtime",
                autonomy_zone="yellow",
                approval_state="not_required",
                impact_level="low",
                reversibility="easy",
                metadata={"interrupted": True},
            )
        self._db.upsert_run(
            {
                "run_id": self._current["run_id"],
                "session_id": self._current.get("session_id"),
                "task_id": self._current.get("task_id"),
                "status": status,
                "outcome": outcome,
                "started_at": self._current["started_at"],
                "ended_at": time.time(),
                "turn_exit_reason": result.get("turn_exit_reason"),
                "api_calls": int(result.get("api_calls") or 0),
                "message_count": int(message_count),
                "tool_call_count": int(tool_call_count),
                "input_tokens": int(result.get("input_tokens") or 0),
                "output_tokens": int(result.get("output_tokens") or 0),
                "total_tokens": int(result.get("total_tokens") or 0),
                "estimated_cost_usd": result.get("estimated_cost_usd"),
                "final_response_summary": _summarize_value(result.get("final_response"), limit=500),
                "metadata": {
                    "provider": result.get("provider"),
                    "base_url": result.get("base_url"),
                    "response_previewed": result.get("response_previewed"),
                    "partial": result.get("partial"),
                    "guardrail": guardrail,
                },
            }
        )
        with self._lock:
            self._current = None
