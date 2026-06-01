"""Local intelligence event ledger for Shay-Shay.

The ledger is intentionally small and boring: append-only JSONL under the
active ``SHAY_HOME``. It gives higher-level analyzers a durable, inspectable
signal stream without coupling them to session DB internals, gateway logs, or
external observability vendors.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Iterable

from shay_constants import get_shay_home

_DEFAULT_MAX_FIELD_CHARS = 4_000
_SECRET_KEY_RE = re.compile(r"(api[_-]?key|token|secret|password|credential|authorization)", re.I)
_SECRET_VALUE_RE = re.compile(
    r"\b(?:sk-[A-Za-z0-9_-]{16,}|pk-[A-Za-z0-9_-]{16,}|[A-Za-z0-9_-]{32,})\b"
)
_WRITE_LOCK = threading.Lock()


class IntelligenceLedgerError(RuntimeError):
    """Raised when a ledger event cannot be persisted or read."""


def is_enabled() -> bool:
    """Return whether local intelligence ledger writes are enabled.

    The ledger defaults ON because it only writes local metadata. Operators can
    disable writes with ``SHAY_INTELLIGENCE_ENABLED=0`` / ``false`` / ``off``.
    """
    value = os.environ.get("SHAY_INTELLIGENCE_ENABLED", "").strip().lower()
    return value not in {"0", "false", "no", "off", "disabled"}


def intelligence_home() -> Path:
    """Return the profile-scoped intelligence directory."""
    return get_shay_home() / "intelligence"


def events_path() -> Path:
    """Return the profile-scoped JSONL event ledger path."""
    return intelligence_home() / "events.jsonl"


def append_event(
    event_type: str,
    *,
    summary: str = "",
    metadata: dict[str, Any] | None = None,
    source: str = "shay",
    session_id: str = "",
    task_id: str = "",
    ts: float | None = None,
) -> dict[str, Any] | None:
    """Append a sanitized intelligence event and return the stored record.

    Returns ``None`` when the ledger is disabled. ``event_type`` should be a
    stable dotted string such as ``tool.failed`` or ``delegation.completed``.
    """
    if not is_enabled():
        return None

    normalized_type = str(event_type or "").strip()
    if not normalized_type:
        raise ValueError("event_type is required")

    record = {
        "id": uuid.uuid4().hex,
        "ts": float(time.time() if ts is None else ts),
        "type": normalized_type,
        "source": _truncate(str(source or "shay")),
        "session_id": _truncate(str(session_id or "")),
        "task_id": _truncate(str(task_id or "")),
        "summary": _sanitize_value(summary),
        "metadata": _sanitize_value(metadata or {}),
    }

    path = events_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False, sort_keys=True)
        with _WRITE_LOCK:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
    except OSError as exc:
        raise IntelligenceLedgerError(f"Could not append intelligence event: {exc}") from exc

    return record


def read_events(
    *,
    limit: int | None = 100,
    event_type: str | None = None,
    since_ts: float | None = None,
    path: Path | None = None,
) -> list[dict[str, Any]]:
    """Read recent intelligence events from the JSONL ledger.

    Invalid JSONL rows are skipped so one corrupted line does not brick the
    whole report. Results preserve file order, then apply the trailing limit.
    """
    ledger_path = path or events_path()
    if not ledger_path.exists():
        return []

    events: list[dict[str, Any]] = []
    try:
        with ledger_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict):
                    continue
                if event_type and event.get("type") != event_type:
                    continue
                if since_ts is not None:
                    try:
                        if float(event.get("ts", 0)) < since_ts:
                            continue
                    except (TypeError, ValueError):
                        continue
                events.append(event)
    except OSError as exc:
        raise IntelligenceLedgerError(f"Could not read intelligence events: {exc}") from exc

    if limit is None:
        return events
    safe_limit = max(0, int(limit))
    if safe_limit == 0:
        return []
    return events[-safe_limit:]


def summarize_events(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Return lightweight counts for report/briefing code."""
    counts: dict[str, int] = {}
    sources: dict[str, int] = {}
    total = 0
    latest_ts = None
    for event in events:
        total += 1
        event_type = str(event.get("type") or "unknown")
        source = str(event.get("source") or "unknown")
        counts[event_type] = counts.get(event_type, 0) + 1
        sources[source] = sources.get(source, 0) + 1
        try:
            ts = float(event.get("ts"))
        except (TypeError, ValueError):
            ts = None
        if ts is not None and (latest_ts is None or ts > latest_ts):
            latest_ts = ts
    return {
        "total": total,
        "by_type": dict(sorted(counts.items())),
        "by_source": dict(sorted(sources.items())),
        "latest_ts": latest_ts,
    }


def _sanitize_value(value: Any, *, key: str = "") -> Any:
    if _SECRET_KEY_RE.search(key):
        return "[REDACTED]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _redact_string(_truncate(value))
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            clean_key = _truncate(str(raw_key), max_chars=256)
            clean[clean_key] = _sanitize_value(raw_value, key=clean_key)
        return clean
    if isinstance(value, (list, tuple, set)):
        return [_sanitize_value(item, key=key) for item in value]
    return _redact_string(_truncate(str(value)))


def _truncate(value: str, *, max_chars: int = _DEFAULT_MAX_FIELD_CHARS) -> str:
    if len(value) <= max_chars:
        return value
    return value[:max_chars] + f"... [truncated {len(value) - max_chars} chars]"


def _redact_string(value: str) -> str:
    return _SECRET_VALUE_RE.sub("[REDACTED]", value)
