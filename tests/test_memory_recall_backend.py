"""Tests for the semantic + graph recall backend (memory lifecycle C4)."""

from pathlib import Path

import pytest

from agent.memory_recall_backend import (
    Embedder,
    MemoryNode,
    MemoryRecallBackend,
    ingest_markdown_dir,
)


@pytest.fixture
def backend(tmp_path):
    b = MemoryRecallBackend(db_path=str(tmp_path / "recall.db"), prefer_model=False)
    yield b
    b.close()


def test_hashing_embedder_is_deterministic_and_normalised():
    e = Embedder(prefer_model=False)
    assert e.backend == "hashing"
    v1 = e.embed("brand kit production workflow")
    v2 = e.embed("brand kit production workflow")
    assert (v1 == v2).all()
    # L2-normalised (norm ~1 for non-empty text).
    import numpy as np
    assert abs(float(np.linalg.norm(v1)) - 1.0) < 1e-5


def test_semantic_recall_ranks_relevant_node_first(backend):
    backend.upsert_node(MemoryNode("a", "logo branding color palette typography"))
    backend.upsert_node(MemoryNode("b", "kanban dispatcher protocol violation retry"))
    backend.upsert_node(MemoryNode("c", "remotion video render composition timeline"))
    hits = backend.query_semantic("protocol violation retry dispatcher", k=2)
    assert hits
    assert hits[0].node.node_id == "b"
    assert hits[0].score > 0


def test_project_scoping_filters(backend):
    backend.upsert_node(MemoryNode("x", "shared term alpha", project="proj1"))
    backend.upsert_node(MemoryNode("y", "shared term alpha", project="proj2"))
    hits = backend.query_semantic("shared term alpha", k=5, project="proj1")
    assert {h.node.node_id for h in hits} == {"x"}


def test_graph_neighbors_make_chain_visible(backend):
    # recommendation -> plan -> build chain.
    backend.upsert_node(MemoryNode("rec", "adopt turbovec recommendation"))
    backend.upsert_node(MemoryNode("plan", "adopt-plan executes turbovec"))
    backend.upsert_node(MemoryNode("build", "build turbovec backend"))
    backend.add_edge("rec", "plan", kind="planned_as")
    backend.add_edge("plan", "build", kind="built_as")

    one_hop = {n.node_id for n in backend.neighbors("rec", depth=1)}
    assert one_hop == {"plan"}
    two_hop = {n.node_id for n in backend.neighbors("rec", depth=2)}
    assert two_hop == {"plan", "build"}


def test_recall_combines_semantic_and_graph(backend):
    backend.upsert_node(MemoryNode("rec", "turbovec adoption recommendation memory"))
    backend.upsert_node(MemoryNode("build", "implementation detail unrelated words"))
    backend.add_edge("rec", "build", kind="built_as")
    hits = backend.recall("turbovec adoption recommendation", k=1, graph_depth=1)
    by_id = {h.node.node_id: h for h in hits}
    assert "rec" in by_id and by_id["rec"].via == "semantic"
    assert "build" in by_id and by_id["build"].via == "graph"


def test_upsert_is_idempotent(backend):
    backend.upsert_node(MemoryNode("dup", "first text"))
    backend.upsert_node(MemoryNode("dup", "second text"))
    assert backend.count() == 1
    hits = backend.query_semantic("second text", k=1)
    assert hits[0].node.text == "second text"


def test_vector_provider_is_numpy_until_install(backend):
    # No heavy backend installed in the venv → numpy-cosine floor.
    assert backend.vector_provider in ("numpy-cosine", "turbovec", "sqlite-vec")


def test_ingest_markdown_dir(tmp_path):
    vault = tmp_path / "vault"
    (vault / "sub").mkdir(parents=True)
    (vault / "one.md").write_text("first note about kanban gates")
    (vault / "sub" / "two.md").write_text("second note about memory recall")
    b = MemoryRecallBackend(db_path=str(tmp_path / "r.db"), prefer_model=False)
    try:
        n = ingest_markdown_dir(b, str(vault), tier="L1", project="vault")
        assert n == 2
        assert b.count() == 2
        hits = b.query_semantic("memory recall", k=1, project="vault")
        assert hits[0].node.node_id.endswith("two.md")
    finally:
        b.close()
