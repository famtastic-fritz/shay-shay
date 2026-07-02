"""Shay intelligence-loop prefetch helpers.

This module closes the pointer/dereference gap without making prompt memory
larger.  It treats MEMORY.md / USER.md as a thin index, expands only the most
relevant dereferenceable pointers, and adds high-signal live intelligence
artifacts before the model has to guess which tool to call.

The prefetcher is deliberately read-only and deterministic: it never mutates
memory, never rewrites capability truth, and never calls an LLM.  Generative
reflection can feed richer L2/L3 artifacts later; this layer is the runtime
bridge that makes those artifacts useful once they exist.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence


_MAX_SOURCE_CHARS = 1200
_MAX_TOTAL_CHARS = 4200
_MAX_POINTERS = 5

_POINTER_PATTERNS = [
    re.compile(r"Prompt-memory spillover ledger:\s*(?P<path>[^\n§]+)", re.IGNORECASE),
    re.compile(r"(?:hot-state pointer|active-state pointer|pointer):\s*(?P<path>~?/[^\n§]+\.md)", re.IGNORECASE),
    re.compile(r"(?:read|see|source|ledger):\s*(?P<path>~?/[^\n§]+\.(?:md|json|jsonl|txt))", re.IGNORECASE),
]

_TOKEN_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{2,}")


@dataclass(frozen=True)
class PrefetchSource:
    label: str
    path: Path
    reason: str
    preferred_tool: str = "read_file"


def _expand_path(raw: str) -> Path:
    text = raw.strip().strip("`'\"")
    # Trim trailing prose punctuation without damaging real filenames.
    text = re.sub(r"[).,;:]+$", "", text)
    return Path(os.path.expandvars(text)).expanduser()


def _query_tokens(query: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(query or "") if len(t) >= 3}


def _source_tokens(source: PrefetchSource) -> set[str]:
    text = f"{source.label} {source.path.name} {source.path.parent.name} {source.reason}"
    return _query_tokens(text)


def _score_source(source: PrefetchSource, query_tokens: set[str], ordinal: int) -> tuple[int, int]:
    if not query_tokens:
        return (0, -ordinal)
    overlap = len(query_tokens & _source_tokens(source))
    # Prefer explicit query hits, but keep deterministic original order for ties.
    return (overlap, -ordinal)


def parse_pointer_sources(entries: Iterable[str]) -> List[PrefetchSource]:
    """Extract dereferenceable file pointers from prompt-memory entries."""
    sources: list[PrefetchSource] = []
    seen: set[Path] = set()
    for entry in entries:
        for pattern in _POINTER_PATTERNS:
            for match in pattern.finditer(entry or ""):
                path = _expand_path(match.group("path"))
                if path in seen:
                    continue
                seen.add(path)
                sources.append(
                    PrefetchSource(
                        label="prompt-memory pointer",
                        path=path,
                        reason=(entry or "").strip().splitlines()[0][:180],
                    )
                )
    return sources


def default_intelligence_sources(home: Path | None = None) -> List[PrefetchSource]:
    """Return high-signal Shay/FAMtastic intelligence artifacts if present.

    These are intentionally broad and safe: they are read-only status surfaces
    that already exist in Fritz's setup and are useful before most platform
    turns. Missing files are filtered later.
    """
    user_home = home or Path.home()
    shay_home = Path(os.environ.get("SHAY_HOME", user_home / ".shay")).expanduser()
    obsidian = user_home / "famtastic" / "obsidian"
    process_intel = shay_home / "process-intelligence" / "intelligence"
    return [
        PrefetchSource(
            "hot context pointer index",
            obsidian / "01-Shay-Platform" / "HOT-CONTEXT-POINTERS.md",
            "session-agnostic hot-state pointers",
        ),
        PrefetchSource(
            "latest gap research",
            obsidian / "01-Shay-Platform" / "gap-research" / "latest-gap-research.md",
            "current gap research output",
        ),
        PrefetchSource(
            "reflection behavior steering",
            obsidian / "Shay-Memory" / "reflections" / "behavior-steering.json",
            "nightly reflection steering payload",
        ),
        PrefetchSource(
            "reflection briefing context",
            obsidian / "Shay-Memory" / "reflections" / "briefing-context.json",
            "nightly reflection briefing payload",
        ),
        PrefetchSource(
            "control-plane runtime plan",
            process_intel / "control-plane-runtime-plan.md",
            "hourly control-plane plan and status",
        ),
    ]


def _read_source(path: Path, *, max_chars: int = _MAX_SOURCE_CHARS) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    text = text.strip()
    if not text:
        return ""

    if path.suffix.lower() == ".json":
        try:
            parsed = json.loads(text)
            text = json.dumps(parsed, indent=2, ensure_ascii=False)
        except Exception:
            pass
    elif path.suffix.lower() == ".jsonl":
        lines = [line for line in text.splitlines() if line.strip()]
        text = "\n".join(lines[-20:])

    if len(text) > max_chars:
        return text[:max_chars].rstrip() + "\n… [prefetch truncated]"
    return text


def build_intelligence_prefetch(
    query: str,
    *,
    memory_entries: Sequence[str] = (),
    user_entries: Sequence[str] = (),
    home: Path | None = None,
    max_sources: int = _MAX_POINTERS,
    max_total_chars: int = _MAX_TOTAL_CHARS,
) -> str:
    """Build a small, fenced-ready prefetch block from relevant pointers.

    The caller should wrap the returned text using the existing memory-context
    fence. Empty string means no relevant sources were available.
    """
    explicit = parse_pointer_sources([*memory_entries, *user_entries])
    candidates = explicit + default_intelligence_sources(home)

    existing: list[PrefetchSource] = []
    seen: set[Path] = set()
    for source in candidates:
        path = source.path.expanduser()
        if path in seen or not path.exists() or not path.is_file():
            continue
        seen.add(path)
        existing.append(PrefetchSource(source.label, path, source.reason, source.preferred_tool))

    if not existing:
        return ""

    q_tokens = _query_tokens(query)
    ranked = sorted(enumerate(existing), key=lambda item: _score_source(item[1], q_tokens, item[0]), reverse=True)

    sections: list[str] = []
    total = 0
    for _, source in ranked[:max_sources]:
        body = _read_source(source.path)
        if not body:
            continue
        header = (
            f"## {source.label}\n"
            f"- source: {source.path}\n"
            f"- preferred_tool: {source.preferred_tool}\n"
            f"- reason: {source.reason}\n\n"
        )
        section = header + body
        if total + len(section) > max_total_chars:
            remaining = max_total_chars - total
            if remaining < 300:
                break
            section = section[:remaining].rstrip() + "\n… [prefetch budget reached]"
        sections.append(section)
        total += len(section)
        if total >= max_total_chars:
            break

    if not sections:
        return ""
    return "Shay intelligence prefetch: dereferenced prompt-memory pointers and live intelligence artifacts.\n\n" + "\n\n---\n\n".join(sections)
