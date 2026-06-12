# Platform memory persistence audit — 2026-06-12

## Scope

Read-only audit of `shay-platform-build` against `origin/main`, focused on:

1. branch / PR state
2. canonical memory doctrine docs
3. runtime alignment with that doctrine
4. classification of in-flight Claude Code platform work before any cutover

No code changes were made during the audit. This report is the only new file.

## Executive read

Bottom line: the canonical memory doctrine is already on `main`, and the branch carries it unchanged. The branch also contains some good runtime/platform work worth preserving, but it mixes that with experimental memory implementations that do **not** match the canonical doctrine yet. So the right move is **not** "merge the whole branch." The right move is: preserve the proven pieces, review the experimental memory pieces, and quarantine the speculative platform rewrite until it has a clean adoption plan.

## 1) Branch / PR state

Repository state at audit time:

- branch: `shay-platform-build`
- working tree: clean
- branch HEAD: `e684c05`
- `origin/main`: `56bd6c8`
- ahead/behind vs `origin/main`: `0 behind / 61 ahead`
- `origin/main` is an ancestor of `shay-platform-build`: yes
- PR: `#1` — `Broad Shay platform/runtime build`
- PR state: open draft
- merge state: `UNSTABLE`
- URL: `https://github.com/famtastic-fritz/shay-shay/pull/1`

Interpretation:

- This is a forward branch, not a diverged one.
- Nothing on the branch is blocked by upstream drift right now.
- The risk is not merge-conflict drift. The risk is scope contamination: too many unrelated platform experiments bundled together.

## 2) Canonical memory docs parity with `origin/main`

Verified identical between `shay-platform-build` and `origin/main`:

- `docs/shay-memory-hierarchy.md`
- `docs/shay-memory-compaction-policy.md`
- `docs/shay-private-memory-policy.md`
- `docs/shay-session-artifact-policy.md`
- `docs/shay-db-status.md`

Hash parity at audit time:

- `docs/shay-memory-hierarchy.md` — `3795826a2813`
- `docs/shay-memory-compaction-policy.md` — `fabf197e5aa3`
- `docs/shay-private-memory-policy.md` — `7b1769005dda`
- `docs/shay-session-artifact-policy.md` — `4bba3b01792a`
- `docs/shay-db-status.md` — `7c5170c4150b`

Interpretation:

- The doctrine is already established on `main`.
- The branch does **not** introduce a competing canonical doc set.
- Any conflict now is runtime/design drift, not documentation drift between branch and main.

## 3) Canonical doctrine distilled

From the canonical docs now shared by both branch and main:

- `SOUL.md` + `PERSONA.md` are runtime identity files.
- `~/.shay/memories/MEMORY.md` and `~/.shay/memories/USER.md` are bounded prompt memory, not a giant general memory lake.
- `~/.shay/private/` exists, but it is deliberately isolated and not part of normal shared retrieval.
- `~/.shay/state.db` is the canonical session/message/tool-call history store.
- `~/.shay/sessions/*.jsonl` and `sessions.json` are auxiliary session artifacts / bookkeeping, not the canonical history source.
- `~/.shay/shay.db` is not a canonical live runtime dependency.
- Shared long-horizon knowledge belongs in the Obsidian/basic-memory layer, not in ad hoc parallel stores.

That is the doctrine the runtime should obey.

## 4) Runtime alignment: what matches the doctrine

### 4.1 Identity loading is aligned

`agent/prompt_builder.py` explicitly loads:

- `SOUL.md` from `SHAY_HOME`
- `PERSONA.md` from `SHAY_HOME`

This matches the doctrine and the Shay identity model.

Relevant runtime evidence:

- `agent/prompt_builder.py:1411-1468`

### 4.2 Prompt memory model is aligned

`run_agent.py` still treats persistent prompt memory as disk-backed `MEMORY.md + USER.md`, with `USER.md` explicitly injected when enabled.

Relevant runtime evidence:

- `run_agent.py:1911-1913`
- `run_agent.py:5911-5915`

This matches the canonical memory doctrine.

### 4.3 No automatic private-memory bleed detected

Search across runtime code found no active code path automatically ingesting `~/.shay/private/` or a parallel "private vault" into normal recall.

That is aligned with the private-memory doctrine.

### 4.4 `state.db` remains the real canonical session/history store

Runtime references for live session persistence, maintenance, gateway/session handling, and CLI behavior all still point at `state.db`.

Relevant runtime surfaces include:

- `shay_state.py`
- `gateway/session.py`
- `gateway/platforms/api_server.py`
- `acp_adapter/session.py`
- `cli.py`
- `shay_cli/config.py`

This matches the canonical doctrine that `state.db` is the truth source.

### 4.5 Session artifact treatment is mostly aligned

The runtime still writes session artifacts like `sessions.json`, `*.jsonl`, and request dumps, but code/comments treat them as bookkeeping, mirror, export, or cleanup targets rather than the authoritative canonical history store.

This is consistent with the doctrine as long as nobody re-promotes them to source-of-truth status.

### 4.6 Session memo persistence is directionally aligned

`agent/session_memo.py` writes session memos into the shared Obsidian vault under:

`~/famtastic/obsidian/Shay-Memory/reflections/episodic/sessions/<session_id>.md`

And `agent/context_compressor.py` persists that memo on session end using already-generated handoff summaries.

Relevant runtime evidence:

- `agent/session_memo.py:1-190`
- `agent/context_compressor.py:404-435`

Interpretation:

- This is not a random new hidden DB.
- It writes into the shared knowledge layer, which is the right family of place.
- But the exact L1/L0-L3 terminology here does **not** match the canonical docs' naming, so this needs review before adoption as doctrine-backed runtime behavior.

## 5) Runtime conflicts / doctrine drift

This is where the branch gets messy.

### 5.1 `agent/memory_recall_backend.py` + `agent/recall_router.py` introduce an alternate memory architecture

`agent/recall_router.py` describes a flag-gated C4/C5 recall system and seeds the alternate backend from:

- `~/.shay/memories`

Relevant runtime evidence:

- `agent/recall_router.py:1-120`

Problem:

- The canonical docs say `MEMORY.md` / `USER.md` are bounded prompt memory files.
- The recall router treats that same directory as a seed corpus for a separate semantic/graph recall plane.
- That is a real architecture choice, but it is **not** described as canonical doctrine in the docs.
- Worse, the router uses labels like `C4`, `C5`, `L1`, and `project="vault"` that are foreign to the shipped canonical docs.

My read:

- This is promising experimental work.
- It is not yet doctrine-aligned enough to cut over blindly.
- Keep it out of a broad merge until the doctrine and runtime model are reconciled in one language.

### 5.2 The TypeScript `@shay/memory` package is a separate memory philosophy

`packages/memory/src/store.ts` defines a `MemoryStore` with:

- semantic recall via embeddings
- optional persistence to JSONL
- default persistence path in temp space
- four tiers `T0/T1/T2/T3`

Relevant runtime evidence:

- `packages/memory/src/store.ts:1-145`
- `schemas/memory-record.schema.json:1-68`
- `packages/doctor/src/checks/memory-check.ts:1-130`

Problem:

- This is a second memory system with a second tier vocabulary.
- It defaults to `tmpdir()` persistence, which is absolutely not canonical Shay memory persistence.
- It is not wired into the Python runtime as the live truth source, but it creates conceptual drift and future merge risk.

My read:

- Good seed work for a future package ecosystem.
- Not production-cutover-ready.
- Needs quarantine until there is a clean migration/adoption plan.

### 5.3 `shay.db` remains non-canonical, which is good — but audits/specs around it should stay documentary only

Code search found `shay.db` references mainly in audit scripts and documentation, not in the live runtime path.

That is good.

Risk:

- Do not let documentary investigation around `shay.db` creep into runtime assumptions. Keep it as audit/spec material unless a deliberate architecture decision promotes it.

### 5.4 Naming drift is the real enemy here

The branch currently contains multiple overlapping vocabularies:

- canonical docs vocabulary
- `L0/L1/L2/L3` session memo vocabulary
- `C4/C5` recall-router vocabulary
- `T0/T1/T2/T3` TypeScript package vocabulary

That is exactly how platform memory goes sideways.

The technical issue is not just code; it is competing doctrine languages inside one repo.

## 6) Preserve / review / quarantine classification

This is the important cutover section.

### Preserve

These are worth keeping and are either already aligned or low-risk/high-value:

1. Canonical memory doctrine docs
   - all `docs/shay-*memory*` / policy docs listed above
   - status: already on `main`; preserve as canon

2. PERSONA runtime loading
   - `agent/prompt_builder.py`
   - commit line: `feat(identity): load PERSONA.md as voice layer in system prompt`
   - reason: directly aligned with Shay identity doctrine

3. Session-search token cap fix
   - `fix(session-search): cap summary tokens`
   - reason: practical stabilization with no doctrine conflict seen in this audit

4. Non-memory platform hardening that is orthogonal to this cutover
   - selected kanban reliability work
   - model picker fixes
   - gateway/task route hardening
   - restart handoff safety
   - reason: these can be reviewed on their own merits and are not the memory doctrine problem

### Review before preserve

These have real value but need surgical review, not bulk merge:

1. Session memo persistence
   - `agent/session_memo.py`
   - `agent/context_compressor.py`
   - question: should episodic memos live in shared Obsidian exactly this way, and under this naming scheme?

2. Recall backend and router
   - `agent/memory_recall_backend.py`
   - `agent/recall_router.py`
   - question: is `~/.shay/memories` allowed to seed semantic recall, or must recall pull from state.db + Obsidian instead?

3. Memory-related docs that are reports/specs rather than canon
   - audit docs added on this branch
   - question: useful evidence, yes; canonical architecture, no

4. Build ledger / build tracker / coordinator work
   - probably useful platform work
   - but unrelated enough to memory cutover that it should not ride shotgun in a memory merge

5. Desk/web/dashboard/platform API additions
   - likely useful
   - but also unrelated enough that they should be split from the memory cutover decision

### Quarantine for now

These should not be part of a near-term memory persistence cutover:

1. TypeScript monorepo platform rewrite / `@shay/*` package ecosystem
   - `packages/*`
   - `schemas/*`
   - related TS config/package scaffolding
   - reason: substantial parallel platform architecture, not cutover-safe, not doctrine-harmonized

2. `@shay/memory` package and associated doctor/schema stack
   - separate memory model, separate persistence assumptions, separate tier language
   - reason: conceptually promising, operationally premature

3. Archive/WIP carryovers
   - `archive/wip-2026-06-01/*`
   - reason: by definition not cutover material

4. Broad umbrella merge from PR #1
   - reason: scope too mixed; guarantees avoidable confusion

## 7) Recommended cutover stance

Do this:

- treat `origin/main` as the doctrine base
- cherry-pick or manually re-implement only the memory/runtime pieces that survive doctrine review
- keep PR #1 draft
- split the branch into smaller adoption lanes

Do not do this:

- do not merge PR #1 wholesale
- do not adopt the TS memory package as if it were already Shay canon
- do not let four naming systems coexist in production memory logic

## 8) Exact next prompts

### Prompt A — surgical salvage plan from this branch

Use this when you want Claude Code or another worker to produce a cutover-safe salvage list.

```text
Audit shay-platform-build against origin/main and produce a surgical salvage plan for memory/runtime work only.

Rules:
- Read-only first.
- Do NOT recommend merging the whole branch.
- Treat origin/main as canonical for memory doctrine.
- Separate findings into: preserve now, review next, quarantine.
- Focus on these files first:
  - agent/prompt_builder.py
  - agent/context_compressor.py
  - agent/session_memo.py
  - agent/memory_recall_backend.py
  - agent/recall_router.py
  - run_agent.py
  - docs/shay-memory-hierarchy.md
  - docs/shay-memory-compaction-policy.md
  - docs/shay-private-memory-policy.md
  - docs/shay-session-artifact-policy.md
  - docs/shay-db-status.md
- Explicitly call out any naming/doctrine drift.
- End with a proposed sequence of cherry-picks or manual re-implementations.
```

### Prompt B — hard review of memory runtime conflicts

Use this when you want adversarial review on whether the experimental memory code should survive at all.

```text
Do an adversarial review of the memory runtime work on shay-platform-build.

Question to answer:
Does the branch's memory runtime actually align with the canonical Shay memory doctrine now documented on origin/main, or is it introducing a competing architecture?

Inspect at minimum:
- agent/session_memo.py
- agent/context_compressor.py
- agent/memory_recall_backend.py
- agent/recall_router.py
- run_agent.py
- packages/memory/src/store.ts
- schemas/memory-record.schema.json

Output format:
1. aligned
2. conflicts
3. hidden risks
4. what to keep
5. what to kill
6. exact smallest safe next step

Be ruthless. Prefer protecting doctrine clarity over preserving branch effort.
```

### Prompt C — split the branch into adoption lanes

Use this when you want the branch decomposed into independent follow-up branches/PRs.

```text
Break shay-platform-build into adoption lanes.

Goal:
Turn one mixed platform branch into a set of narrow branches or PR recommendations.

Required lanes:
- memory doctrine/runtime alignment
- identity/persona loading
- kanban reliability and completion watcher work
- build tracker / build ledger / coordinator work
- desk/web/dashboard/API work
- TypeScript @shay package ecosystem
- archive/WIP quarantine

For each lane provide:
- purpose
- risk level
- should preserve / review / quarantine
- suggested branch name
- suggested PR title
- whether it can merge independently of the memory cutover
```

## 9) Final call

The branch is not rotten. It is overloaded.

There is real value in it.
But for memory persistence cutover, broad merge is the wrong move.

Preserve the doctrine-aligned gains.
Review the promising memory experiments.
Quarantine the platform rewrite.
Split the branch before you let it touch production truth.
