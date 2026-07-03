import json
from pathlib import Path

from agent.memory_manager import MemoryManager
from agent.memory_provider import MemoryProvider


class DummyMemoryProvider(MemoryProvider):
    @property
    def name(self):
        return "dummy"

    def is_available(self):
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        pass

    def get_tool_schemas(self):
        return []

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        return "loaded context for " + query


def test_prefetch_writes_trace(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    manager = MemoryManager()
    manager.add_provider(DummyMemoryProvider())

    context = manager.prefetch_all("that billing thing", session_id="s1")

    assert "loaded context" in context
    trace_path = tmp_path / ".shay/runtime/prefetch/prefetch-proof.jsonl"
    rows = [json.loads(line) for line in trace_path.read_text().splitlines()]
    assert rows[-1]["hit"] is True
    assert rows[-1]["providers"][0]["provider"] == "dummy"
    assert rows[-1]["context_bytes"] > 0
