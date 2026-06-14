from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from agent.redact import redact_sensitive_text
from shay_constants import get_shay_home
from utils import atomic_json_write, atomic_replace

PROCESS_INTELLIGENCE_DIRNAME = "process-intelligence"
RUNS_DIRNAME = "runs"
LEDGER_FILENAME = "runs.jsonl"

REQUIRED_FIELDS: tuple[str, ...] = (
    "run_id",
    "plan_id",
    "job_id",
    "task_id",
    "parent_job_id",
    "lane",
    "task_name",
    "started_at",
    "ended_at",
    "duration_seconds",
    "instruction_summary",
    "instruction_hash",
    "full_instruction_stored",
    "tools_used",
    "commands_run",
    "files_inspected",
    "files_changed",
    "artifacts_created",
    "commits_created",
    "decisions_made",
    "assumptions_made",
    "gaps_opened",
    "gaps_closed",
    "validation_results",
    "safety_events",
    "blockers",
    "outcome",
    "next_actions",
    "lessons_learned",
    "redactions",
)

_LIST_FIELDS = {
    "tools_used",
    "commands_run",
    "files_inspected",
    "files_changed",
    "artifacts_created",
    "commits_created",
    "decisions_made",
    "assumptions_made",
    "gaps_opened",
    "gaps_closed",
    "validation_results",
    "safety_events",
    "blockers",
    "next_actions",
    "lessons_learned",
    "redactions",
}

_SENSITIVE_EXACT_KEYS = {
    "api_key",
    "apikey",
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "secret",
    "client_secret",
    "password",
    "passwd",
    "cookie",
    "cookies",
    "authorization",
    "private_key",
    "headers",
    "body",
    "messages",
    "system_prompt",
    "prompt",
    "transcript",
    "private_content",
    "private_vault_content",
    "session_transcript",
}

_SENSITIVE_SUBSTRINGS = (
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "passwd",
    "cookie",
    "authorization",
    "private_key",
)

_ENV_CONTAINER_KEYS = {"env", "environment", "env_vars", "environment_variables"}
_PRIVATE_CONTENT_KEYS = {
    "body",
    "headers",
    "messages",
    "system_prompt",
    "transcript",
    "private_content",
    "private_vault_content",
    "session_transcript",
}
_SUCCESS_STATUSES = {"pass", "passed", "ok", "success", "succeeded", "green"}
_FAILURE_STATUSES = {"fail", "failed", "error", "errored", "blocked", "unsafe", "red"}
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def process_intelligence_home() -> Path:
    return get_shay_home() / PROCESS_INTELLIGENCE_DIRNAME


def runs_dir() -> Path:
    return process_intelligence_home() / RUNS_DIRNAME


def ledger_index_path() -> Path:
    return process_intelligence_home() / LEDGER_FILENAME


def validate_run_id(run_id: Any) -> str:
    normalized = _normalize_identifier(run_id)
    if not normalized:
        raise ValueError("run_id cannot be empty")
    if not _RUN_ID_RE.fullmatch(normalized):
        raise ValueError("run_id must match ^[A-Za-z0-9._-]+$")
    return normalized


def run_record_path(run_id: str) -> Path:
    safe_run_id = validate_run_id(run_id)
    base = runs_dir()
    candidate = base / f"{safe_run_id}.json"
    resolved_base = base.resolve()
    resolved_candidate = candidate.resolve(strict=False)
    if os.path.commonpath((str(resolved_base), str(resolved_candidate))) != str(resolved_base):
        raise ValueError("run_id escapes the process-intelligence runs directory")
    return candidate


def ensure_storage() -> Path:
    base = process_intelligence_home()
    runs_dir().mkdir(parents=True, exist_ok=True)
    return base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _normalize_identifier(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _normalize_list(value: Any) -> list[Any]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return sorted(value, key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, default=str))
    return [value]


def _append_unique(redactions: list[str], note: str) -> None:
    if note and note not in redactions:
        redactions.append(note)


def _key_name(path: str) -> str:
    if not path:
        return ""
    name = path.rsplit(".", 1)[-1]
    if "[" in name:
        name = name.split("[", 1)[0]
    return name.strip().lower()


def _is_env_container(name: str) -> bool:
    return name in _ENV_CONTAINER_KEYS


def _is_private_content_key(name: str) -> bool:
    return name in _PRIVATE_CONTENT_KEYS


def _is_sensitive_key(name: str) -> bool:
    if not name:
        return False
    if name in _SENSITIVE_EXACT_KEYS:
        return True
    return any(token in name for token in _SENSITIVE_SUBSTRINGS)


def _sanitize_value(value: Any, key_path: str, redactions: list[str]) -> Any:
    key_name = _key_name(key_path)
    if _is_env_container(key_name):
        _append_unique(redactions, f"{key_path}: environment values not captured")
        return f"[redacted:{key_name}:values-not-captured]"
    if _is_private_content_key(key_name):
        _append_unique(redactions, f"{key_path}: private content not captured")
        return f"[redacted:{key_name}:content-not-captured]"
    if _is_sensitive_key(key_name):
        _append_unique(redactions, f"{key_path}: secret-bearing value redacted")
        return f"[redacted:{key_name}]"

    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            child_key = str(raw_key)
            child_path = f"{key_path}.{child_key}" if key_path else child_key
            child_name = child_key.strip().lower()
            if _is_env_container(child_name):
                sanitized[child_key] = f"[redacted:{child_name}:values-not-captured]"
                _append_unique(redactions, f"{child_path}: environment values not captured")
            elif _is_private_content_key(child_name):
                sanitized[child_key] = f"[redacted:{child_name}:content-not-captured]"
                _append_unique(redactions, f"{child_path}: private content not captured")
            elif _is_sensitive_key(child_name):
                sanitized[child_key] = f"[redacted:{child_name}]"
                _append_unique(redactions, f"{child_path}: secret-bearing value redacted")
            else:
                sanitized[child_key] = _sanitize_value(raw_value, child_path, redactions)
        return sanitized

    if isinstance(value, list):
        return [_sanitize_value(item, f"{key_path}[{idx}]", redactions) for idx, item in enumerate(value)]
    if isinstance(value, tuple):
        return [_sanitize_value(item, f"{key_path}[{idx}]", redactions) for idx, item in enumerate(value)]
    if isinstance(value, set):
        items = sorted(value, key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, default=str))
        return [_sanitize_value(item, f"{key_path}[{idx}]", redactions) for idx, item in enumerate(items)]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, str):
        redacted = redact_sensitive_text(value, force=True)
        if redacted != value:
            _append_unique(redactions, f"{key_path}: sensitive text redacted")
        return redacted
    return value


def _dedupe_list(items: list[Any]) -> list[Any]:
    seen: set[str] = set()
    deduped: list[Any] = []
    for item in items:
        marker = json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)
        if marker in seen:
            continue
        seen.add(marker)
        deduped.append(item)
    return deduped


def _generate_run_id(seed: str) -> str:
    stamp = _utc_now().strftime("%Y%m%dT%H%M%SZ")
    if seed:
        suffix = hashlib.sha256(seed.encode("utf-8", errors="replace")).hexdigest()[:8]
    else:
        suffix = hashlib.sha256(os.urandom(16)).hexdigest()[:8]
    return f"run-{stamp}-{suffix}"


def _derive_duration_seconds(
    started_at: datetime,
    ended_at: datetime,
    explicit_duration: Any,
) -> float:
    if explicit_duration not in (None, ""):
        try:
            return round(max(0.0, float(explicit_duration)), 3)
        except (TypeError, ValueError):
            pass
    return round(max(0.0, (ended_at - started_at).total_seconds()), 3)


def _append_jsonl_atomic(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = ""
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing and not existing.endswith("\n"):
            existing += "\n"
    line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.stem}_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(existing)
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
        atomic_replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except OSError:
                pass


def prepare_run_record(payload: Mapping[str, Any]) -> dict[str, Any]:
    redactions: list[str] = []

    raw_instruction_text = _normalize_text(payload.get("instruction_text"))
    instruction_summary_source = payload.get("instruction_summary") or raw_instruction_text
    instruction_summary = _sanitize_value(_normalize_text(instruction_summary_source), "instruction_summary", redactions)

    if raw_instruction_text:
        _append_unique(redactions, "instruction_text observed for hashing only; raw instruction not stored")
    if payload.get("full_instruction") not in (None, "", [], {}):
        _append_unique(redactions, "full_instruction provided but not stored in MVP")
    if payload.get("full_instruction_stored"):
        _append_unique(redactions, "full_instruction_stored requested but disabled in MVP")

    started_at = _parse_datetime(payload.get("started_at")) or _utc_now()
    ended_at = _parse_datetime(payload.get("ended_at")) or started_at
    if ended_at < started_at:
        ended_at = started_at
        _append_unique(redactions, "ended_at earlier than started_at; clamped to started_at")

    instruction_hash_source = raw_instruction_text or _normalize_text(instruction_summary_source) or _normalize_text(payload.get("task_name"))
    instruction_hash = hashlib.sha256(instruction_hash_source.encode("utf-8", errors="replace")).hexdigest()

    if payload.get("run_id") not in (None, ""):
        run_id = validate_run_id(payload.get("run_id"))
    else:
        run_id = _generate_run_id(instruction_hash_source)

    record: dict[str, Any] = {
        "run_id": run_id,
        "plan_id": _normalize_identifier(payload.get("plan_id")),
        "job_id": _normalize_identifier(payload.get("job_id")),
        "task_id": _normalize_identifier(payload.get("task_id")),
        "parent_job_id": _normalize_identifier(payload.get("parent_job_id")),
        "lane": _sanitize_value(_normalize_text(payload.get("lane") or "manual"), "lane", redactions),
        "task_name": _sanitize_value(_normalize_text(payload.get("task_name")), "task_name", redactions),
        "started_at": _isoformat(started_at),
        "ended_at": _isoformat(ended_at),
        "duration_seconds": _derive_duration_seconds(started_at, ended_at, payload.get("duration_seconds")),
        "instruction_summary": instruction_summary,
        "instruction_hash": instruction_hash,
        "full_instruction_stored": False,
        "tools_used": [],
        "commands_run": [],
        "files_inspected": [],
        "files_changed": [],
        "artifacts_created": [],
        "commits_created": [],
        "decisions_made": [],
        "assumptions_made": [],
        "gaps_opened": [],
        "gaps_closed": [],
        "validation_results": [],
        "safety_events": [],
        "blockers": [],
        "outcome": _sanitize_value(_normalize_text(payload.get("outcome") or "unknown"), "outcome", redactions),
        "next_actions": [],
        "lessons_learned": [],
        "redactions": [],
    }

    for field in _LIST_FIELDS - {"redactions"}:
        record[field] = _dedupe_list(
            _sanitize_value(_normalize_list(payload.get(field)), field, redactions)
        )

    incoming_redactions = _sanitize_value(_normalize_list(payload.get("redactions")), "redactions", redactions)
    combined_redactions = _dedupe_list([*incoming_redactions, *redactions])
    record["redactions"] = combined_redactions

    return record


def log_run(payload: Mapping[str, Any]) -> dict[str, Any]:
    record = prepare_run_record(payload)
    ensure_storage()
    atomic_json_write(run_record_path(record["run_id"]), record)
    _append_jsonl_atomic(ledger_index_path(), record)
    return record


def _read_index_records() -> list[dict[str, Any]]:
    path = ledger_index_path()
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            records.append(row)
    return records


def _read_run_files() -> list[dict[str, Any]]:
    directory = runs_dir()
    if not directory.exists():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(row, dict):
            records.append(row)
    return records


def list_run_records(limit: int = 10) -> list[dict[str, Any]]:
    limit = max(1, int(limit or 10))
    records = _read_index_records() or _read_run_files()
    if not records:
        return []
    latest_by_run_id: dict[str, dict[str, Any]] = {}
    for record in records:
        run_id = _normalize_identifier(record.get("run_id"))
        if run_id:
            latest_by_run_id[run_id] = record
    ordered = sorted(
        latest_by_run_id.values(),
        key=lambda record: (
            _normalize_text(record.get("ended_at")),
            _normalize_text(record.get("started_at")),
            _normalize_identifier(record.get("run_id")),
        ),
        reverse=True,
    )
    return ordered[:limit]


def get_run_record(run_id: str) -> dict[str, Any] | None:
    run_id = validate_run_id(run_id)
    path = run_record_path(run_id)
    if path.exists():
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(row, dict):
                return row
        except (OSError, json.JSONDecodeError):
            pass
    for record in reversed(_read_index_records()):
        if _normalize_identifier(record.get("run_id")) == run_id:
            return record
    return None


def latest_run_record() -> dict[str, Any] | None:
    records = list_run_records(limit=1)
    return records[0] if records else None


def _render_item(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, Mapping):
        ordered_keys = ("check", "tool", "command", "path", "status", "result", "message", "summary", "id")
        parts: list[str] = []
        for key in ordered_keys:
            value = item.get(key)
            if value not in (None, "", [], {}):
                parts.append(f"{key}={value}")
        if parts:
            return ", ".join(parts)
        return json.dumps(item, ensure_ascii=False, sort_keys=True)
    return str(item)


def _section_lines(items: list[Any], *, fallback: str = "(none)", limit: int = 4) -> list[str]:
    if not items:
        return [f"- {fallback}"]
    rendered = [_render_item(item) for item in items[:limit]]
    lines = [f"- {line}" for line in rendered]
    remaining = len(items) - len(rendered)
    if remaining > 0:
        lines.append(f"- (+{remaining} more)")
    return lines


def _successful_validation_items(record: Mapping[str, Any]) -> list[Any]:
    matches: list[Any] = []
    for item in _normalize_list(record.get("validation_results")):
        if isinstance(item, Mapping):
            status = _normalize_text(item.get("status") or item.get("result")).strip().lower()
            if status in _SUCCESS_STATUSES:
                matches.append(item)
    if not matches and _normalize_text(record.get("outcome")).strip().lower() in _SUCCESS_STATUSES:
        matches.append(f"Outcome recorded as {record.get('outcome')}")
    return matches


def _failed_items(record: Mapping[str, Any]) -> list[Any]:
    matches: list[Any] = []
    for item in _normalize_list(record.get("validation_results")):
        if isinstance(item, Mapping):
            status = _normalize_text(item.get("status") or item.get("result")).strip().lower()
            if status in _FAILURE_STATUSES:
                matches.append(item)
    matches.extend(_normalize_list(record.get("blockers")))
    matches.extend(_normalize_list(record.get("safety_events")))
    return matches


def _format_duration(duration_seconds: Any) -> str:
    try:
        seconds = float(duration_seconds)
    except (TypeError, ValueError):
        return "unknown"
    if seconds < 60:
        return f"{seconds:.3f}s" if seconds and seconds != int(seconds) else f"{int(seconds)}s"
    minutes, secs = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m {secs}s"


def _improvement_recommendation(record: Mapping[str, Any]) -> str:
    lessons = _normalize_list(record.get("lessons_learned"))
    if lessons:
        return _render_item(lessons[0])
    blockers = _normalize_list(record.get("blockers"))
    if blockers:
        return f"Reduce blocker recurrence: {_render_item(blockers[0])}"
    validations = _normalize_list(record.get("validation_results"))
    if not validations:
        return "Capture explicit validation results next time so the ledger can distinguish success from assumption."
    return "Wire this command into the invoking runtime path so run records are emitted automatically, not only via manual logging."


def render_after_action_report(record: Mapping[str, Any]) -> str:
    plan_triplet = " / ".join(
        value or "-"
        for value in (
            _normalize_identifier(record.get("plan_id")),
            _normalize_identifier(record.get("job_id")),
            _normalize_identifier(record.get("task_id")),
        )
    )
    tools = ", ".join(_normalize_list(record.get("tools_used"))) or "(none recorded)"
    lines = [
        f"run_id: {record.get('run_id', '')}",
        f"lane: {record.get('lane', '')} | outcome: {record.get('outcome', '')} | duration: {_format_duration(record.get('duration_seconds'))}",
        f"task: {record.get('task_name', '') or '(unnamed task)'}",
        f"trigger: {record.get('instruction_summary', '') or '(not recorded)'}",
        f"plan/job/task: {plan_triplet}",
        f"tools: {tools}",
        f"commands: {len(_normalize_list(record.get('commands_run')))} | files inspected: {len(_normalize_list(record.get('files_inspected')))} | files changed: {len(_normalize_list(record.get('files_changed')))}",
        "",
        "what happened:",
        * _section_lines([
            f"{record.get('task_name', '') or 'Run'} finished with outcome={record.get('outcome', 'unknown')} in {_format_duration(record.get('duration_seconds'))}",
        ], fallback="(not recorded)", limit=1),
        "what worked:",
        * _section_lines(_successful_validation_items(record), fallback="No explicit successful validations recorded"),
        "what failed:",
        * _section_lines(_failed_items(record), fallback="No explicit failures recorded"),
        "gaps opened:",
        * _section_lines(_normalize_list(record.get("gaps_opened"))),
        "gaps closed:",
        * _section_lines(_normalize_list(record.get("gaps_closed"))),
        "decisions made:",
        * _section_lines(_normalize_list(record.get("decisions_made"))),
        "next action:",
        * _section_lines(_normalize_list(record.get("next_actions"))),
        "improvement recommendation:",
        f"- {_improvement_recommendation(record)}",
    ]
    return "\n".join(lines)
