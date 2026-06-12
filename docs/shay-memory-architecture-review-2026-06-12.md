# Shay-Shay memory architecture review

Banner: This document is a diagnostic snapshot from 2026-06-12. Canonical memory policy now lives in `docs/shay-memory-hierarchy.md` and its companion policy docs.

Date: 2026-06-12
Repo root reviewed: `/Users/famtasticfritz/famtastic/shay-shay-build`
Runtime home reviewed: `/Users/famtasticfritz/.shay`

## Executive summary

Shay currently has three real active memory planes and two passive/archive planes.

Active by default at session start:
1. `~/.shay/SOUL.md` and `~/.shay/PERSONA.md` are loaded into the system prompt as identity/voice layers.
2. `~/.shay/memories/MEMORY.md` and `~/.shay/memories/USER.md` are loaded into a built-in `MemoryStore` and injected into the system prompt as a frozen snapshot.
3. Project context files (`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `SHAY.md`, cwd context files) are injected as context layers.

Active on demand, not auto-injected:
4. `~/.shay/state.db` is the actual long-term conversation recall store. `session_search` reads from SQLite session/message history, not from the JSON session files.
5. The Obsidian vault at `~/famtastic/obsidian` is live through MCP (`basic-memory`, `vault-search`, `obsidian`) and functions as structured/shared knowledge, but only when a tool calls into it.

Passive / not part of the default runtime prompt:
6. `~/.shay/private/` is intentionally excluded from shared vault indexing and not auto-loaded into the prompt.
7. `~/.shay/sessions/*.json` are legacy/auxiliary artifacts. They still exist on disk and some session-index metadata is still used by the gateway, but they are no longer the primary recall system.

Bottom line: the real runtime brain is not one thing. It is a layered stack:
- identity files
- bounded prompt memory
- SQLite recall
- MCP vault knowledge
- private off-prompt notes
- leftover JSON artifacts

## What I inspected

### Live config
File: `~/.shay/config.yaml`

Relevant active settings:
- `memory.memory_enabled: true`
- `memory.user_profile_enabled: true`
- `memory.memory_char_limit: 4000`
- `memory.user_char_limit: 4000`
- `memory.provider: builtin`
- `sessions.write_json_snapshots: false`
- MCP enabled:
  - `obsidian` pointed at `/Users/famtasticfritz/famtastic/obsidian`
  - `basic-memory` enabled
  - `vault-search` enabled

Interpretation:
- Built-in prompt memory is active.
- External memory provider plugins are not active right now.
- JSON session snapshots are disabled as the intended primary session persistence path, but old snapshot files remain on disk.
- Vault-backed knowledge access is active via tools, not via auto-prompt injection.

### Live runtime files
- `~/.shay/SOUL.md` — 21,193 chars, 264 lines
- `~/.shay/PERSONA.md` — 7,264 chars, 155 lines
- `~/.shay/memories/MEMORY.md` — 3,925 chars, 25 lines
- `~/.shay/memories/USER.md` — 3,988 chars, 33 lines
- `~/.shay/state.db` — 239,255,552 bytes
  - `sessions`: 469
  - `messages`: 14,728
  - FTS tables present: `messages_fts`, `messages_fts_trigram`
- `~/.shay/shay.db` — size 0, no tables
- `~/.shay/sessions/` — 628 files total
  - 625 `.json`
  - 3 `.jsonl`
  - `sessions.json` present

Interpretation:
- `MEMORY.md` and `USER.md` are both close to the configured 4,000-char ceiling.
- `state.db` is the real historical recall substrate.
- `shay.db` is effectively unused in the current wiring.
- The sessions directory is still carrying a large amount of legacy/session artifact baggage.

### Shared and private vaults
- Shared vault path confirmed: `~/famtastic/obsidian`
- `basic-memory` project `famtastic` is live and queryable
- `vault-search` semantic retrieval is live and queryable
- Private vault exists at `~/.shay/private/README.md`
  - explicitly documented as not indexed by `basic-memory`
  - explicitly documented as not covered by `vault-search`
  - explicitly documented as outside the shared Obsidian vault

## Actual runtime wiring

## 1) Identity layer: ACTIVE and auto-injected

Source files:
- `~/.shay/SOUL.md`
- `~/.shay/PERSONA.md`

Code path:
- `agent/prompt_builder.py`
  - `load_soul_md()` loads `get_shay_home() / "SOUL.md"`
  - `load_persona_md()` loads `get_shay_home() / "PERSONA.md"`
- `run_agent.py` builds these into the stable system-prompt layer before volatile memory blocks

Behavior:
- This is session-start identity, not tool-retrieved recall.
- It is active every session as part of the prompt assembly.
- It is not just documentation; it is runtime behavioral wiring.

Classification:
- ACTIVE
- AUTO-INJECTED
- STABLE SESSION PREFIX

## 2) Built-in bounded memory layer: ACTIVE and auto-injected

Source files:
- `~/.shay/memories/MEMORY.md`
- `~/.shay/memories/USER.md`

Code path:
- `tools/memory_tool.py`
  - `get_memory_dir()` resolves to `get_shay_home() / "memories"`
  - `load_from_disk()` reads `MEMORY.md` and `USER.md`
  - `_system_prompt_snapshot` stores the frozen prompt copy
  - `format_for_system_prompt()` returns the frozen snapshot, not the live mutable state
- `run_agent.py`
  - creates `MemoryStore` when `memory_enabled` or `user_profile_enabled` is true
  - loads from disk during init
  - injects memory/user blocks into the volatile prompt section

Behavior:
- The system prompt gets a snapshot taken at load time.
- Mid-session `memory` tool writes persist to disk immediately but do not update the in-flight prompt snapshot.
- The snapshot refreshes on next session load, and can also be reloaded if `_invalidate_system_prompt()` runs after compression.

Important nuance:
- The code comments call this "volatile" prompt content, but operationally it is session-stable unless the prompt cache is invalidated.
- So it is active, but not truly live-reactive turn to turn.

Classification:
- ACTIVE
- AUTO-INJECTED
- FROZEN SNAPSHOT PER SESSION

Risk note:
- Both files are near the 4,000-char cap already, so this layer is close to saturation.

## 3) External memory provider plugin layer: INACTIVE

Config:
- `memory.provider: builtin`

Code path:
- `run_agent.py` only initializes `_memory_manager` if `mem_config.get("provider")` is non-empty
- The external provider prompt block is only appended if `_memory_manager` exists and returns content

Behavior:
- No external plugin memory provider is active right now.
- No `honcho`, `mem0`, `hindsight`, etc. layer is participating in the current prompt/runtime.

Classification:
- INACTIVE
- CONFIGURED OFF

## 4) SQLite conversation recall layer: ACTIVE on demand

Primary store:
- `~/.shay/state.db`

Code path:
- `shay_state.py`
  - `DEFAULT_DB_PATH = get_shay_home() / "state.db"`
  - session and message tables are first-class
  - FTS5 tables `messages_fts` and trigram FTS are created
- `run_agent.py`
  - lazy `_get_session_db_for_recall()` fallback creates `SessionDB()` if needed
- `tools/session_search_tool.py`
  - searches past sessions via SQLite/FTS and summarizes matches

Behavior:
- This is the real long-term transcript recall plane.
- It is not auto-injected into the prompt.
- It becomes active when `session_search` is called or when session persistence/retrieval features use `SessionDB`.

Classification:
- ACTIVE
- TOOL-RETRIEVED / ON-DEMAND
- PRIMARY HISTORICAL RECALL STORE

## 5) Shared Obsidian knowledge layer: ACTIVE on demand

Stores/services:
- Shared vault: `~/famtastic/obsidian`
- MCP servers:
  - `basic-memory`
  - `vault-search`
  - `obsidian`

Observed runtime behavior:
- `basic-memory` directory listing worked and showed the full five-stream vault structure plus Shay documents.
- `basic-memory recent_activity` returned live recent notes/observations.
- `vault-search` semantic retrieval returned `01-Shay/SHAY-PERSONA.md` and recovery notes.

Behavior:
- This layer is real and live.
- It is not injected automatically into the system prompt.
- It behaves as a structured/shared knowledge substrate callable by tool.

Classification:
- ACTIVE
- TOOL-RETRIEVED / ON-DEMAND
- SHARED KNOWLEDGE BASE

## 6) Private vault layer: PASSIVE and intentionally isolated

Store:
- `~/.shay/private/`

Observed contract from README:
- not indexed by `basic-memory`
- not covered by `vault-search`
- not part of shared Obsidian vault
- intended for reasoning logs, observations, strategy, dreams

Behavior:
- Present on disk
- intentionally excluded from the shared recall stack
- not auto-injected into prompt
- not discoverable through the current shared MCP routes

Classification:
- PASSIVE / MANUAL
- PRIVATE
- OFF-PROMPT

This is architecturally important: it exists, but it is not currently wired into the normal working brain.

## 7) JSON session artifacts: PASSIVE with one narrow active seam

Store:
- `~/.shay/sessions/`

Config says:
- `sessions.write_json_snapshots: false`

Code reality:
- `gateway/session.py` still loads/saves `sessions.json` for session key -> ID mapping
- transcript persistence has moved to SQLite (`state.db`)
- many legacy `.json` session files still remain on disk

Behavior:
- Not the primary recall source anymore
- Still partially active for gateway bookkeeping/index mapping
- Large leftover artifact set remains

Classification:
- MOSTLY PASSIVE
- LEGACY / AUXILIARY
- PARTIALLY ACTIVE FOR GATEWAY SESSION INDEXING

## Active/passive layer map

### Active by default every session
- `~/.shay/SOUL.md`
- `~/.shay/PERSONA.md`
- `~/.shay/memories/MEMORY.md` snapshot
- `~/.shay/memories/USER.md` snapshot
- project context files from cwd/repo

### Active only when called through tools/code
- `~/.shay/state.db` via `session_search` and session DB utilities
- `~/famtastic/obsidian` via `basic-memory`, `vault-search`, `obsidian`

### Present but passive / excluded from default runtime
- `~/.shay/private/`
- `~/.shay/sessions/*.json` legacy snapshots
- `~/.shay/shay.db`

## What is actually "the brain" right now

If the question is "what memory actually shapes Shay's behavior in a normal session?" the answer is:

Primary behavioral brain:
1. SOUL.md
2. PERSONA.md
3. MEMORY.md snapshot
4. USER.md snapshot
5. repo/project context files

Primary recall brain:
6. `state.db` session/message history through `session_search`
7. Obsidian shared vault through MCP

Private subconscious / not yet surfaced by default:
8. `~/.shay/private/`

Legacy residue:
9. `~/.shay/sessions/*.json`
10. `~/.shay/shay.db`

## Gaps and tensions

### 1) Prompt memory is nearly full
- `MEMORY.md`: 3,925 / 4,000 chars
- `USER.md`: 3,988 / 4,000 chars

Impact:
- very little headroom remains for new durable facts
- future saves will start failing or force churn

### 2) "Active memory" is split across two different access modes
- prompt memory is auto-loaded
- session/db/vault memory is tool-loaded

Impact:
- Shay can know something exists without automatically carrying it into the turn
- this is good for token cost, but bad if the retrieval discipline is inconsistent

### 3) Private vault exists but is not integrated into normal cognition
Impact:
- the place intended for thinking logs and intimate observations is architecturally isolated
- that protects privacy, but also means it does not inform normal runtime unless explicitly read

### 4) Legacy session artifact sprawl remains
Impact:
- `~/.shay/sessions/` still looks like a live primary memory store even though it mostly is not
- raises ambiguity about what is canonical

### 5) `shay.db` exists but is empty
Impact:
- another false affordance / confusing surface
- invites wrong assumptions during debugging

## Recommended truth model

Use this as the canonical mental model going forward:

- Identity/behavior source of truth:
  - `~/.shay/SOUL.md`
  - `~/.shay/PERSONA.md`

- Durable prompt memory source of truth:
  - `~/.shay/memories/MEMORY.md`
  - `~/.shay/memories/USER.md`

- Canonical conversation recall source of truth:
  - `~/.shay/state.db`

- Canonical shared knowledge source of truth:
  - `~/famtastic/obsidian` through `basic-memory` + `vault-search`

- Canonical private/off-grid thought store:
  - `~/.shay/private/`

- Legacy/non-canonical residue:
  - `~/.shay/sessions/*.json`
  - `~/.shay/shay.db`

## Best next moves

1. Declare this hierarchy explicitly in docs/code comments so nobody keeps confusing JSON sessions with real recall.
2. Create a memory compaction strategy for `MEMORY.md` and `USER.md` before they hard-stop.
3. Decide whether `~/.shay/private/` should remain fully manual or get a deliberate, opt-in retrieval path.
4. Audit whether legacy session JSON files should be pruned, archived, or clearly labeled as non-canonical.
5. Either remove `shay.db` from the mental map or wire it to a real purpose.

## Conclusion

Shay's current memory architecture is not broken, but it is layered and easy to misread.

The active runtime personality is coming from SOUL/PERSONA plus bounded prompt memory.
The active historical recall is coming from SQLite.
The active shared knowledge is coming from the Obsidian vault over MCP.
The private vault is real but intentionally off the main line.
The JSON session pile is mostly residue.

That is the real wiring as of this review.