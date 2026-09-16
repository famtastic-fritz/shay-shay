"""Small append-only, redacted effect-decision ledger."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path


_SECRET_KEYS = {"api_key", "authorization", "credential", "password", "secret", "token"}


def _redact(value):
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if k.lower() in _SECRET_KEYS else _redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


class DecisionLedger:
    """Thread-safe JSONL writer; one row per resolved effect decision."""

    def __init__(self, path: str | os.PathLike | None = None):
        self.path = Path(path or os.getenv("SHAY_EFFECT_LEDGER", "~/.shay/effect-decisions.jsonl")).expanduser()
        self._lock = threading.Lock()

    def append(self, *, rule_id, client, session_id, task_id, tool_call_id,
               effect_id, effect_class, outcome, reason="") -> dict:
        row = {
            "schema_version": 1,
            "recorded_at": time.time(),
            "rule_id": str(rule_id or "policy"),
            "client": str(client or "unknown"),
            "session_id": str(session_id or ""),
            "task_id": str(task_id or ""),
            "tool_call_id": str(tool_call_id or ""),
            "effect_id": str(effect_id or ""),
            "effect_class": str(effect_class or "read"),
            "outcome": str(outcome or "denied"),
            "reason": str(reason or ""),
        }
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(_redact(row), sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        return row
