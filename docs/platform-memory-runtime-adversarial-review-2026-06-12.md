# Platform memory runtime adversarial review — 2026-06-12

## Executive Summary

Verdict: RISKY.

Do not merge the platform branch memory/runtime work as a block.

The branch contains some doctrine-aligned pieces worth salvaging, but it also carries three separate competing memory languages and at least two competing runtime memory planes:

- canonical Shay doctrine
- L1/L0-L3 episodic memo language
- C4/C5 recall-router language
- T0/T1/T2/T3 TypeScript memory-package language

That is not harmless naming drift. That is how canonical memory gets corrupted by “almost the same” systems.

Blunt read:
- prompt memory is mostly safe
- session_search is mostly safe
- session JSON artifacts are not fully contained yet
- session memo persistence is unresolved
- recall-router / recall-backend work is not doctrine-aligned
- the TypeScript memory package is a separate memory philosophy and should not be treated as Shay runtime memory

If merged without redesign, the future Shay codebase will have ambiguous answers to basic questions like:
- what is canonical memory?
- what gets injected automatically?
- what gets recalled only by tool?
- where conversations actually live?
- what tier names are real?

## Canonical Memory Doctrine

Accepted hierarchy from the source-of-truth docs:

1. Identity and operating voice
   - `~/.shay/SOUL.md`
   - `~/.shay/PERSONA.md`
   - active, auto-injected

2. Bounded prompt memory
   - `~/.shay/memories/MEMORY.md`
   - `~/.shay/memories/USER.md`
   - active, auto-injected, compact durable facts only

3. Project/repo context
   - `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `SHAY.md`, similar repo context files
   - active, auto-injected, environment-specific

4. Conversation recall
   - `~/.shay/state.db`
   - canonical historical conversation store
   - retrieval-based

5. Shared knowledge vault
   - `~/famtastic/obsidian` through MCP services like `basic-memory`, `vault-search`, `obsidian`
   - retrieval-based shared knowledge

6. Private memory vault
   - `~/.shay/private/`
   - private-by-default
   - not auto-injected
   - any retrieval must be explicit and opt-in

7. Legacy/auxiliary artifacts
   - `~/.shay/sessions/*.json`
   - `~/.shay/sessions/sessions.json`
   - `~/.shay/shay.db`
   - non-canonical unless a documented runtime role exists

Hard doctrine boundaries:
- `state.db` is the canonical conversation recall layer
- session JSON artifacts are not canonical historical memory
- `shay.db` is not an active canonical memory store
- `~/.shay/private/` must not auto-load
- shared-vault retrieval should happen through the shared MCP surfaces, not parallel ad hoc vault readers
- memory retrieval outside prompt memory should remain explicit / retrieval-based, not ambient by default

## Runtime Memory Inventory

Below is the memory-related concept map found in the platform branch.

| Concept | File/path | Purpose | Class | Canonical match? |
|---|---|---|---|---|
| SOUL/PERSONA runtime identity loading and governance prompt | `agent/prompt_builder.py` | Defines active identity loading and identity preamble | prompt memory / identity | Yes |
| Built-in durable memory guidance for `MEMORY.md` / `USER.md` | `agent/prompt_builder.py` | Reinforces bounded prompt memory doctrine | prompt memory | Yes |
| Built-in disk-backed memory store for `MEMORY.md` / `USER.md` | `run_agent.py` | Auto-injects bounded durable memory | prompt memory | Yes |
| Explicit `session_search` guidance | `agent/prompt_builder.py` | Tells runtime to use recall tool for past conversations | recall memory | Yes |
| SessionDB-backed transcript search | `tools/session_search_tool.py` | Canonical conversation recall from `state.db` | recall memory | Yes |
| SessionDB fallback accessor for recall | `run_agent.py` | Ensures `session_search` uses SessionDB | recall memory | Yes |
| Gateway session metadata + transcript persistence with JSON mirror/fallback | `gateway/session.py` | Session routing, bookkeeping, transcript loading | archive / recall seam | Partial / risky |
| Context compaction summary handoff | `agent/context_compressor.py` | Compresses long sessions into reference-only summary | archive / prompt-support | Yes |
| Session memo persistence to Obsidian note | `agent/session_memo.py` | Writes handoff summaries as episodic session notes | shared-vault / archive | Partial / unresolved |
| Session-end persistence hook into compressor flow | `agent/context_compressor.py` | Calls `persist_session_memo()` on session finalization | shared-vault / archive | Partial / unresolved |
| External memory provider plugin system | `run_agent.py` + `agent/memory_manager.py` | Optional plugin memory providers with sync/prefetch | recall memory | No, in current form |
| External-memory turn mirroring | `run_agent.py` | Syncs completed turns into external memory providers | durable memory side-store | No, in current form |
| External-memory prefetch injection | `run_agent.py` | Prefetches external memory and injects it before tool loop | ambient recall | No |
| Semantic + graph recall backend with `recall.db` | `agent/memory_recall_backend.py` | Alternate local memory backend | recall memory | No |
| C4/C5 recall router and seeding logic | `agent/recall_router.py` | Routes recall to alternate backend and seeds from `~/.shay/memories` | recall memory | No |
| L1 episodic session memo taxonomy | `agent/session_memo.py` | Labels session memos with `memory_layer: L1` and `memory/l1` tags | archive / shared-vault | No, terminology conflict |
| T0/T1/T2/T3 memory hierarchy | `packages/memory/src/types.ts` | Defines separate memory tier taxonomy | unrelated package memory model | No |
| JSONL semantic memory store | `packages/memory/src/store.ts` | Stores memory records with optional persistence and semantic recall | recall memory | No |
| `getTier0()` always-in-context surface | `packages/memory/src/store.ts` | Exposes ambient memory records | ambient recall semantics | No |
| Markdown vault bridge with `~/basic-memory` default | `packages/memory/src/basic-memory-bridge.ts` | Reads markdown files and maps them into T-tier records | shared-vault duplicate | No |
| `MemoryRecord` schema with T tiers | `schemas/memory-record.schema.json` | Formalizes package memory vocabulary | unrelated package memory model | No |
| Doctor memory integrity check | `packages/doctor/src/checks/memory-check.ts` | Writes synthetic record and validates T-tier semantics | memory diagnostic side-effect | No |
| Brain request context items | `packages/brain/src/router.ts`, `schemas/brain-request.schema.json` | Generic context routing, budgeting, lane hints | unrelated | Yes / neutral |
| Insights over SessionDB | `agent/insights.py` | Reads historical data for analytics | unrelated | Yes |
| Curator scheduler state | `agent/curator.py` | `.curator_state` bookkeeping | unrelated | Yes |

## Conflicts and Ambiguities

### Direct conflicts

1. Alternate canonical-seeming recall backend
   - `agent/memory_recall_backend.py`
   - introduces `~/.shay/memory/recall.db`
   - introduces `L0/L1/L2/L3`
   - creates a parallel recall store outside `state.db` and outside the shared MCP vault path

2. Alternate recall router and seed corpus misuse
   - `agent/recall_router.py`
   - seeds C4 recall from `~/.shay/memories`
   - treats bounded prompt memory as seed corpus for a separate recall plane
   - that is a doctrine mismatch

3. Competing TypeScript memory taxonomy
   - `packages/memory/src/types.ts`
   - `packages/memory/src/store.ts`
   - `schemas/memory-record.schema.json`
   - introduces T0/T1/T2/T3 as a general memory hierarchy

4. Shared-vault duplication
   - `packages/memory/src/basic-memory-bridge.ts`
   - recursively reads markdown files directly from `~/basic-memory`
   - bypasses the canonical shared-vault MCP interfaces and uses a non-canonical default path

5. Ambient retrieval behavior
   - `run_agent.py:12025-12035`
   - external memory prefetch happens automatically before the tool loop
   - that is ambient retrieval, not explicit tool-based retrieval

6. Durable side-store writes outside doctrine
   - `run_agent.py:5518-5556`
   - syncs completed turns into external memory providers and queues prefetch automatically
   - creates durable memory behavior outside `MEMORY.md` / `USER.md` and outside canonical conversation recall doctrine

7. Session JSON fallback still alive in a way that can outrank DB results
   - `gateway/session.py:1337-1356`
   - returns JSONL when it has more messages than SQLite
   - operationally understandable, doctrinally dangerous if left permanent

8. Mutating doctor memory check
   - `packages/doctor/src/checks/memory-check.ts:32-54`
   - health check writes a synthetic memory record
   - a doctor check should not create memory artifacts in an ambiguous store

### Near-conflicts / unresolved areas

1. Session memo persistence is directionally reasonable but vocabulary-hostile
   - `agent/session_memo.py`
   - stores in the shared vault, which is the right family
   - but uses `L1`, `memory/l1`, and “episodic” taxonomy not present in canonical docs
   - also creates a durable session-memory layer outside `state.db`, so policy needs to explicitly bless that pattern before it becomes normal runtime truth

2. Context compressor is safe except for the memo write path
   - `agent/context_compressor.py`
   - the compression summary itself is aligned
   - the persistence target it calls is not fully aligned yet

3. `gateway/session.py` comments and doctrine say one thing while runtime compatibility still does another
   - comments say `state.db` is canonical
   - fallback path still lets JSONL win when longer
   - that is a temporary seam, not a stable doctrine-compatible endpoint

### Explicit answers to the requested doctrine checks

- Does anything make JSON sessions canonical again?
  - Not explicitly in docs/comments.
  - Functionally, `gateway/session.py:1337-1356` still lets JSONL outrank DB data for transcript loading in some cases.

- Does anything bypass `state.db` as conversation recall?
  - Yes, `gateway/session.py` can load transcript history from JSONL when DB is shorter or unavailable.
  - `tools/session_search_tool.py` itself remains aligned with SessionDB.

- Does anything auto-load `~/.shay/private/`?
  - No active auto-load path was found in the reviewed runtime slice.

- Does anything treat `shay.db` as active/canonical?
  - No.

- Does anything introduce a competing memory tier taxonomy?
  - Yes, three times:
    - `agent/session_memo.py` with `L1`
    - `agent/memory_recall_backend.py` / `agent/recall_router.py` with `L0-L3` and `C4/C5`
    - `packages/memory/**` and `schemas/memory-record.schema.json` with `T0-T3`

- Does anything write durable user/system memory outside `MEMORY.md` / `USER.md` without clear policy?
  - Yes:
    - `agent/session_memo.py`
    - `run_agent.py` external memory-provider sync path
    - `packages/memory/src/store.ts` if used persistently

- Does anything duplicate Obsidian/vault behavior?
  - Yes:
    - `packages/memory/src/basic-memory-bridge.ts`
    - direct vault-writing in `agent/session_memo.py` also bypasses MCP-mediated mental model, even if it lands in the shared vault family

- Does anything make memory retrieval ambient instead of opt-in/tool-based?
  - Yes:
    - `run_agent.py` external memory prefetch injection
    - `packages/memory/src/store.ts` + `getTier0()` encode an ambient-memory design

## Component-by-Component Verdict

### Python memory/runtime

#### `agent/prompt_builder.py`
- Verdict: preserve as-is
- Why:
  - correctly treats identity files and bounded prompt memory as active runtime context
  - correctly pushes past-conversation recall toward `session_search`
- Exact risk:
  - low
- What must change later:
  - nothing memory-doctrinally urgent

#### `agent/memory_recall_backend.py`
- Verdict: quarantine for later
- Why:
  - introduces alternate `recall.db`
  - introduces foreign tier language (`L0-L3`)
  - creates a separate semantic/graph memory plane with no canonical adoption plan
- Exact risk:
  - future Shay ends up with two “real” recall systems and no authoritative mental model
- What must change later:
  - redesign against canonical hierarchy, canonical names, and explicit integration boundaries before any runtime adoption

#### `agent/recall_router.py`
- Verdict: quarantine for later
- Why:
  - routes recall to the alternate backend
  - seeds from `~/.shay/memories`, which are supposed to be bounded prompt memory, not generic recall corpus
  - adds `C4/C5` doctrine drift
- Exact risk:
  - prompt memory gets silently repurposed into a hidden recall index
- What must change later:
  - redefine inputs, naming, and activation model against canonical doctrine; do not let `MEMORY.md` / `USER.md` become bulk seed corpus by default

#### `agent/session_memo.py`
- Verdict: rewrite against canonical hierarchy
- Why:
  - the destination family is plausible (shared vault)
  - the current terminology is not
  - it creates a durable session-memory pattern that needs explicit doctrine language before it becomes normal
- Exact risk:
  - people start treating L1 episodic memos as an unofficial canonical memory layer
- What must change later:
  - rename terminology to canonical language
  - explicitly document whether session memos are shared-vault knowledge artifacts, archive artifacts, or a sanctioned derivative of compaction summaries
  - ensure they do not compete with `state.db` as conversation truth

#### `agent/context_compressor.py`
- Verdict: preserve with rename/terminology alignment
- Why:
  - compression and handoff summaries are aligned
  - the only risky piece is the session-memo persistence seam
- Exact risk:
  - low if the persistence seam is gated; medium if memo persistence is treated as settled doctrine
- What must change later:
  - keep compression
  - detach or rewrite the memo persistence terminology/path

#### `agent/curator.py`
- Verdict: preserve as-is
- Why:
  - not a competing memory surface
- Exact risk:
  - negligible
- What must change later:
  - nothing for memory doctrine

#### `agent/insights.py`
- Verdict: preserve as-is
- Why:
  - uses canonical session data for analytics, not alternate memory doctrine
- Exact risk:
  - low
- What must change later:
  - nothing memory-specific

#### `tools/session_search_tool.py`
- Verdict: preserve as-is
- Why:
  - explicit, tool-based recall from SessionDB
  - aligned with `state.db` canonical conversation recall
- Exact risk:
  - low
- What must change later:
  - nothing doctrinally urgent

#### `gateway/session.py`
- Verdict: rewrite against canonical hierarchy
- Why:
  - comments are doctrine-aligned
  - runtime compatibility path still lets JSONL outrank DB transcript data
- Exact risk:
  - operators keep treating JSON artifacts as quasi-canonical because runtime still sometimes does
- What must change later:
  - preserve compatibility seams if needed
  - but stop JSONL from winning as a normal transcript source once migration is complete
  - document any remaining JSON dependency as compatibility-only

#### `run_agent.py`
- Verdict: preserve but gate behind config
- Why:
  - built-in prompt memory pieces are aligned
  - external memory-provider sync/prefetch path is not
- Exact risk:
  - ambient retrieval and silent durable side-stores blur the doctrine immediately
- What must change later:
  - keep MEMORY.md/USER.md flow
  - keep SessionDB/session_search flow
  - hard-gate or redesign external memory-provider behavior so it cannot behave like hidden canonical memory

### TypeScript memory/platform

#### `packages/memory/src/types.ts`
- Verdict: discard
- Why:
  - defines a competing top-level memory taxonomy (`T0-T3`) as if it were the Shay memory fabric
- Exact risk:
  - conceptual takeover by schema instead of doctrine
- What must change later:
  - if any ideas survive, remap them into canonical language rather than preserving the taxonomy

#### `packages/memory/src/store.ts`
- Verdict: quarantine for later
- Why:
  - semantic recall logic may be reusable
  - current persistence and tier model are not doctrine-aligned
- Exact risk:
  - JSONL side-store + ambient `T0` semantics create a second memory system
- What must change later:
  - strip taxonomy
  - strip implicit persistence assumptions
  - rebuild only if there is a clear package-level role that does not compete with Python runtime canon

#### `packages/memory/src/basic-memory-bridge.ts`
- Verdict: discard
- Why:
  - duplicates shared-vault retrieval with a parallel filesystem adapter
  - uses non-canonical default path `~/basic-memory`
- Exact risk:
  - bypasses the MCP-based shared-vault mental model and multiplies sources of truth
- What must change later:
  - none; if shared-vault access is needed, use the canonical MCP path instead

#### `packages/brain/**`
- Verdict: preserve as-is
- Why:
  - reviewed pieces are generic context plumbing, not memory-doctrine code
- Exact risk:
  - low
- What must change later:
  - nothing unless memory semantics are later added here

#### `packages/doctor/src/checks/memory-check.ts`
- Verdict: discard
- Why:
  - mutates the memory store during a health check
  - validates the wrong taxonomy
- Exact risk:
  - diagnostics create artifacts and normalize the wrong memory model
- What must change later:
  - if a doctor check is ever rebuilt, it must be non-mutating and doctrine-aware

#### `schemas/memory-record.schema.json`
- Verdict: discard
- Why:
  - formalizes the competing T-tier doctrine in schema form
- Exact risk:
  - schema starts masquerading as canonical memory design
- What must change later:
  - replace only if a schema is later needed for a canonically defined, non-competing subsystem

#### `schemas/brain-request.schema.json`
- Verdict: preserve as-is
- Why:
  - generic context packaging only
- Exact risk:
  - low
- What must change later:
  - nothing memory-specific

## Required Terminology Alignment

### Names that should survive
- Identity / operating voice
- bounded prompt memory
- project/repo context
- conversation recall
- shared knowledge vault
- private memory vault
- legacy/auxiliary artifacts
- `state.db` as canonical conversation recall
- `MEMORY.md` / `USER.md` as bounded prompt memory

### Names that should be renamed or retired
- `L0/L1/L2/L3`
  - retire as runtime-facing doctrine language
- `C4/C5`
  - retire as runtime-facing doctrine language
  - acceptable only as internal experiment labels in research notes, not production architecture names
- `T0/T1/T2/T3`
  - retire entirely from Shay memory/runtime naming
- `memory fabric`
  - too broad and competes with the actual doctrine
- `always-in-context` as a free-floating tier concept
  - if something is auto-injected, it should map to canonical prompt/identity/repo context layers directly
- `episodic` as a canonical layer name
  - acceptable in prose if clearly subordinate to the canonical hierarchy, but not as a replacement taxonomy

## Safe Salvage Candidates

Low-risk memory-related code worth extracting later:

1. `agent/prompt_builder.py`
   - identity loading
   - memory guidance
   - session_search guidance

2. `tools/session_search_tool.py`
   - explicit SessionDB-backed recall

3. `run_agent.py`
   - built-in `MEMORY.md` / `USER.md` prompt-memory path only
   - not the external memory-provider path

4. `agent/context_compressor.py`
   - summary/handoff generation and compression behavior
   - provided the session-memo persistence seam is detached or rewritten

5. `agent/insights.py`
   - SessionDB analytics, if useful

6. `packages/brain/**`
   - generic context routing/budgeting only

7. `schemas/brain-request.schema.json`
   - generic request packaging only

## Quarantine Candidates

These should not be merged into the future Shay runtime until redesigned:

1. `agent/memory_recall_backend.py`
2. `agent/recall_router.py`
3. external memory-provider sync/prefetch behavior in `run_agent.py`
4. `agent/session_memo.py` in its current vocabulary/form
5. session-memo persistence seam in `agent/context_compressor.py` until terminology and policy are aligned
6. JSONL-winning compatibility behavior in `gateway/session.py`
7. `packages/memory/**`
8. `schemas/memory-record.schema.json`
9. `packages/doctor/src/checks/memory-check.ts`

## Recommended Next Step

3. quarantine all new memory runtime work and continue with non-memory platform slices

Reason:
- the branch contains good platform work outside memory
- the memory/runtime slice is too ambiguous to merge safely
- a broad memory rewrite right now would mix implementation and doctrine cleanup in one move
- safer sequence: isolate the bad memory slice, keep moving on non-memory platform value, then do a dedicated memory-runtime alignment pass with one vocabulary and one authority model

## Exact Next Prompt

Use this exact next prompt after reviewing this report:

`Quarantine the doctrine-conflicting memory/runtime work from shay-platform-build and prepare a read-only extraction plan. Do not modify code yet. In /Users/famtasticfritz/famtastic/shay-shay-build on branch shay-platform-build, identify the exact commits, files, and code ranges that belong to: (1) safe salvage memory pieces, (2) quarantine-only memory pieces, and (3) non-memory platform slices that can continue independently. Source of truth remains docs/shay-memory-hierarchy.md, docs/shay-private-memory-policy.md, docs/shay-session-artifact-policy.md, docs/shay-db-status.md, and docs/platform-memory-runtime-adversarial-review-2026-06-12.md. Produce one report only: docs/platform-memory-quarantine-extraction-plan-2026-06-12.md. Include commit/file mapping, proposed extraction order, dependencies, and exact “do not carry forward” items. Read-only only.`

## Files inspected

Source-of-truth docs:
- `docs/shay-memory-hierarchy.md`
- `docs/shay-memory-compaction-policy.md`
- `docs/shay-private-memory-policy.md`
- `docs/shay-session-artifact-policy.md`
- `docs/shay-db-status.md`
- `docs/platform-memory-persistence-audit-2026-06-12.md`

Python runtime:
- `agent/prompt_builder.py`
- `agent/memory_recall_backend.py`
- `agent/recall_router.py`
- `agent/session_memo.py`
- `agent/context_compressor.py`
- `agent/curator.py`
- `agent/insights.py`
- `tools/session_search_tool.py`
- `gateway/session.py`
- `run_agent.py`
- supporting evidence from `agent/memory_manager.py` via `run_agent.py` references

TypeScript / schemas:
- `packages/memory/src/types.ts`
- `packages/memory/src/store.ts`
- `packages/memory/src/basic-memory-bridge.ts`
- `packages/brain/src/router.ts`
- `packages/brain/src/context-budget.ts`
- `packages/doctor/src/checks/memory-check.ts`
- `schemas/memory-record.schema.json`
- `schemas/brain-request.schema.json`
- `schemas/config.schema.json`

## Bottom-line classification summary

### Preserve list
- `agent/prompt_builder.py`
- `tools/session_search_tool.py`
- built-in `MEMORY.md` / `USER.md` path in `run_agent.py`
- compression/handoff logic in `agent/context_compressor.py` minus unresolved memo seam
- `agent/insights.py`
- `agent/curator.py`
- `packages/brain/**`
- `schemas/brain-request.schema.json`

### Rewrite list
- `agent/session_memo.py`
- session-memo persistence seam in `agent/context_compressor.py`
- `gateway/session.py`
- external memory-provider behavior in `run_agent.py` if it is to survive at all

### Quarantine list
- `agent/memory_recall_backend.py`
- `agent/recall_router.py`
- `packages/memory/src/store.ts`
- external memory-provider sync/prefetch path in `run_agent.py`
- JSONL-winning transcript path in `gateway/session.py` until reclassified/fixed

### Discard list
- `packages/memory/src/types.ts`
- `packages/memory/src/basic-memory-bridge.ts`
- `schemas/memory-record.schema.json`
- `packages/doctor/src/checks/memory-check.ts`

### High-level verdict
- risky

### Next prompt
- see “Exact Next Prompt” above
