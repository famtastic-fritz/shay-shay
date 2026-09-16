"""Offline end-to-end profile isolation and benchmark checks for R5."""

import json
from pathlib import Path

from tools.memory_tool import MemoryStore


FIXTURE = Path(__file__).parents[1] / "fixtures/memory_provenance_benchmark_v1.json"


def _load_profile(root: Path):
    memory_dir = root / "memories"
    store = MemoryStore()
    # The profile root is injected by the same resolver used in production.
    import tools.memory_tool as memory_tool
    original = memory_tool.get_memory_dir
    memory_tool.get_memory_dir = lambda: memory_dir
    try:
        store.load_from_disk()
        for row in json.loads(FIXTURE.read_text(encoding="utf-8"))["corpus"]:
            store.add(row["target"], row["content"], source=row["source"],
                      confidence=row["confidence"], record_id=row["id"])
    finally:
        memory_tool.get_memory_dir = original
    return store


def test_memory_provenance_benchmark_gate(tmp_path):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    left = _load_profile(tmp_path / "profile-left")
    right = _load_profile(tmp_path / "profile-right")
    assert len(left._provenance.records()) == 32
    assert len(right._provenance.records()) == 32
    for query in payload["queries"]:
        result = left.recall(query["text"], limit=8)
        cited = set(result["record_ids"])
        assert set(query["expected_record_ids"]) <= cited
        assert not cited.intersection(query["forbidden_record_ids"])
        for row in result["provenance"]:
            assert all(field in row and row[field] is not None
                       for field in query["required_provenance_fields"])
    # Distinct profiles never share records or raw memory files.
    assert left._provenance.profile_id != right._provenance.profile_id
    assert left._provenance.path != right._provenance.path
