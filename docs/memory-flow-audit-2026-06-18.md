# Shay memory flow audit — 2026-06-18

Status: fixed
Scope: built-in prompt memory routing (`MEMORY.md` / `USER.md`) and off-prompt spillover behavior

## What was wrong

Root cause was not a mystery backend. It was simpler and worse:

1. Live runtime still used the built-in `MemoryStore` in `tools/memory_tool.py` as the write target for every accepted memory entry.
2. That store enforced hard character ceilings on `~/.shay/memories/MEMORY.md` and `~/.shay/memories/USER.md`.
3. There was no code path that redirected bulky detail to Obsidian or any other off-prompt truth surface.
4. So the intended architecture existed mostly as doctrine/docs, while the live write path still behaved like prompt memory was the storage layer.
5. Once `USER.md` and `MEMORY.md` drifted near the configured cap, new writes could fail with the familiar "memory full / exceed the limit" behavior.

## End-to-end flow audited

Verified surfaces and wiring:

- Identity startup layer: `~/.shay/SOUL.md` and `~/.shay/PERSONA.md`
- Prompt memory layer: `~/.shay/memories/MEMORY.md` and `~/.shay/memories/USER.md`
- Runtime code path: `run_agent.py` -> `tools/memory_tool.py`
- Historical recall: `~/.shay/state.db` via `session_search`
- Shared truth surfaces: `~/famtastic/obsidian/...` via MCP and direct file access
- Live config: `~/.shay/config.yaml` still uses built-in memory provider

## Fix applied

### Code

Updated `tools/memory_tool.py` to add spillover-aware routing:

- Large or over-limit memory writes/replacements no longer fail by default.
- Instead, the built-in memory tool now:
  - writes the full detail to an off-prompt spillover ledger
  - keeps prompt memory limited to a compact pointer entry
- Default spillover target is:
  - `~/famtastic/obsidian/01-Shay-Platform/Prompt-Memory/MEMORY-DETAILS.md`
  - `~/famtastic/obsidian/01-Shay-Platform/Prompt-Memory/USER-DETAILS.md`
- If the shared vault path is unavailable, fallback is `~/.shay/private/prompt-memory/`
- Override supported with `SHAY_PROMPT_MEMORY_VAULT`

Routing triggers now include:

- projected prompt-memory size would exceed the configured limit
- single entry is large enough to be prompt-bloat on its own
- store is already crowded and the new entry is still sizable

### Runtime memory surfaces

Compacted live prompt memory files so they behave more like thin index layers again:

- `~/.shay/memories/USER.md`
- `~/.shay/memories/MEMORY.md`

Both were rewritten into shorter declarative entries with pointer-style language, while leaving long-form detail to off-prompt truth surfaces.

### Docs / truth surfaces

Updated:

- `docs/shay-memory-hierarchy.md`
- `~/famtastic/obsidian/01-Shay-Platform/Agent-Capability-Matrix.md`
- this audit note

## Proof

### Targeted tests

Passed:

- `./scripts/run_tests.sh tests/tools/test_memory_tool.py`
- `./scripts/run_tests.sh tests/tools/test_session_search.py tests/run_agent/test_memory_provider_init.py`

### Direct runtime-style proof

Ad hoc verification against `MemoryStore` with a temp memory dir and temp spillover vault showed:

- compact entries stayed in prompt memory
- a larger third entry was auto-routed to the spillover ledger
- the result returned `spillover: True`
- `MEMORY.md` retained only compact entries plus the pointer entry
- the full long entry was preserved in the spillover markdown file

## Lessons learned

- Memory doctrine is worthless if the live write path still treats prompt memory like bulk storage.
- Session-memory integrity work and prompt-memory compaction are related but not the same layer; both need to be right.
- Pointer-style architecture should be enforced in code, not only described in docs.
- Replacements matter as much as adds; if only `add()` spills over, prompt bloat comes back through `replace()`.
- The always-injected layer should stay mixed and thin: compact durable facts inline, larger detail off-prompt behind pointers.
- Research recall has the same shape problem: capture alone is not enough without an enforced preflight against prior artifacts.

## Recommendations

- Keep `USER.md` + `MEMORY.md` under a practical combined target of ~2k chars so injected memory stays useful instead of noisy.
- Add a future retrieval layer that can consult spillover ledgers deliberately when a pointer-backed detail is needed.
- Consider a periodic compaction/audit command that reports prompt-memory size, duplicate drift, and pointer coverage.
- Keep the shared Obsidian spillover ledgers as the default target so off-prompt detail remains durable and inspectable across sessions.
- Apply the same closed-loop principle to research: preflight first, capture second, then resume from the saved artifact next time.

## Remaining gap

This closes the write-path failure and restores pointer-style behavior for new writes.

What it does NOT do automatically yet:

- semantic retrieval from spillover ledgers without an explicit search/read step
- auto-compaction of every historical prompt-memory entry into curated Obsidian notes

That is acceptable for this repair because the blocking failure was the live write path, not retrieval infrastructure.
