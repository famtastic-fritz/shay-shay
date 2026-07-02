"""Permissioned ambient context connectors for Shay intelligence prefetch.

Connectors are read-only by default, source-labeled, TTL-bound, and safe to
turn off globally.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Protocol


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class AmbientContextItem:
    source: str
    label: str
    summary: str
    confidence: float
    captured_at: str
    ttl_seconds: int
    private: bool = False
    persist: bool = True


class AmbientConnector(Protocol):
    name: str
    def collect(self) -> Iterable[AmbientContextItem]: ...


@dataclass(frozen=True)
class LocalArtifactConnector:
    paths: tuple[Path, ...]
    ttl_seconds: int = 3600
    name: str = "local_artifacts"

    def collect(self) -> Iterable[AmbientContextItem]:
        for path in self.paths:
            p = path.expanduser()
            if not p.exists() or not p.is_file():
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace").strip()
            except OSError:
                continue
            if not text:
                continue
            yield AmbientContextItem(str(p), p.name, text[:220], 0.8, _now(), self.ttl_seconds)


@dataclass(frozen=True)
class ProcessSnapshotConnector:
    ttl_seconds: int = 900
    name: str = "process_snapshot"

    def collect(self) -> Iterable[AmbientContextItem]:
        # Read-only lightweight process signal. No command execution here; callers
        # that need richer runtime truth should use explicit terminal probes.
        yield AmbientContextItem(
            "process_snapshot",
            "current process",
            f"pid={os.getpid()} cwd={os.getcwd()}",
            0.6,
            _now(),
            self.ttl_seconds,
            private=False,
            persist=False,
        )


@dataclass(frozen=True)
class SessionRecentConnector:
    summaries: tuple[str, ...]
    ttl_seconds: int = 3600
    name: str = "session_recent"

    def collect(self) -> Iterable[AmbientContextItem]:
        for idx, summary in enumerate(self.summaries, start=1):
            clean = " ".join(str(summary).split())
            if clean:
                yield AmbientContextItem("session_recent", f"recent session item {idx}", clean[:220], 0.7, _now(), self.ttl_seconds)


def collect_ambient_context(connectors: Iterable[AmbientConnector], *, enabled: bool = True, persist_private_sources: bool = False) -> list[dict]:
    if not enabled:
        return []
    items: list[dict] = []
    for connector in connectors:
        for item in connector.collect():
            if item.private and not persist_private_sources:
                items.append({**asdict(item), "summary": "[private source withheld]", "persist": False})
            elif item.persist or not item.private:
                items.append(asdict(item))
    return items


def write_ambient_context(path: Path, items: Iterable[dict]) -> None:
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(list(items), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
