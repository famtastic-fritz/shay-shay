"""Session memo persistence — stage (b) SAVE/COMPACT of the memory lifecycle.

The context compressor already generates a structured handoff summary
(``## Active Task`` … ``## Critical Context``) when it compacts a session.
Historically that summary lived only in the in-memory transcript and was
thrown away when the process exited. This module persists it as a
first-class L1 *episodic* note so the nightly dreamer (``reflect.py``) and
the next session's carry-forward can read it.

Design: ``research/memory-lifecycle-design-2026-05-31.md`` §3(b).

The memo is written to::

    ~/famtastic/obsidian/Shay-Memory/reflections/episodic/sessions/<session_id>.md

with front-matter (``memory_layer: L1``, ``memory/l1`` tag, ``session_id``,
``started_at``/``ended_at``, ``platform``, ``project``, ``model``,
``memo_schema: handoff-v1``) and the handoff-summary sections verbatim as
the body. Writes are idempotent: re-persisting the same session overwrites
its single file (matches the L0-L3 schema's per-date idempotency rule).

No new memory store, no LLM call here — the summary is supplied by the
caller (the compressor's already-generated handoff). Secret-scrubbing is
the summary template's responsibility (the ``[REDACTED]`` instruction);
this module additionally strips obvious key/token lines as belt-and-braces.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Default vault location. Overridable via SHAY_MEMORY_VAULT for tests / other
# hosts. The path is intentionally outside the shay-shay repo (the vault is a
# separate Obsidian store).
_DEFAULT_VAULT = "~/famtastic/obsidian/Shay-Memory"

# Belt-and-braces secret scrub. The summary template already instructs the
# aux model to write [REDACTED]; this catches anything that slips through a
# short-session direct-from-transcript path.
_SECRET_LINE_RE = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|password|passwd|bearer|"
    r"authorization|connection[_-]?string|aws_secret|private[_-]?key)\b"
    r"\s*[:=]\s*\S+"
)


def _vault_root() -> Path:
    raw = os.environ.get("SHAY_MEMORY_VAULT", _DEFAULT_VAULT)
    return Path(raw).expanduser()


def sessions_dir() -> Path:
    """Return the L1 episodic sessions directory (created on demand)."""
    return _vault_root() / "reflections" / "episodic" / "sessions"


def _scrub_secrets(text: str) -> str:
    out_lines = []
    for line in text.splitlines():
        if _SECRET_LINE_RE.search(line):
            # Replace the value but keep the label so the memo still records
            # that a credential was present (per the template's intent).
            out_lines.append(_SECRET_LINE_RE.sub(r"\1: [REDACTED]", line))
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


def _safe_session_id(session_id: str) -> str:
    """Make a session id safe to use as a filename."""
    sid = (session_id or "unknown").strip()
    sid = re.sub(r"[^A-Za-z0-9._-]+", "-", sid)
    return sid[:120] or "unknown"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _yaml_quote(value: Optional[str]) -> str:
    """Quote a scalar for single-line YAML front-matter."""
    if value is None:
        return '""'
    s = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def build_memo_markdown(
    *,
    session_id: str,
    summary_body: str,
    started_at: Optional[str] = None,
    ended_at: Optional[str] = None,
    platform: Optional[str] = None,
    project: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    """Render the full memo markdown (front-matter + scrubbed body)."""
    ended = ended_at or _now_iso()
    body = _scrub_secrets((summary_body or "").strip())
    front = [
        "---",
        f"session_id: {_yaml_quote(session_id)}",
        "memory_layer: L1",
        f"started_at: {_yaml_quote(started_at)}",
        f"ended_at: {_yaml_quote(ended)}",
        f"platform: {_yaml_quote(platform)}",
        f"project: {_yaml_quote(project)}",
        f"model: {_yaml_quote(model)}",
        "memo_schema: handoff-v1",
        "tags:",
        "  - memory/l1",
        "  - session-memo",
        "---",
        "",
        f"# Session memo — {session_id}",
        "",
        body,
        "",
    ]
    return "\n".join(front)


def persist_session_memo(
    *,
    session_id: str,
    summary_body: str,
    started_at: Optional[str] = None,
    ended_at: Optional[str] = None,
    platform: Optional[str] = None,
    project: Optional[str] = None,
    model: Optional[str] = None,
    vault_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Persist a session memo to the L1 episodic sessions folder.

    Returns the written path, or ``None`` when there is nothing worth
    persisting (empty/whitespace summary) or on write failure. Never
    raises — session-end teardown must not be blocked by a memo failure.

    Idempotent: writing the same ``session_id`` overwrites its single file.
    """
    if not summary_body or not summary_body.strip():
        return None
    try:
        out_dir = Path(vault_dir) if vault_dir is not None else sessions_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{_safe_session_id(session_id)}.md"
        markdown = build_memo_markdown(
            session_id=session_id,
            summary_body=summary_body,
            started_at=started_at,
            ended_at=ended_at,
            platform=platform,
            project=project,
            model=model,
        )
        path.write_text(markdown, encoding="utf-8")
        return path
    except Exception:
        return None


def detect_project(shay_home: Optional[str] = None) -> Optional[str]:
    """Best-effort project scope key: git root of cwd, else cwd basename.

    Used as the memo's ``project`` front-matter so carry-forward can scope
    recall to the right project.
    """
    try:
        import subprocess

        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return os.path.basename(proc.stdout.strip())
    except Exception:
        pass
    try:
        return os.path.basename(os.getcwd()) or None
    except Exception:
        return None
