from pathlib import Path

from agent.intelligence_prefetch import (
    build_intelligence_prefetch,
    parse_pointer_sources,
    default_intelligence_sources,
)


def test_parse_prompt_memory_spillover_pointer_expands_path(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    sources = parse_pointer_sources([
        "Prompt-memory spillover ledger: ~/vault/MEMORY-DETAILS.md",
        "ordinary static fact",
    ])

    assert len(sources) == 1
    assert sources[0].path == tmp_path / "vault" / "MEMORY-DETAILS.md"
    assert sources[0].preferred_tool == "read_file"


def test_build_prefetch_dereferences_relevant_pointer(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("SHAY_HOME", str(tmp_path / ".shay"))
    ledger = tmp_path / "vault" / "MEMORY-DETAILS.md"
    ledger.parent.mkdir(parents=True)
    ledger.write_text("# Memory Details\n\nGoDaddy billing visibility gap lives here.", encoding="utf-8")

    block = build_intelligence_prefetch(
        "what about godaddy billing",
        memory_entries=[f"Prompt-memory spillover ledger: {ledger}"],
        home=tmp_path,
    )

    assert "Shay intelligence prefetch" in block
    assert str(ledger) in block
    assert "GoDaddy billing visibility gap" in block
    assert "preferred_tool: read_file" in block


def test_build_prefetch_includes_default_gap_research_when_present(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAY_HOME", str(tmp_path / ".shay"))
    gap = tmp_path / "famtastic" / "obsidian" / "01-Shay-Platform" / "gap-research" / "latest-gap-research.md"
    gap.parent.mkdir(parents=True)
    gap.write_text("# Latest Gap Research\n\nRecurring cPanel issue.", encoding="utf-8")

    block = build_intelligence_prefetch("cpanel", home=tmp_path)

    assert "latest gap research" in block
    assert "Recurring cPanel issue" in block


def test_build_prefetch_returns_empty_when_no_sources(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAY_HOME", str(tmp_path / ".shay"))
    assert build_intelligence_prefetch("anything", home=tmp_path) == ""


def test_current_root_wins_and_legacy_install_still_works(tmp_path, monkeypatch):
    monkeypatch.setenv("SHAY_HOME", str(tmp_path / ".shay"))
    suffix = Path("01-Shay-Platform/gap-research/latest-gap-research.md")
    legacy = tmp_path / "famtastic/obsidian" / suffix
    current = tmp_path / "Development/FAMtastic/obsidian" / suffix
    legacy.parent.mkdir(parents=True)
    legacy.write_text("Legacy evidence")
    assert "Legacy evidence" in build_intelligence_prefetch("gap research", home=tmp_path)
    current.parent.mkdir(parents=True)
    current.write_text("Current evidence")
    block = build_intelligence_prefetch("gap research", home=tmp_path)
    assert "Current evidence" in block
    assert "Legacy evidence" not in block
    current.unlink()
    # Once the current vault exists, do not mix missing artifacts with old ones.
    assert "Legacy evidence" not in build_intelligence_prefetch("gap research", home=tmp_path)


def test_missing_roots_resolve_to_current_layout(tmp_path):
    source = default_intelligence_sources(tmp_path)[0]
    assert source.path.is_relative_to(tmp_path / "Development/FAMtastic/obsidian")
