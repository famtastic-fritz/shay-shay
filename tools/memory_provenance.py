"""Versioned provenance for Shay's built-in memory store.

This module is deliberately a small file-backed sidecar.  ``MemoryStore``
continues to own MEMORY.md and USER.md; this ledger records the evidence for
each change without replacing those files or introducing a vector database.
Records are append-only.  Corrections and removals point at the earlier
record instead of rewriting it.  Candidate records are inert until an owner
decision is explicitly consumed by ``MemoryStore.promote_candidate``.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback is best effort.
    fcntl = None


PROVENANCE_SCHEMA_VERSION = 1
PROVENANCE_FILENAME = "MEMORY-PROVENANCE.jsonl"
DECISIONS_FILENAME = "MEMORY-DECISIONS.jsonl"
PROTECTED_TARGETS = frozenset({"identity", "persona", "soul", "standing_rule"})


def canonical_json(value: Any) -> str:
    """Serialize a value in the stable form used by provenance records."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def profile_id(profile_root: Path) -> str:
    """Return a non-secret, stable binding for one profile root."""
    return hashlib.sha256(str(profile_root.resolve()).encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@contextmanager
def _locked_append(path: Path):
    """Open a sidecar append lock without replacing the sidecar itself."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with lock_path.open("a+", encoding="utf-8") as lock:
        if fcntl is not None:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _append_jsonl(path: Path, row: Dict[str, Any]) -> None:
    payload = (canonical_json(row) + "\n").encode("utf-8")
    with _locked_append(path):
        fd, tmp_name = tempfile.mkstemp(prefix=".memory-provenance-", dir=str(path.parent))
        try:
            # Rewrite by atomic replacement so readers never observe a partial line.
            previous = path.read_bytes() if path.exists() else b""
            with os.fdopen(fd, "wb") as handle:
                handle.write(previous)
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise


class MemoryProvenance:
    """Append-only provenance and owner-decision journal for one profile."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.profile_id = profile_id(self.root)
        self.path = self.root / PROVENANCE_FILENAME
        self.decisions_path = self.root / DECISIONS_FILENAME

    def _read(self, path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            return []
        rows: List[Dict[str, Any]] = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if isinstance(row, dict):
                    rows.append(row)
        except (OSError, UnicodeError, json.JSONDecodeError):
            # Legacy/partial sidecars must not make the built-in memory
            # unavailable.  Valid rows before the bad line remain readable.
            return rows
        return rows

    def records(self) -> List[Dict[str, Any]]:
        return self._read(self.path)

    def decisions(self) -> List[Dict[str, Any]]:
        return self._read(self.decisions_path)

    def _envelope(
        self,
        *,
        record_id: str,
        target: str,
        content: str,
        tier: str,
        write_origin: str,
        source: str,
        session_id: str = "",
        parent_session_id: str = "",
        tool_call_id: str = "",
        task_id: str = "",
        confidence: float = 1.0,
        supersedes_or_tombstones: Optional[Iterable[str]] = None,
        created_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        if target not in {"memory", "user"}:
            raise ValueError("provenance records may target only ordinary memory or user profile")
        if tier not in {"working", "candidate", "curated", "tombstone"}:
            raise ValueError("invalid memory provenance tier")
        return {
            "schema_version": PROVENANCE_SCHEMA_VERSION,
            "record_id": record_id,
            "profile_id": self.profile_id,
            "target": target,
            "tier": tier,
            "content": content,
            "content_hash": content_hash(content),
            "write_origin": write_origin or "unknown",
            "source": source or "memory_tool",
            "session_id": session_id or "",
            "parent_session_id": parent_session_id or "",
            "tool_call_id": tool_call_id or "",
            "task_id": task_id or "",
            "created_at": created_at or utc_now(),
            "confidence": float(confidence),
            "supersedes_or_tombstones": sorted(set(supersedes_or_tombstones or [])),
        }

    def append_record(self, **kwargs: Any) -> Dict[str, Any]:
        row = self._envelope(**kwargs)
        _append_jsonl(self.path, row)
        return row

    def append_decision(
        self,
        *,
        decision_id: str,
        record_id: str,
        decision: str = "approve",
        reviewer: str = "owner",
        profile: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not decision_id or not record_id:
            raise ValueError("decision_id and record_id are required")
        if decision not in {"approve", "reject"}:
            raise ValueError("decision must be approve or reject")
        if any(d.get("decision_id") == decision_id for d in self.decisions()):
            raise ValueError("decision_id has already been recorded")
        row = {
            "schema_version": PROVENANCE_SCHEMA_VERSION,
            "decision_id": decision_id,
            "record_id": record_id,
            "profile_id": profile or self.profile_id,
            "decision": decision,
            "reviewer": reviewer or "owner",
            "decided_at": utc_now(),
        }
        _append_jsonl(self.decisions_path, row)
        return row

    def active_records(self, *, target: Optional[str] = None) -> List[Dict[str, Any]]:
        rows = self.records()
        superseded = {
            old
            for row in rows
            for old in row.get("supersedes_or_tombstones", [])
            if isinstance(old, str)
        }
        return [
            row for row in rows
            if row.get("record_id") not in superseded
            and row.get("tier") in {"candidate", "curated"}
            and (target is None or row.get("target") == target)
        ]

    def curated_records(self, *, target: Optional[str] = None) -> List[Dict[str, Any]]:
        return [r for r in self.active_records(target=target) if r.get("tier") == "curated"]

    def promote(self, record_id: str, decision_id: str) -> Dict[str, Any]:
        rows = self.records()
        candidates = [r for r in rows if r.get("record_id") == record_id]
        if len(candidates) != 1:
            raise ValueError("candidate record was not found")
        candidate = candidates[0]
        if candidate.get("profile_id") != self.profile_id:
            raise ValueError("candidate belongs to another profile")
        if candidate.get("tier") != "candidate":
            raise ValueError("only candidate records can be promoted")
        if candidate.get("target") not in {"memory", "user"}:
            raise ValueError("protected memory targets cannot be promoted")
        decisions = [d for d in self.decisions() if d.get("decision_id") == decision_id]
        if len(decisions) != 1:
            raise ValueError("owner decision was not found")
        decision = decisions[0]
        if decision.get("profile_id") != self.profile_id or decision.get("record_id") != record_id:
            raise ValueError("owner decision does not match this profile and record")
        if decision.get("decision") != "approve":
            raise ValueError("owner decision did not approve promotion")
        if any(r.get("tier") == "curated" and r.get("tool_call_id") == decision_id for r in rows):
            raise ValueError("owner decision has already been consumed")
        promoted = self.append_record(
            record_id=f"memory-{uuid.uuid4().hex}",
            target=candidate["target"], content=candidate["content"], tier="curated",
            write_origin="owner_review", source="memory_promotion",
            session_id=candidate.get("session_id", ""),
            parent_session_id=candidate.get("parent_session_id", ""),
            tool_call_id=decision_id, task_id=candidate.get("task_id", ""),
            confidence=candidate.get("confidence", 1.0),
            supersedes_or_tombstones=[record_id],
        )
        return promoted
