"""Recall router (memory lifecycle C5) — flag-gated rewire onto the C4 backend.

Recall today is flat: the vault-search MCP / basic-memory grep the markdown
vault. C5 rewires recall so a query goes query -> vector + graph -> injected
context via the C4 ``MemoryRecallBackend``, with the legacy flat path retired
BEHIND A FLAG so the live gateway is unaffected until the switch is flipped.

Flag (env): ``SHAY_RECALL_BACKEND``
  * ``flat``  (default) — use the legacy flat recall callable supplied by the
    caller. Nothing changes; safe on the live gateway with no restart.
  * ``c4``    — route recall through ``MemoryRecallBackend`` (semantic + graph).
    The heavy vector/embedding backends still need an attended install +
    gateway restart to reach full performance; until then this runs on the
    numpy-cosine + hashing floor, which is functional but not as strong.

This module is scaffolding: it wires the route and the flag so flipping
``SHAY_RECALL_BACKEND=c4`` (after the attended C4 activation) swaps recall
with no further code change. It never restarts the gateway or installs
anything.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, List, Optional

# Default vault locations to seed the C4 index from on first activation.
# These are the markdown stores the legacy flat recall used to grep.
_DEFAULT_SEED_DIRS = ("~/.shay/memories",)


def recall_backend_mode() -> str:
    """Return the active recall mode: 'c4' or 'flat' (default)."""
    val = (os.environ.get("SHAY_RECALL_BACKEND") or "flat").strip().lower()
    return "c4" if val in ("c4", "graph", "vector", "semantic") else "flat"


def _seed_dirs() -> list:
    """Seed dirs, overridable via SHAY_RECALL_SEED_DIRS (os.pathsep list)."""
    raw = os.environ.get("SHAY_RECALL_SEED_DIRS")
    if raw:
        return [d for d in raw.split(os.pathsep) if d.strip()]
    return list(_DEFAULT_SEED_DIRS)


def ensure_seeded(backend) -> int:
    """Seed an empty C4 backend from the vault once (idempotent).

    If the backend already has nodes, this is a no-op. Otherwise it ingests
    the default vault dirs so a fresh ``SHAY_RECALL_BACKEND=c4`` flip returns
    real hits instead of an empty index. Returns nodes ingested this call.
    """
    try:
        if backend.count() > 0:
            return 0
    except Exception:
        return 0
    from agent.memory_recall_backend import ingest_markdown_dir

    total = 0
    for d in _seed_dirs():
        if Path(d).expanduser().is_dir():
            try:
                total += ingest_markdown_dir(backend, d, tier="L1", project="vault")
            except Exception:
                continue
    return total


def _format_hits(hits) -> str:
    """Render C4 RecallHit list as an injectable context block."""
    if not hits:
        return ""
    lines = ["# Recalled context (semantic + graph)"]
    for h in hits:
        node = h.node
        tag = "graph" if h.via == "graph" else f"score {h.score:.2f}"
        src = node.source_path or node.node_id
        snippet = (node.text or "").strip().replace("\n", " ")
        if len(snippet) > 240:
            snippet = snippet[:240] + "…"
        lines.append(f"- [{node.tier}|{tag}] `{src}`: {snippet}")
    return "\n".join(lines)


def route_recall(
    query: str,
    *,
    project: Optional[str] = None,
    k: int = 5,
    flat_recall: Optional[Callable[[str], str]] = None,
    backend=None,
) -> str:
    """Route a recall query through the active backend and return context text.

    When the flag is ``c4`` and a backend is reachable, runs the C4
    semantic+graph recall and formats the hits. Otherwise falls back to the
    caller-supplied ``flat_recall`` callable (the legacy path). On any C4
    error, also falls back to flat so recall never hard-fails. Returns "" if
    nothing is available.
    """
    mode = recall_backend_mode()

    if mode == "c4":
        try:
            be = backend
            if be is None:
                from agent.memory_recall_backend import MemoryRecallBackend
                be = MemoryRecallBackend()
                # First activation on a fresh index: seed from the vault so
                # c4 returns real hits instead of an empty result.
                ensure_seeded(be)
            hits = be.recall(query, k=k, project=project, graph_depth=1)
            block = _format_hits(hits)
            if block:
                return block
            # Empty C4 result — fall through to flat as a backstop.
        except Exception:
            pass  # fall back to flat on any failure

    if flat_recall is not None:
        try:
            return flat_recall(query) or ""
        except Exception:
            return ""
    return ""


__all__ = ["recall_backend_mode", "route_recall", "ensure_seeded"]
