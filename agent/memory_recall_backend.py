"""Semantic + graph recall backend (memory lifecycle C4).

The root-cause insight from the impact map: flat-markdown memory with no
graph/link layer means recall is file-grep, not semantic+linked, so Shay
can't connect recommendation -> plan -> build and silently drops items.
This module is the backend that fixes that: a semantic vector index plus a
lightweight graph (edges between memory nodes) over a single local SQLite
file, with a recall API that returns semantic hits AND their graph
neighbours so chains are visible.

Design notes (specs verified 2026-05-31):
  * tencent-agent-memory-adopt — Identity/Experience/Persona tiers map onto
    a ``tier`` column (L0/L1/L2/L3); each node carries a ``node_id`` for
    drill-down tracing, matching the symbolic-memory pattern.
  * turbovec-adopt — TurboVec is the eventual compressed vector index. It
    requires an install (pip + an embedding model), so it is plugged in as
    an OPTIONAL provider. Until installed, an in-process numpy cosine store
    is used so the backend works today with zero new services.
  * rlm-rs-adopt — long-context chunking lives elsewhere; this module only
    stores/retrieves.

DEPLOYMENT DISCIPLINE (Fritz's C4 constraint): this module installs nothing
and touches no running service. The heavy backends (TurboVec, sqlite-vec,
fastembed/sentence-transformers) are detected and used only if already
importable; otherwise the pure-stdlib+numpy path runs. Activating the heavy
path requires an attended install + gateway restart — out of scope here.

All public APIs are import-clean with only numpy + stdlib.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np

_DEFAULT_DB = "~/.shay/memory/recall.db"
_EMBED_DIM = 256  # hashing-embedder dimension; overridden by real models.


# ---------------------------------------------------------------------------
# Embedding layer — pluggable. Real model if importable, else hashing fallback.
# ---------------------------------------------------------------------------
class Embedder:
    """Resolve the best available embedding backend.

    Order: fastembed -> sentence-transformers -> deterministic hashing
    (numpy, zero deps). The hashing embedder is NOT semantically strong but
    keeps the backend fully functional offline with no install; it is the
    documented "works now, upgrade attended" floor.
    """

    def __init__(self, prefer_model: bool = True):
        self.backend = "hashing"
        self.dim = _EMBED_DIM
        self._model = None
        if prefer_model:
            self._try_load_model()

    def _try_load_model(self) -> None:
        try:
            from fastembed import TextEmbedding  # type: ignore

            self._model = TextEmbedding()
            self.backend = "fastembed"
            # Probe dimension lazily on first embed.
            self.dim = 384
            return
        except Exception:
            self._model = None
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore

            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            self.backend = "sentence-transformers"
            self.dim = 384
            return
        except Exception:
            self._model = None

    def _hash_embed(self, text: str) -> np.ndarray:
        """Deterministic bag-of-tokens hashing embedding (L2-normalised)."""
        vec = np.zeros(self.dim, dtype=np.float32)
        for tok in _tokenize(text):
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 8) & 1 else -1.0
            vec[idx] += sign
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def embed(self, text: str) -> np.ndarray:
        if self._model is not None:
            try:
                if self.backend == "fastembed":
                    arr = np.asarray(list(self._model.embed([text]))[0], dtype=np.float32)
                else:  # sentence-transformers
                    arr = np.asarray(self._model.encode(text), dtype=np.float32)
                self.dim = int(arr.shape[0])
                norm = np.linalg.norm(arr)
                return arr / norm if norm > 0 else arr
            except Exception:
                pass
        return self._hash_embed(text)


def _tokenize(text: str) -> List[str]:
    out: List[str] = []
    cur = []
    for ch in (text or "").lower():
        if ch.isalnum():
            cur.append(ch)
        else:
            if cur:
                out.append("".join(cur))
                cur = []
    if cur:
        out.append("".join(cur))
    return out


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class MemoryNode:
    node_id: str
    text: str
    tier: str = "L1"          # L0 raw / L1 episodic / L2 semantic / L3 reflective
    project: Optional[str] = None
    source_path: Optional[str] = None
    created_at: float = field(default_factory=time.time)


@dataclass
class RecallHit:
    node: MemoryNode
    score: float
    via: str = "semantic"     # "semantic" | "graph"


# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------
class MemoryRecallBackend:
    """Semantic vector index + graph edges over one local SQLite file.

    Vector store provider: an in-process numpy cosine index persisted to the
    ``nodes`` table (embeddings stored as float32 blobs). When TurboVec /
    sqlite-vec become importable, a future provider can swap in behind the
    same ``query_semantic`` method — the schema already keeps raw vectors.
    """

    def __init__(self, db_path: Optional[str] = None, prefer_model: bool = True):
        raw = db_path or os.environ.get("SHAY_RECALL_DB", _DEFAULT_DB)
        self.db_path = str(Path(raw).expanduser())
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.embedder = Embedder(prefer_model=prefer_model)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
        self._vector_provider = _detect_vector_provider()

    @property
    def vector_provider(self) -> str:
        """Name of the active vector provider ('numpy-cosine' until an
        attended install makes TurboVec/sqlite-vec importable)."""
        return self._vector_provider

    @property
    def embedding_backend(self) -> str:
        return self.embedder.backend

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS nodes (
                node_id     TEXT PRIMARY KEY,
                text        TEXT NOT NULL,
                tier        TEXT NOT NULL DEFAULT 'L1',
                project     TEXT,
                source_path TEXT,
                created_at  REAL NOT NULL,
                dim         INTEGER NOT NULL,
                embedding   BLOB NOT NULL
            );
            CREATE TABLE IF NOT EXISTS edges (
                src    TEXT NOT NULL,
                dst    TEXT NOT NULL,
                kind   TEXT NOT NULL DEFAULT 'related',
                weight REAL NOT NULL DEFAULT 1.0,
                PRIMARY KEY (src, dst, kind)
            );
            CREATE INDEX IF NOT EXISTS idx_nodes_project ON nodes(project);
            CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src);
            CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst);
            """
        )
        self.conn.commit()

    # -- ingest -----------------------------------------------------------
    def upsert_node(self, node: MemoryNode) -> str:
        emb = self.embedder.embed(node.text).astype(np.float32)
        self.conn.execute(
            "INSERT INTO nodes(node_id, text, tier, project, source_path, "
            "created_at, dim, embedding) VALUES(?,?,?,?,?,?,?,?) "
            "ON CONFLICT(node_id) DO UPDATE SET text=excluded.text, "
            "tier=excluded.tier, project=excluded.project, "
            "source_path=excluded.source_path, dim=excluded.dim, "
            "embedding=excluded.embedding",
            (
                node.node_id, node.text, node.tier, node.project,
                node.source_path, node.created_at, int(emb.shape[0]),
                emb.tobytes(),
            ),
        )
        self.conn.commit()
        return node.node_id

    def add_edge(self, src: str, dst: str, kind: str = "related",
                 weight: float = 1.0) -> None:
        """Add a directed graph edge (e.g. recommendation -> plan -> build).

        This is the flat-file graph stand-in the design names: associations
        as edges now, swappable for a real graph DB later.
        """
        self.conn.execute(
            "INSERT INTO edges(src, dst, kind, weight) VALUES(?,?,?,?) "
            "ON CONFLICT(src, dst, kind) DO UPDATE SET weight=excluded.weight",
            (src, dst, kind, weight),
        )
        self.conn.commit()

    # -- query ------------------------------------------------------------
    def _row_to_node(self, row: sqlite3.Row) -> MemoryNode:
        return MemoryNode(
            node_id=row["node_id"], text=row["text"], tier=row["tier"],
            project=row["project"], source_path=row["source_path"],
            created_at=row["created_at"],
        )

    def query_semantic(self, query: str, k: int = 5,
                       project: Optional[str] = None) -> List[RecallHit]:
        """Return top-k nodes by cosine similarity, optionally project-scoped."""
        qv = self.embedder.embed(query).astype(np.float32)
        sql = "SELECT * FROM nodes"
        params: list = []
        if project:
            sql += " WHERE project = ?"
            params.append(project)
        rows = self.conn.execute(sql, params).fetchall()
        scored: List[RecallHit] = []
        for row in rows:
            emb = np.frombuffer(row["embedding"], dtype=np.float32)
            if emb.shape[0] != qv.shape[0]:
                continue  # dimension mismatch (model changed) — skip safely
            denom = (np.linalg.norm(emb) * np.linalg.norm(qv))
            score = float(np.dot(emb, qv) / denom) if denom else 0.0
            scored.append(RecallHit(self._row_to_node(row), score, "semantic"))
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:k]

    def neighbors(self, node_id: str, depth: int = 1) -> List[MemoryNode]:
        """Graph-expand: nodes reachable from ``node_id`` within ``depth`` hops
        (following edges in both directions). Makes chains visible."""
        seen = {node_id}
        frontier = {node_id}
        out: List[MemoryNode] = []
        for _ in range(max(0, depth)):
            if not frontier:
                break
            placeholders = ",".join("?" * len(frontier))
            rows = self.conn.execute(
                f"SELECT src, dst FROM edges WHERE src IN ({placeholders}) "
                f"OR dst IN ({placeholders})",
                (*frontier, *frontier),
            ).fetchall()
            nxt = set()
            for r in rows:
                for nid in (r["src"], r["dst"]):
                    if nid not in seen:
                        seen.add(nid)
                        nxt.add(nid)
            frontier = nxt
        ids = seen - {node_id}
        if not ids:
            return out
        placeholders = ",".join("?" * len(ids))
        rows = self.conn.execute(
            f"SELECT * FROM nodes WHERE node_id IN ({placeholders})", tuple(ids),
        ).fetchall()
        return [self._row_to_node(r) for r in rows]

    def recall(self, query: str, k: int = 5, project: Optional[str] = None,
               graph_depth: int = 1) -> List[RecallHit]:
        """Full recall: semantic top-k, then graph-expanded neighbours.

        Returns semantic hits first (by score), followed by deduped graph
        neighbours of the top hit — so a query that matches a recommendation
        also surfaces its linked plan/build nodes (the chain that flat-grep
        could not connect).
        """
        sem = self.query_semantic(query, k=k, project=project)
        results: List[RecallHit] = list(sem)
        seen_ids = {h.node.node_id for h in sem}
        if sem and graph_depth > 0:
            for n in self.neighbors(sem[0].node.node_id, depth=graph_depth):
                if n.node_id not in seen_ids:
                    seen_ids.add(n.node_id)
                    results.append(RecallHit(n, score=0.0, via="graph"))
        return results

    def count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0])

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass


def _detect_vector_provider() -> str:
    """Report which compressed vector backend is available.

    Returns the heavy provider name if importable, else 'numpy-cosine'.
    Detection only — never installs. Activating TurboVec/sqlite-vec needs an
    attended install + gateway restart.
    """
    import importlib.util as u
    if u.find_spec("turbovec"):
        return "turbovec"
    if u.find_spec("sqlite_vec"):
        return "sqlite-vec"
    return "numpy-cosine"


def ingest_markdown_dir(backend: MemoryRecallBackend, root: str,
                        tier: str = "L1",
                        project: Optional[str] = None) -> int:
    """Ingest every ``.md`` file under ``root`` as a memory node.

    node_id = relative path. Idempotent (upsert). Returns count ingested.
    Used to seed the index from the vault's session memos / reflections.
    """
    rootp = Path(root).expanduser()
    n = 0
    if not rootp.is_dir():
        return 0
    for p in rootp.rglob("*.md"):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        backend.upsert_node(MemoryNode(
            node_id=str(p.relative_to(rootp)),
            text=text,
            tier=tier,
            project=project,
            source_path=str(p),
        ))
        n += 1
    return n
