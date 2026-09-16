"""Versioned, adapter-neutral client domain contract for Shay.

The contract is deliberately a projection over the R3 Kanban authority.  It
does not own a second task/session store and it does not replace any transport.
All returned values are plain JSON-compatible dictionaries so CLI, TUI, API,
and ACP can preserve their existing wire formats while sharing identifiers,
statuses, replay semantics, and errors.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Optional

from .kanban_db import (
    VALID_STATUSES,
    active_run,
    cancel_run,
    get_task,
    latest_run,
    list_events_after,
    unblock_task,
)

PROTOCOL_NAME = "shay.client"
PROTOCOL_VERSION = "shay.client.v1"
PROTOCOL_MAJOR = 1
PROTOCOL_MINOR = 0

TERMINAL_STATUSES = frozenset(
    {"completed", "done", "failed", "blocked", "cancelled", "interrupted", "archived"}
)


class DomainContractError(ValueError):
    """Stable client-facing error with a machine-readable code."""

    def __init__(self, code: str, message: str, *, details: Optional[Mapping[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})

    def as_dict(self) -> dict[str, Any]:
        return {
            "object": "shay.error",
            "protocol": PROTOCOL_VERSION,
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


class IncompatibleVersionError(DomainContractError):
    def __init__(self, version: Any):
        super().__init__(
            "incompatible_version",
            f"Unsupported Shay client protocol version: {version!r}",
            details={"expected_major": PROTOCOL_MAJOR, "received": version},
        )


def require_compatible_version(version: Any) -> None:
    """Accept v1 readers and fail closed for missing/major-incompatible input."""
    if version is None:
        raise IncompatibleVersionError(version)
    value = str(version).strip()
    if value == PROTOCOL_VERSION:
        return
    # Be tolerant of a future v1 minor version for readers that only consume
    # additive fields.  A different major version is never silently accepted.
    if value.startswith(f"{PROTOCOL_NAME}.v1"):
        suffix = value[len(f"{PROTOCOL_NAME}.v1") :]
        if not suffix or re.fullmatch(r"\.\d+", suffix):
            return
    raise IncompatibleVersionError(version)


def _json_value(value: Any) -> Any:
    """Return a JSON-safe copy, preserving unknown additive fields."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(v) for v in value]
    return str(value)


@dataclass(frozen=True)
class ContractObject:
    object: str
    protocol: str = PROTOCOL_VERSION

    def as_dict(self) -> dict[str, Any]:
        return _json_value(asdict(self))


@dataclass(frozen=True)
class Capability(ContractObject):
    object: str = "shay.capability"
    name: str = ""
    available: bool = False
    source: str = ""
    reason: Optional[str] = None


@dataclass(frozen=True)
class Usage(ContractObject):
    object: str = "shay.usage"
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_usd: Optional[float] = None


@dataclass(frozen=True)
class EffectProjection(ContractObject):
    object: str = "shay.effect"
    schema_version: str = "shay.effect.v1"
    authority_ref: str = ""
    effect_id: str = ""
    status: str = ""


@dataclass(frozen=True)
class MemoryProvenance(ContractObject):
    object: str = "shay.memory_provenance"
    schema_version: str = "shay.memory-provenance.v1"
    authority_ref: str = ""
    record_id: str = ""
    source: str = ""


@dataclass(frozen=True)
class Session(ContractObject):
    object: str = "shay.session"
    session_id: str = ""
    status: str = "unknown"
    client: Optional[str] = None
    task_id: Optional[str] = None


@dataclass(frozen=True)
class Approval(ContractObject):
    object: str = "shay.approval"
    approval_id: Optional[str] = None
    status: str = "unavailable"
    actor: Optional[str] = None


@dataclass(frozen=True)
class ErrorObject(ContractObject):
    object: str = "shay.error"
    code: str = ""
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EventObject(ContractObject):
    object: str = "shay.event"
    event_id: int = 0
    task_id: str = ""
    run_id: Optional[int] = None
    kind: str = ""
    payload: Optional[dict[str, Any]] = None
    created_at: Optional[int] = None


@dataclass(frozen=True)
class RunObject(ContractObject):
    object: str = "shay.run"
    run_id: Optional[int] = None
    task_id: str = ""
    status: str = "unknown"
    outcome: Optional[str] = None
    started_at: Optional[int] = None
    ended_at: Optional[int] = None
    summary: Optional[str] = None
    error: Optional[str] = None
    usage: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class TaskObject(ContractObject):
    object: str = "shay.task"
    task_id: str = ""
    title: str = ""
    status: str = "unknown"
    created_at: Optional[int] = None
    started_at: Optional[int] = None
    completed_at: Optional[int] = None
    result: Optional[str] = None
    run: Optional[dict[str, Any]] = None
    effect: Optional[dict[str, Any]] = None
    memory_provenance: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        _validate_optional_projection(self.effect, "shay.effect.v1", "effect")
        _validate_optional_projection(
            self.memory_provenance, "shay.memory-provenance.v1", "memory_provenance"
        )


@dataclass(frozen=True)
class EventPage(ContractObject):
    object: str = "shay.event_page"
    task_id: str = ""
    after_event_id: int = 0
    next_event_id: int = 0
    has_more: bool = False
    events: tuple[dict[str, Any], ...] = ()


def _validate_optional_projection(
    projection: Optional[Mapping[str, Any]], expected_schema: str, name: str
) -> None:
    """Validate optional R4/R5 projections without inventing authority.

    A missing projection is explicitly unavailable. If a caller supplies one,
    it must identify its schema and the durable authority that produced it;
    otherwise accepting it would turn unverified metadata into a claim.
    """
    if projection is None:
        return
    if not isinstance(projection, Mapping):
        raise DomainContractError("invalid_projection", f"{name} must be an object")
    if projection.get("schema_version") != expected_schema:
        raise DomainContractError(
            "invalid_projection", f"{name}.schema_version must be {expected_schema!r}"
        )
    authority = projection.get("authority_ref")
    if not isinstance(authority, str) or not authority.strip():
        raise DomainContractError(
            "invalid_projection", f"{name}.authority_ref is required when populated"
        )


def _task_object(conn: sqlite3.Connection, task_id: str) -> TaskObject:
    task = get_task(conn, task_id)
    if task is None:
        raise DomainContractError("task_not_found", f"Task not found: {task_id}", details={"task_id": task_id})
    run = active_run(conn, task_id) or latest_run(conn, task_id)
    run_obj = None
    if run is not None:
        run_obj = RunObject(
            run_id=run.id,
            task_id=run.task_id,
            status=run.status or run.outcome or "unknown",
            outcome=run.outcome,
            started_at=run.started_at,
            ended_at=run.ended_at,
            summary=run.summary,
            error=run.error,
            usage=(run.metadata if isinstance(run.metadata, dict) and "usage" in run.metadata else None),
        ).as_dict()
    return TaskObject(
        task_id=task.id,
        title=task.title,
        status=task.status,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        result=task.result,
        run=run_obj,
        # Optional projections are unavailable on the R3 ancestry.  ``None``
        # is intentional: it is not a fabricated zero/empty/safe value.
        effect=None,
        memory_provenance=None,
    )


class DomainService:
    """The sole public lifecycle seam shared by client adapters."""

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def inspect_task(self, task_id: str) -> dict[str, Any]:
        return _task_object(self.connection, str(task_id)).as_dict()

    def list_task_events(self, task_id: str, after_event_id: int = 0) -> dict[str, Any]:
        try:
            cursor = int(after_event_id)
        except (TypeError, ValueError) as exc:
            raise DomainContractError("invalid_cursor", "after_event_id must be an integer") from exc
        if cursor < 0:
            raise DomainContractError("invalid_cursor", "after_event_id must be non-negative")
        # Validate existence even when the task has no events.
        _task_object(self.connection, str(task_id))
        events = list_events_after(self.connection, str(task_id), cursor=cursor)
        projected = tuple(
            EventObject(
                event_id=event.id,
                task_id=event.task_id,
                run_id=event.run_id,
                kind=event.kind,
                payload=_json_value(event.payload),
                created_at=event.created_at,
            ).as_dict()
            for event in events
        )
        next_id = projected[-1]["event_id"] if projected else cursor
        return EventPage(
            task_id=str(task_id), after_event_id=cursor, next_event_id=next_id,
            has_more=False, events=projected,
        ).as_dict()

    def cancel_task(self, task_id: str, actor: str) -> dict[str, Any]:
        task = _task_object(self.connection, str(task_id))
        if not actor or not str(actor).strip():
            raise DomainContractError("invalid_actor", "actor is required")
        run = active_run(self.connection, str(task_id)) or latest_run(self.connection, str(task_id))
        # A terminal cancellation replay is idempotent. Other terminal states
        # remain immutable and are reported truthfully as no-op.
        changed = cancel_run(
            self.connection, str(task_id),
            run_id=(run.id if run else None), actor=str(actor).strip(),
            reason=f"cancel requested by {str(actor).strip()}",
        ) if run is not None else False
        return {"changed": bool(changed), "task": self.inspect_task(str(task_id))}

    def retry_task(self, task_id: str, actor: str) -> dict[str, Any]:
        if not actor or not str(actor).strip():
            raise DomainContractError("invalid_actor", "actor is required")
        current = _task_object(self.connection, str(task_id))
        changed = False
        if current.status == "blocked":
            changed = unblock_task(self.connection, str(task_id))
        elif current.status in {"ready", "todo", "triage", "running"}:
            changed = False  # already retryable/in-flight; no duplicate run
        else:
            raise DomainContractError(
                "not_retryable", f"Task {task_id} is terminal and cannot be retried", details={"status": current.status}
            )
        return {"changed": bool(changed), "task": self.inspect_task(str(task_id)), "actor": str(actor).strip()}

    def resume_task(self, task_id: str, actor: str) -> dict[str, Any]:
        if not actor or not str(actor).strip():
            raise DomainContractError("invalid_actor", "actor is required")
        current = _task_object(self.connection, str(task_id))
        # Restart recovery intentionally leaves interrupted work blocked. A
        # resume is an explicit operator action and uses the same Kanban
        # unblock transition as retry; it never claims a worker prematurely.
        if current.status == "blocked":
            changed = unblock_task(self.connection, str(task_id))
        elif current.status in {"ready", "todo", "running"}:
            changed = False
        else:
            raise DomainContractError(
                "not_resumable", f"Task {task_id} cannot be resumed from {current.status}", details={"status": current.status}
            )
        return {"changed": bool(changed), "task": self.inspect_task(str(task_id)), "actor": str(actor).strip()}


def contract_fixture(*, task_id: str = "task-fixture", client: str = "cli") -> dict[str, Any]:
    """Return a stable transport fixture for adapter compatibility tests."""
    return {
        "protocol": PROTOCOL_VERSION,
        "client": client,
        "capability": Capability(name="task.lifecycle", available=True, source="shay_cli.domain_contract").as_dict(),
        "session": Session(session_id=f"session-{task_id}", task_id=task_id, client=client).as_dict(),
        "approval": Approval().as_dict(),
        "usage": Usage().as_dict(),
        "error": ErrorObject(code="example", message="example").as_dict(),
    }


__all__ = [
    "PROTOCOL_NAME", "PROTOCOL_VERSION", "TERMINAL_STATUSES", "Capability",
    "DomainContractError", "DomainService", "EffectProjection", "ErrorObject",
    "EventObject", "EventPage", "IncompatibleVersionError", "MemoryProvenance",
    "RunObject", "Session", "Approval", "TaskObject", "Usage",
    "contract_fixture", "require_compatible_version",
]
