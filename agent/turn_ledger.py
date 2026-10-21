"""Transport-neutral, content-free contracts for the Shay turn ledger.

The ledger is an operational audit trail, not a transcript.  Payloads are
flat, allowlisted facts and deliberately cannot carry conversation content or
tool inputs/outputs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Optional


CONTRACT_VERSION = 1

ALLOWED_PAYLOAD_FIELDS = frozenset(
    {
        "tool_name", "outcome", "status", "duration_ms", "provider", "model",
        "api_mode", "event_code", "error_code", "count", "size_bytes",
        "input_count", "output_count", "effect_id", "tool_call_id",
        "correlation_id", "source", "surface",
    }
)
_COUNT_FIELDS = frozenset(
    {"duration_ms", "count", "size_bytes", "input_count", "output_count"}
)
_SENSITIVE_KEY = re.compile(
    r"prompt|completion|reasoning|argument|result|command|approval|body|content|"
    r"authorization|credential|password|secret|token|api.?key",
    re.IGNORECASE,
)
_CREDENTIAL_URL = re.compile(r"^[a-z][a-z0-9+.-]*://[^/@\s]+@", re.IGNORECASE)
_BEARER = re.compile(r"\b(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_TOKENISH = re.compile(
    r"sk[-_][A-Za-z0-9_-]{12,}|pk_[A-Za-z0-9_-]{12,}|gh[opsu]_[A-Za-z0-9]{12,}|"
    r"xox[baprs]-[A-Za-z0-9-]{10,}|sk-ant-[A-Za-z0-9_-]{10,}|"
    r"AIza[A-Za-z0-9_-]{35}|(?:AKIA|ASIA)[A-Z0-9]{16}|"
    r"\b\d{6,12}:[A-Za-z0-9_-]{20,}\b|"
    r"\b[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\b",
    re.IGNORECASE,
)
_OPERATIONAL_CODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:@+-]{0,127}")
_MODEL_CODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/@+-]{0,127}")


def _require_operational_code(value: Optional[str], label: str) -> None:
    if value is not None and (
        not isinstance(value, str) or _OPERATIONAL_CODE.fullmatch(value) is None
    ):
        raise ValueError(f"{label} must be a 1-128 character operational code")
    if value is not None and (_CREDENTIAL_URL.search(value) or _BEARER.search(value) or _TOKENISH.search(value)):
        raise ValueError(f"credential-bearing value is forbidden for {label}")


def validate_ledger_identifier(value: str) -> str:
    """Validate persisted identities before any irreversible normalization."""
    if value is None:
        raise ValueError("ledger identifier is required")
    _require_operational_code(value, "ledger identifier")
    return value


def normalize_ledger_payload(payload: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    """Return a JSON-safe allowlisted payload or raise ``ValueError``.

    Unknown fields are rejected instead of silently retained.  Values must be
    short scalar operational facts; nested containers and credential-shaped
    strings are rejected.  The caller therefore cannot accidentally turn this
    metadata channel into a transcript or tool-content store.
    """
    if payload is None:
        return {}
    if not isinstance(payload, Mapping):
        raise TypeError("ledger payload must be a mapping")
    normalized: dict[str, Any] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or key not in ALLOWED_PAYLOAD_FIELDS:
            if isinstance(key, str) and _SENSITIVE_KEY.search(key):
                raise ValueError("sensitive ledger field is forbidden")
            raise ValueError("ledger field is not allowlisted")
        if value is None:
            continue
        if key in _COUNT_FIELDS:
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{key} must be a non-negative integer")
            normalized[key] = value
            continue
        if isinstance(value, bool) or not isinstance(value, str):
            raise ValueError(f"{key} must be a string")
        value = value.strip()
        if _CREDENTIAL_URL.search(value) or _BEARER.search(value) or _TOKENISH.search(value):
            raise ValueError(f"credential-bearing value is forbidden for {key}")
        value_pattern = _MODEL_CODE if key == "model" else _OPERATIONAL_CODE
        if value_pattern.fullmatch(value) is None:
            raise ValueError(f"{key} must be a 1-128 character operational identifier")
        normalized[key] = value
    return normalized


def redact_ledger_payload(payload: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    """Drop non-allowlisted fields, then strictly normalize retained facts.

    This is intended for boundary adapters that receive mixed metadata.  It
    never masks and stores sensitive values: forbidden fields are omitted and
    credential-shaped values in otherwise allowed fields still fail closed.
    """
    if payload is None:
        return {}
    if not isinstance(payload, Mapping):
        raise TypeError("ledger payload must be a mapping")
    return normalize_ledger_payload(
        {key: value for key, value in payload.items() if key in ALLOWED_PAYLOAD_FIELDS}
    )


@dataclass(frozen=True)
class TurnEvent:
    turn_id: str
    sequence: int
    event_type: str
    occurred_at: float
    payload: Mapping[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    version: int = CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.version != CONTRACT_VERSION:
            raise ValueError("unsupported turn event contract version")
        _require_operational_code(self.turn_id, "turn_id")
        _require_operational_code(self.event_type, "event_type")
        _require_operational_code(self.correlation_id, "correlation_id")
        if self.sequence < 1:
            raise ValueError("event sequence must be positive")
        object.__setattr__(self, "payload", MappingProxyType(normalize_ledger_payload(self.payload)))


@dataclass(frozen=True)
class TurnReceipt:
    turn_id: str
    session_id: str
    status: str
    started_at: float
    finished_at: Optional[float] = None
    outcome: Optional[str] = None
    correlation_id: Optional[str] = None
    version: int = CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.version != CONTRACT_VERSION:
            raise ValueError("unsupported turn receipt contract version")
        _require_operational_code(self.turn_id, "turn_id")
        _require_operational_code(self.correlation_id, "correlation_id")
        _require_operational_code(self.outcome, "outcome")
        if self.status not in {"active", "succeeded", "failed", "abandoned"}:
            raise ValueError(f"invalid turn status: {self.status}")
        terminal = self.status != "active"
        if terminal != (self.finished_at is not None):
            raise ValueError("terminal receipts require finished_at")
