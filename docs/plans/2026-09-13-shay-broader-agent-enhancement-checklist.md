# Shay Broader Agent Enhancement — Detailed Checklist Plan

Status: Phase 0 documentation; feature-branch implementation, verification, reviewed
commit, and push approved; implementation not yet proven; merge approval remains
separate and pending

Date: 2026-09-13

Repository: `/Users/famtastic-fritz/Development/FAMtastic/shay-shay`

Pinned planning baseline: `cf6bb95e3dc12e0d4b8eadef2c33be2b39ad21b6` on `main`

Owner constraint: preserve Shay's custom code, identity, workflows, and runtime state

## 1. Outcome

Strengthen Shay by borrowing bounded patterns from OpenHands, Letta, Goose, Aider,
and OpenCode while keeping Shay's existing architecture authoritative. The work is
complete only when durable task state, deterministic safety, memory provenance,
shared client semantics, and CLI improvements are proven end to end without
replacing Shay's custom behavior.

This plan corrects the earlier high-level roadmap in one important way: Shay already
has substantial implementations for these concerns. The work is therefore an audit,
reconciliation, and targeted hardening program—not a greenfield agent rewrite.

## 2. Scope boundary

Included:

- durable task/run/event lifecycle and restart recovery;
- deterministic permission, idempotency, retry, and spend controls;
- versioned memory provenance and owner-controlled promotion;
- consistent task/session/event semantics across CLI, TUI, gateway API, and ACP;
- truthful CLI status, inspection, recovery, and diagnostics;
- anti-drift traceability from research recommendation to plan, task, code, test,
  review, and release evidence.

Excluded:

- filming work;
- voice, STT/TTS, and spoken-persona implementation;
- edits to `PERSONA.md`, `SOUL.md`, private identity files, credentials, or live
  runtime configuration;
- autonomous payments, publishing, messaging, account changes, or production
  deployment;
- a native mobile-client build;
- wholesale adoption of another agent framework.

Historical clarification: the earlier filming review only surfaced the launcher
portability defect. The portability repair is already on `main`; filming is not an
input to this architecture program.

## 3. Current evidence and honest starting verdict

### Locally proven at the pinned baseline

- [x] `scripts/run_tests.sh` ran the focused guardrail, checkpoint, memory, TUI
  protocol, command, configuration-drift, budget-race, session-resume, and batch
  checkpoint set: **573 passed**.
- [x] The focused Kanban kernel set passed: **151 passed, 1 skipped**.
- [x] `tests/stress/test_concurrency.py` completed 100 tasks with 100 claims and 100
  completions; all invariants held.
- [x] The checkout remained clean on `main` at the pinned baseline.

### Reproduced defects

- [ ] `tests/stress/test_subprocess_e2e.py` fails before exercising the lifecycle:
  `NameError: name 'Path' is not defined` at line 20.
- [ ] Concurrent `create_task(...)` calls with the same idempotency key can create
  two task IDs because the index is non-unique and the pre-check is outside the
  write transaction.
- [ ] `tests/stress/test_atypical_scenarios.py` still refers to removed
  `Task.spawn_failures` instead of `consecutive_failures`.
- [ ] Archived-parent dependency semantics disagree between task creation and
  readiness/claim paths.

### Blocked or source-defined only

- [ ] The local `.venv` uses Python 3.14 and lacks the full `.[all,dev]` dependency
  set used by CI on Python 3.11; async API, FastAPI, ACP, and gateway recovery tests
  are not locally proven.
- [ ] `scripts/run_tests.sh` always excludes `tests/integration` and `tests/e2e`, so
  it cannot currently serve as the canonical local E2E gate.
- [ ] `/v1/runs` state and SSE queues are process-memory dictionaries and do not
  survive gateway restart.
- [ ] Memory provenance is partial: external provider hooks receive metadata, but
  built-in durable entries do not have a complete versioned provenance ledger.
- [ ] CLI, TUI, API, and ACP do not share one explicit versioned schema for task,
  run, session, event, approval, usage, and error envelopes.
- [ ] No hard dollar-denominated preflight/runtime spending cutoff is proven.

Starting verdict: **NO-GO for implementation claims until Phase 1 passes.**

Implementation authority is nevertheless recorded: on 2026-09-13 the user directed,
“Run all phases until complete and when its feasible run in parallel.” This authorizes
implementation, verification, reviewed feature-branch commits, and feature-branch
pushes for Phases 0–8 subject to their dependency and path gates. It does not
authorize merge to `main`, release, live enablement, credentials, destructive
actions, or production changes; every `merge_approval` remains null until a later
explicit owner decision.

## 4. What the external research contributes

Durable research record:
[shay-broader-agent-architecture-research-2026-09-13.md](/Users/famtastic-fritz/Development/FAMtastic/obsidian/Shay-Memory/research/shay-broader-agent-architecture-research-2026-09-13.md).
Generated planning-evidence record:
[shay-broader-agent-plan-evidence-2026-09-13.md](/Users/famtastic-fritz/Development/FAMtastic/obsidian/Shay-Memory/research/shay-broader-agent-plan-evidence-2026-09-13.md).
The reviewed snapshots are pinned, not floating repository claims:
[OpenHands `2846462`](https://github.com/OpenHands/OpenHands/commit/28464621d879e3e9b3ceeae9d70a71d96da6212d),
[Letta `5bcdd17`](https://github.com/letta-ai/letta/commit/5bcdd177d70fa2b31a754cfcd801e77b2e1ab16a),
[Letta MemFS docs `28970b3`](https://github.com/letta-ai/letta-docs-md/commit/28970b32a81e211105943d974d604b503dbe2845),
[Goose `50666ae`](https://github.com/aaif-goose/goose/commit/50666ae0b9a51e260b52b7efbab2e4e020346e94),
[Aider `5dc9490`](https://github.com/Aider-AI/aider/commit/5dc9490bb35f9729ef2c95d00a19ccd30c26339c), and
[OpenCode `631f67a`](https://github.com/anomalyco/opencode/commit/631f67a9f330e2e0b1c064db358e67133a053655).
The Phase 0 candidate copies both Obsidian records without modifying their originals and
contains canonical content-bearing snapshots for every exact pinned source path below,
including repository URL, commit, path, Git blob OID, content SHA-256, and base64 bytes.
Its strict research manifest binds those immutable candidate-local artifacts; later review
does not trust a floating URL, mutable checkout, or mutable Obsidian file.
A successor candidate reuses only the currently selected candidate's strictly revalidated,
mode-`0400` immutable snapshot bytes. A first uncached capture may fetch the exact pinned
commits with a hard 90-second subprocess timeout; timeout or drift fails before any selection
journal, candidate, invalidation, registry, or pointer mutation, and partial fetch data is disposable.

### Reproducible source observations

These are observations, not Shay design decisions. Reproduce each with
`git show <full-commit>:<path>` in the named repository, or open the commit URL and
that exact path. The full structured record, including verdict and relevance, is in
`docs/architecture/shay-custom-capability-contract.yaml`.

| Source | Exact pinned locations | Observation | Maintenance signal | Install/adoption status |
| --- | --- | --- | --- | --- |
| OpenHands `28464621d879e3e9b3ceeae9d70a71d96da6212d` | `docs/architecture.md`; `src/types/agent-server/core/openhands-event.ts`; `src/api/cloud/sandbox-service.api.ts` | UI, event, agent-server, and sandbox boundaries are separate. | Commit timestamp `2026-09-12T16:09:52Z`. | Source-reviewed only; not installed, vendored, or adopted. |
| Letta `5bcdd177d70fa2b31a754cfcd801e77b2e1ab16a` | `README.md` | The repository says active source moved to `letta-ai/letta-code` and V1 is archived. | Commit timestamp `2026-09-10T17:59:06Z`. | Context-only; not installed, vendored, or adopted. |
| Letta MemFS docs `28970b32a81e211105943d974d604b503dbe2845` | `concepts/memfs/index.md` | Memory is path-addressed Markdown with git history; vector search is optional. | Commit timestamp `2026-09-12T00:48:02Z`. | Documentation reviewed; MemFS/search mod not installed or adopted. |
| Goose `50666ae0b9a51e260b52b7efbab2e4e020346e94` | `crates/goose/src/agents/agent.rs`; `crates/goose/src/acp/server.rs`; `crates/goose-cli/src/cli.rs` | A common agent implementation is exposed through separate client adapters. | Commit timestamp `2026-09-11T20:42:56Z`. | Source-reviewed only; not installed, vendored, or adopted. |
| Aider `5dc9490bb35f9729ef2c95d00a19ccd30c26339c` | `aider/coders/architect_coder.py`; `aider/coders/ask_coder.py`; `aider/repomap.py` | Architect output is separated from editing and prompts before the editing handoff. | Commit timestamp `2026-05-22T14:02:20Z`; older than the other snapshots. | Source-reviewed only; not installed, vendored, or adopted. |
| OpenCode `631f67a9f330e2e0b1c064db358e67133a053655` | `packages/opencode/src/session/status.ts`; `packages/opencode/src/cli/cmd/stats.ts`; `packages/opencode/src/cli/cmd/providers.ts` | Status events and CLI provider/statistics surfaces are explicit. | Commit timestamp `2026-09-13T17:14:41Z`. | Source-reviewed only; not installed, vendored, or adopted. |

### Shay-specific interpretations and dispositions

| Source | Interpretation | Existing Shay owner | Verdict and relevance | Rejected adoption |
| --- | --- | --- | --- | --- |
| OpenHands | Durable event history and explicit execution isolation are useful boundaries. | `shay_cli/kanban_db.py`, `tools/process_registry.py`, gateway API | Bounded reference for R3; make Kanban authoritative for API-visible runs and replay. | Replacing Shay's runtime or adopting unsandboxed defaults. |
| Letta / MemFS | Git-backed provenance is useful around the actual split built-in/external memory paths. | `run_agent.py` `MemoryStore`; optional `MemoryManager` for a configured external provider | Bounded pattern for R5; preserve both authorities and add owner-reviewed promotion. | Replacing built-in memory or migrating identity automatically. |
| Goose | A shared core can keep distinct client transports. | command registry, TUI gateway, API adapter, ACP adapter | Bounded reference for R6; define one versioned domain contract. | Rewriting Shay's clients or core behavior wholesale. |
| Aider | Proposal/edit separation can make authority and actual changes clearer. | central commands, approvals, checkpoints | Ergonomics reference for R7. | Granting write authority merely because a mode was selected. |
| OpenCode | Explicit status/provider/usage surfaces can improve operator truth. | Shay CLI/TUI and provider plugins | Ergonomics reference for R7. | Replacing Shay's TUI or introducing a second chat surface. |
| NotebookLM synthesis | Reasoning/execution separation is a lead to test against primary sources. | plugin hooks, approvals, Kanban, config | Secondary interpretation only; never implementation evidence. | Treating notebook synthesis as authoritative or uploading private Shay source. |

## 5. Existing Shay contracts that must be preserved

- `shay_cli/commands.py:45-315`: `CommandDef`, `COMMAND_REGISTRY`, and
  `resolve_command(...)` remain the definition and alias authority for built-in
  CLI/gateway vocabulary. Plugin-registered commands, ACP-local slash commands,
  and documented TUI routing exceptions remain supported separate surfaces.
- `tools/registry.py:57-410`: built-in tool discovery and `ToolRegistry` remain the
  tool source of truth.
- `model_tools.py:304-810`: model-facing schemas and `handle_function_call(...)`
  remain the central dispatch path.
- `shay_cli/plugins.py:287-635,672-1338`: `PluginContext`, `PluginManager`, and
  lifecycle/tool hooks remain the preferred extension seam.
- `run_agent.py:1913-1933` and `tools/memory_tool.py` retain the separate built-in
  `MemoryStore` authority. `agent/memory_provider.py:42-237` and
  `agent/memory_manager.py:193-575` remain contracts only for a configured external
  provider in the current runtime path; `MemoryManager` does not contain the
  built-in store.
- `shay_cli/kanban_db.py:559-4820` remains the durable task/run/event kernel unless
  evidence proves a narrower owner is needed.
- `tools/approval.py:259-1055` remains the hardline/dangerous-command guard.
- `tools/checkpoint_manager.py:575-820` remains the filesystem rollback mechanism.
- `tui_gateway/server.py`, `tui_gateway/transport.py`, and
  `ui-tui/src/gatewayClient.ts` remain the real TUI transport.
- `shay_constants.py:14-184` remains the profile-aware path authority.
- The dashboard continues to embed the real `shay --tui`; no second React chat
  transcript or composer may be created.
- Prompt caching remains stable: no mid-session toolset, memory-prefix, or system
  prompt reconstruction.

## 6. Allowed APIs for the work

These APIs are source-confirmed and may be copied from their existing examples after
the relevant file is reread in the implementation session:

- `PluginContext.register_tool(...)`, `register_cli_command(...)`,
  `register_command(...)`, and `register_hook(...)` in
  `shay_cli/plugins.py:317-635`.
- `get_pre_tool_call_block_message(...)` in `shay_cli/plugins.py:1315-1332`, which
  accepts an `{"action": "block", "message": "..."}` result.
- `ToolRegistry.register(...)` and `dispatch(...)` in
  `tools/registry.py:234-410` when a core change is explicitly justified.
- `create_task(...)`, `claim_task(...)`, `heartbeat_claim(...)`,
  `release_stale_claims(...)`, `complete_task(...)`, `block_task(...)`, and
  `list_runs(...)` in `shay_cli/kanban_db.py`.
- `MemoryStore.add(...)`, `replace(...)`, and `remove(...)` in
  `tools/memory_tool.py`, independently of `MemoryProvider.on_memory_write(...)` and
  the optional external-provider `MemoryManager` lifecycle forwarding in
  `agent/memory_provider.py` and `agent/memory_manager.py`.
- `CommandDef` plus the derived CLI/gateway/help/autocomplete consumers in
  `shay_cli/commands.py`.
- TUI `method(name)` registration and `Transport` implementations in
  `tui_gateway/server.py:434` and `tui_gateway/transport.py:67-219`.
- `get_shay_home()`, `display_shay_home()`, and `get_subprocess_home()` in
  `shay_constants.py`.

Do not invent or claim the following as current APIs:

- a working generic `smart_model_routing` engine;
- automatic workflow-template v2 routing merely because reserved columns exist;
- durable/replayable `/v1/runs` state;
- a shared client protocol version;
- a hard USD spending-authority boundary;
- a native Shay iOS or Android client.

## 7. Anti-drift operating stack

### Installed skills and plugin support

- [x] Use `claude-mem:make-plan` for documentation-first phased planning and the
  mandatory source/findings/snippets/confidence subagent contract.
- [x] Use `claude-mem:mem-search` before each phase with the required
  search → timeline → selected-observation fetch sequence. Its MCP tools were
  confirmed callable during this planning run.
- [ ] Use `claude-mem:pathfinder` only for line-labelled current-state discovery.
  Do not apply its delete-first or remove-feature-flags preferences where they
  conflict with Fritz's preservation and rollback requirements.
- [x] Use `claude-mem:do` now that implementation is approved. Each
  phase must have separate implementation, verification, anti-pattern, quality,
  and branch/sync responsibility.
- [ ] Use Shay's built-in `test-driven-development`, `writing-plans`,
  `requesting-code-review`, `github-pr-workflow`, and `github-code-review` skills
  as the phase requires.
- [ ] Use `claude-mem:babysit` only after the owner separately authorizes and a PR
  exists, continuing until CI, review threads, and mergeability are honestly clean.
- [x] Use the FAMtastic end-to-end skill's evidence discipline: exit zero, required
  pass markers, machine-readable evidence, and every assertion true. Its commerce
  customer runner is not applicable to Shay core and must not be run as fake proof.
- [x] Use the connected GitHub app for read-only repository, commit, diff, check,
  artifact, and review-thread verification. Although the app currently has broad
  permissions, keep the connector read-only. The separate implementation directive
  authorizes reviewed feature-branch commits and pushes only; it does not authorize
  GitHub merge, release, live enablement, or other repository mutation.
- [x] Use the Plugin Management app to inspect dependency and permission impact
  before enabling any additional external plugin.

### ECC decision

- [x] ECC is **not installed**.
- [x] A prior source-backed evaluation found direct collisions with FAMtastic's
  SessionStart, PreCompact, PostToolUse, and Stop hooks.
- [x] Do not install `ecc@ecc` globally or make it a prerequisite.
- [ ] If ECC is reconsidered, inspect it in a throwaway Codex home/worktree, record
  every hook/settings change, compare duplicate skills, and adopt individual
  patterns only after owner approval.

### Required trace and phase-evidence schema

The canonical repository ledger is an immutable pre-review event stream, not one
mutable row per requirement. Its first forty physical rows are now a frozen prefix
with full SHA-256
`cdd456f0deddf68134554c8acfbb4116a98b6cf68cea941b4d14b1bcacbe0c1f`.
Within it, the first twenty-nine rows are the exact archived-attempt prefix with SHA-256
`4cfe0dcfc84051f3f02fa721e0b87fbbb19c859442f816cd8741f5ffbaeffa9f`.
Rows 1-19 are the exact `drive-documents-v1` prefix with SHA-256
`53f6e9f7ef1984a36d9c2ec21a253b083eb2a2109661573fe16464483d8e0b39`:
nine proposal events, the original R0 `implementation_started`, and nine original
`program_board_linked` events. Row 20 truthfully records why v1 was blocked. Rows
21-29 truthfully record the `local-state-v2` board relinks, including the wrong
`:0` through `:8` task keys that make that setup invalid. All 29 rows are preserved
byte-for-byte and validate only as the full pinned historical prefix defined by the
capability contract; no semantic approximation or loose legacy exception is allowed.
Rows 30-40 preserve the completed v3 setup sequence: R0 E0006, R0 E0007, all
R1-R8 E0004 relinks, and R0 E0008. E0008 is retained but not an active verification
PASS because its three `started_at` and `ended_at` values were copied from
`recorded_at`, not measured around execution. Every row after the frozen 40-row
prefix explicitly carries `contract_revision=non-synced-v3`,
`setup_attempt_id=local-state-v3`, and `timing_status`.
R1-R8 each own one exact pre-review
phase-local evidence JSONL path declared by `phase_local_evidence_contract.path_map`
in the capability contract. Every line in either repository stream has this schema;
the separately described external execution ledger has its own strict closed schema:

```json
{
  "contract_revision": "non-synced-v3",
  "setup_attempt_id": "local-state-v3",
  "event_id": "SHAY-AGENT-R1:E0007",
  "requirement_id": "SHAY-AGENT-R1",
  "event_revision": 7,
  "prior_event_id": "SHAY-AGENT-R1:E0006",
  "event_type": "implementation_started",
  "recorded_at": "<actual-RFC3339-append-time>",
  "timing_status": "not_applicable",
  "status": "in_progress",
  "implementation_approval": {
    "status": "approved",
    "approved_on": "2026-09-13",
    "source_type": "user_message",
    "source": "Run all phases until complete and when its feasible run in parallel",
    "scope": "Implement, verify, commit, and push reviewed feature branches for SHAY-AGENT-R0 through SHAY-AGENT-R8 subject to dependency and path gates"
  },
  "merge_approval": null,
  "research_source": {
    "source_ids": ["OPENHANDS-2846462"],
    "artifact": "/Users/famtastic-fritz/Development/FAMtastic/obsidian/Shay-Memory/research/shay-broader-agent-plan-evidence-2026-09-13.md",
    "observation": "Pinned source exposes distinct event and execution boundaries",
    "interpretation": "Retain Kanban and add a durable adapter"
  },
  "recommendation_ref": {
    "status": "recorded",
    "recommendation_id": "SHAY-REC-R1-BASELINE-E2E",
    "source_ids": ["OPENHANDS-2846462"]
  },
  "plan_ref": {
    "status": "recorded",
    "path": "docs/plans/2026-09-13-shay-broader-agent-enhancement-checklist.md",
    "section": "Phase 1"
  },
  "kanban_ref": {
    "status": "in_progress",
    "program_id": "SHAY-AGENT-ENHANCEMENT-2026-09-13",
    "root": "/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3",
    "board": "shay-agent-enhancement-2026-09-13",
    "database": "/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/kanban/boards/shay-agent-enhancement-2026-09-13/kanban.db",
    "task_id": "t_b9500d49",
    "idempotency_key": "SHAY-AGENT-ENHANCEMENT-2026-09-13:R1",
    "task_status": "ready"
  },
  "dependency_refs": {
    "primary": {
      "requirement_id": "SHAY-AGENT-R0",
      "status": "pending_reviewed_commit",
      "reviewed_commit": null
    },
    "integrated": [],
    "review_gates": []
  },
  "existing_owner": "shay_cli/kanban_db.py",
  "planned_target": "baseline and explicit E2E gate",
  "branch": "codex/shay-agent-phase1-baseline-e2e",
  "worktree": "/Users/famtastic-fritz/Development/FAMtastic/worktrees/shay-agent-phase1-baseline-e2e",
  "planning_anchor_sha": "cf6bb95e3dc12e0d4b8eadef2c33be2b39ad21b6",
  "implementation_base_sha": null,
  "integration_base_sha": null,
  "phase_evidence_path": "docs/architecture/evidence/shay-agent-r1-events.jsonl",
  "allowed_paths": [],
  "forbidden_paths": ["phase-specific narrower path examples"],
  "all_unlisted_paths_forbidden": true,
  "tests": [],
  "changed_paths": {"status": "not_started", "paths": []},
  "test_results": {"status": "not_run", "results": []},
  "review_results": {"status": "not_reviewed", "results": []},
  "verification_refs": {"status": "not_run", "events": []},
  "review_refs": {
    "status": "not_requested",
    "verification": null,
    "anti_pattern": null,
    "quality": null
  },
  "commit_ref": null,
  "release_ref": {
    "status": "not_requested",
    "feature_branch_push": null,
    "pull_request": null,
    "merge": null,
    "live_enablement": null
  },
  "finalization_ref": null,
  "evidence": [{
    "kind": "board",
    "status": "observed",
    "path": "/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/kanban/boards/shay-agent-enhancement-2026-09-13/kanban.db",
    "sha256": null,
    "assertion": "The active v3 program task was resolved after fresh setup",
    "observation": "The new task ID, exact :R1 key, and exact v3 dependency link were read back"
  }],
  "protected_custom_manifest_id": "SHAY-PROTECTED-CUSTOM-BASELINE-v1"
}
```

For rows after line 40, `contract_revision` is exactly `non-synced-v3`,
`setup_attempt_id` is exactly `local-state-v3`, and `timing_status` is mandatory.
The first 40 rows are accepted only when all three pinned prefix hashes and every
frozen chain/path/key/task cross-check match; no other missing-field, legacy-field,
wrong-key, or false-timing exception exists.
`event_id` is globally unique; `event_revision` is monotonic within a stable
`requirement_id`; `prior_event_id` links to the previous event for that requirement.
All reference and result fields use the deterministic closed schemas and enums in
`structured_schemas`; validators reject missing/additional keys, arbitrary nested
objects, invalid transitions, malformed hashes, duplicate IDs/paths, or illegal
nulls. They remain structured even when their honest value is `not_created`,
`not_run`, `not_reviewed`, `not_requested`, or null. Status is derived from evidence,
never self-attested. `implementation_approval` records the 2026-09-13 directive;
`merge_approval` remains null until a separate explicit merge decision.
No requirement may reach complete without a Kanban task, structured changed-path
list, passing in-repository verification, three separately dispatched external-ledger reviews,
one implementation commit C, verified remote equality, and external-ledger Kanban
completion. Explicit merge approval remains required wherever merge is claimed.

The completed v3 recovery sequence is historical/idempotent validation, not work to
repeat. Frozen R0 E0006 recorded superseded v2 R0 task `t_8efbe7da`, key
`SHAY-AGENT-ENHANCEMENT-2026-09-13:0`, and these exact evidence hashes: v2 ledger
`ea480821d1264ba4a409f52ec7d893d1320237d10c66794a26b88f7258781ffa`,
initialization summary
`b1801f6e9687e3ca0d9d1a4eb7827d0473e172181ba91da5a6d284f555a399e4`,
and board database
`204bfdb20d69650b84e55faf7e64ab1ab076c443ef136632ef4d96d41bd3d8df`.
The observation is exact: `requirement.rsplit('R', 1)[1]` dropped the literal `R`,
creating `:0` through `:8` instead of `:R0` through `:R8`. Frozen R0 E0007 and
R1-R8 E0004 then linked the initialized exact `:R0` through `:R8` tasks. Validate
those rows, task IDs, keys, parents, artifacts, and current v3 files read-only; never
recreate or modify them. Neither retired task set is ever changed, commented,
completed, blocked, archived, repaired, or deleted.

The completed operational trace correction is append-only and now read-only.
R0 E0009 `verification_invalidated` records `timing_status=unknown`, blocks E0008 as
active proof, and cites both the copied timestamps and actual artifact mtimes:
self-check result `2026-09-14T01:41:13Z`, initialization summary
`2026-09-14T01:41:21Z`, and pre-verification report `2026-09-14T01:43:06Z`.
R0 E0010 `environment_relinked` binds the finalized immutable v4 environment and its
complete manifest with `timing_status=not_applicable`. R0 E0011 `verification` records
`timing_status=captured` and real, separately captured `started_at < ended_at`
intervals for every command. Idempotent reruns validate E0009/E0010/E0011 and their
artifacts byte-for-byte; they never append, reorder, repair, or replace them.

Before any R1 implementation start, rows 44-51 append exactly one additional
`environment_relinked` event for each R1-R8, ordered by requirement. Each chains to
that requirement's current E0004 row, keeps the phase in `proposed`, leaves base SHAs
null, runs no command, and binds the exact active-v4 interpreter, provenance,
final-full-manifest, summary, and root digest. All planned Python commands in these
current rows use
`/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python`.
The first 51 rows remain byte-for-byte unchanged. Rows 52-59 append one initial
`test_contract_relinked` event for each R1-R8, ordered by requirement and chained from
its E0005. Those E0006 rows bind the exact path manifests and self-contained
local-v4 commands, including both `SHAY_TEST_PYTHON` and
`SHAY_TEST_ENV_PROVENANCE`; Shay-running commands also pin disposable external
`HOME`, `SHAY_HOME`, and `SHAY_PROMPT_MEMORY_VAULT`. Row 60 is R8 E0007, which
supersedes R8 E0006 only to freeze the Phase 0 capability contract and this plan as
non-writable R8 governance, add the final-checklist output, and require the explicit
external proof-output path. The strict current trace has 60 rows. R1 is blocked unless
R1-R7 E0006 and R8 E0007 are current and all R1-R8 E0005 rows remain present. R1-R7
therefore begin phase-local work at E0007 after E0006; R8 begins at E0008 after its
occupied E0007. No future event may reuse or skip a recorded environment or
test-contract relink.

The Node installation commands use `npm ci --no-audit`; dependency installation,
type-check, and focused tests are evidence, but Node vulnerability/audit status is
explicitly **unassessed** and these commands do not constitute security clearance.

For R1-R8, after checkout, protected-hash verification, and dependency integration,
the phase-local evidence file must be the first authored file change. Its first line
is `implementation_started`, recording the external-ledger-proven reviewed primary
tip in `implementation_base_sha`, the post-integration HEAD in
`integration_base_sha`, and exact dependency refs. When no dependency is integrated,
those SHAs are equal. The file may append only implementation evidence, verification,
and honest blocked facts through verification; it contains no review, commit, push,
task-completion, or finalization metadata.

Ancestry and review gating are separate. R5 extends only R4 but is gated by completed
R3 and R4; R6 extends only R3 but is gated by completed R3 and R4. R8 bases on R7 and
creates the sole exact primary-first deterministic two-parent integration with R5.
Review-gate-only commits are not falsely inserted into R5/R6 history.

Two compatibility barriers run after the paired phase-local tested trees exist and
before either paired candidate is frozen. For R3-R6, `run-phase-tests` emits an
immutable `awaiting_pair` packet and no passing terminal. The designated coordinator
then uses the sole bound entrypoint's `run-pair-tests` verb; callers supply only the
closed pair ID and the two ordered `REQ=receipt_id` pending packet identities, never
parent tips, trees, commands, environments, or assertion values. A dedicated
hash-chained pair registry becomes authoritative only after the shared receipt and both
member packets are complete:

- The R3+R4 barrier materializes R3's tested tree, applies the complete R4 delta from
  their common reviewed R2 C/base tree, rejects every conflict, records the R2 C,
  base-tree SHA, both input tree SHAs, and deterministic composed-tree SHA, and runs the approval/cancel/restart
  compatibility cases. In the standard scrubbed E2E envelope its exact contract argv
  is `scripts/run_tests.sh --e2e tests/integration/test_kanban_restart_recovery.py
  tests/integration/test_typed_approval_clients.py`; the receipt producer, not caller
  environment, supplies and binds the two input trees and composed checkout. The same
  immutable command/result/artifact receipt hashes must
  appear in both R3 and R4 phase evidence and normal candidate receipt closure. The
  exact invocation is `run-pair-tests --pair-id SHAY-PAIR-R3-R4 --member-receipt
  SHAY-AGENT-R3=<receipt_id> --member-receipt SHAY-AGENT-R4=<receipt_id>` under the
  R3 coordinator pointer.
- The R5+R6 barrier starts from the accepted R3+R4 composed-tree receipt, applies the
  R6 delta relative to R3 and then the R5 delta relative to R4, rejects every conflict,
  records the accepted R3 C and R4 C, all four input/dependency tree SHAs, and the
  composed-tree SHA, and proves
  that optional effect and memory-provenance fields are safe when absent and truthful
  when populated. In that same envelope its exact contract argv is
  `scripts/run_tests.sh --e2e tests/integration/test_cross_client_contract.py
  tests/integration/test_memory_provenance_profiles.py`, executed in the composed
  checkout. The same immutable receipt hashes must appear in both R5 and R6
  phase evidence and normal candidate receipt closure. The exact invocation is
  `run-pair-tests --pair-id SHAY-PAIR-R5-R6 --member-receipt
  SHAY-AGENT-R5=<receipt_id> --member-receipt SHAY-AGENT-R6=<receipt_id>` under the
  R5 coordinator pointer.

The tool first appends a hash-chained issuance row containing the complete bounded
canonical self-addressed v3 transaction bytes; only then may its prepared pathname or
any shared pair artifact exist. Recovery reopens both pending packets and the accepted
ledger, requires that exact issued row, and recomputes pair authority plus both final
packet IDs/manifests/terminal evidence. A predictable caller-shaped transaction path
without an issuance row is never authority. It writes each new transaction/core/member
file first to a deterministic same-directory temporary, fsyncs the complete bytes,
performs `renameatx_np(RENAME_EXCL)` plus directory fsync, and recovers every exact
partial step idempotently without unlinking a temporary alias. Registry updates use
the common retained-prior CAS and never delete displaced authority. The core binds the
effective sandbox argv/cwd, scrubbed environment, immutable interpreter/provenance,
the SHA-256 of the actual sandbox profile bytes, a nonzero network-denial probe,
before/after tree and environment hashes, streams, timing, and derived assertions.
The command's HOME, SHAY_HOME, SHAY_PROMPT_MEMORY_VAULT, TMPDIR, caches, and coverage
file are relocated beneath the sole writable `pair-output` directory. Its
SHAY_TEST_PYTHON and SHAY_TEST_ENV_PROVENANCE equal the pinned immutable-v4 paths and
are projected into the closed receipt; the composed source checkout remains
write-denied.
Only the pair gate issues the one passing verification terminal for each member.

Changing either paired tested tree invalidates its barrier receipt and both affected
candidate freezes. R3/R4 and R5/R6 implementation may still run with maximum phase
concurrency two; each pair meets at its barrier before review. R8 consumes and
revalidates these already-passing receipt relationships while integrating reviewed
tips; it cannot mint a pair receipt and is not the first compatibility test.

The active strict external execution ledger is:

`/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/evidence/execution-events.jsonl`

with its exclusive lock at sibling `execution-events.lock`. It is outside Git and the
live owner profile and begins with the immutable single genesis prefix. A candidate
binds an exact prefix snapshot and anchor, not the mutable whole-ledger SHA; later
canonical suffix rows must extend that prefix without changing any earlier byte. It is
the only active authority for recorded candidate reviews, implementation commit C, verified push,
Kanban completion, reconciliation, and R8 `program_finalized`. The v3 board and its
nine tasks are also initialized. The unsuffixed Python 3.11 environment is retired
read-only because five pip `__pycache__` files changed after E0008. The active v4
environment is bootstrapped and locked under the immutable full-manifest/root-digest
protocol, and E0010/E0011 bind its evidence before any candidate review. The v1 ledger in the Google Drive synced
Documents location is blocked/retired by `st_nlink=2`. The unsuffixed v2 ledger and
board are invalid/retired by wrong task keys. Neither is copied, rewritten, repaired,
or accepted as a v3 hash-chain prefix or execution authority.

The pre-candidate generated-metadata transition is separately audited at
`/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/evidence/setup/r0/pre-candidate-ignored-metadata-transition-audit.json`.
An accidental read-only dependency preparation refreshed only ignored generated
`node_modules/.package-lock.json`: size/SHA changed from
`91206/ff70dbefbd9a28ef212ebae1f969e21291676925da3acd4d3e2d76495d1c8b6d` to
`91203/ec6d52a40680d0ad5aad3a321c4330d3ba39fecb570e3913d34ee7b1b954ec48`,
while type/mode/uid/gid/nlink, all 49,533 other ignored manifest entries, tracked files,
and the real index remained unchanged. It was neither restored nor deleted and is not
custom code. The final candidate starts from that audited stable state and requires
byte-identical ignored before/after manifests for only its own construction window.
The current trace transition whitelist has no operational-deviation event type, so no
existing event is repurposed; the audited transition remains external evidence, while
the immutable 60-row trace adds only the separate R8 authority-freezing E0007 row.

Each external review binds the same exact candidate and non-tree state:

```json
{
  "schema_version": 5,
  "requirement_id": "SHAY-AGENT-R0 through SHAY-AGENT-R8; exact current phase",
  "candidate_tree_sha": "<40-lowercase-hex-git-tree>",
  "implementation_base_sha": "<40-lowercase-hex-commit>",
  "integration_base_sha": "<40-lowercase-hex-commit>",
  "attempt_authority": "<exact phase/attempt ID, immutable feature branch, and failed-CI predecessor or nulls>",
  "dependency_commits": {"primary": "<exact ancestry dependency C row or null>", "integrated": "<sorted additional ancestry dependency C rows>", "ancestry_required": "<exact ancestry C set>", "review_gates": "<exact completed quality-review gates>"},
  "integration_proof": "<pinned bootstrap, exact sequential parent, or primary-first deterministic two-parent merge tree>",
  "phase_contract": "<closed integration-base Git blob hashes, exact phase manifest/tests/current event, and protected manifest>",
  "test_execution": "<R0 local-governance receipts or R1-R8 scrubbed exact-command manifest and immutable receipts>",
  "release_policy": "<R0 CI-not-applicable-bootstrap or R1-R8 required GitHub workflow path/jobs>",
  "r8_proof": "<null for R0-R7; exact candidate Git blob identity for R8>",
  "candidate_index": {"path": "<normalized-absolute-external-path>", "sha256": "<64-hex>", "mode": "0400", "uid": 501, "gid": 20, "nlink": 1, "device": "<integer>", "inode": "<integer>", "size": "<integer>", "mtime_ns": "<integer>", "flags": "<exact UF_IMMUTABLE bit>"},
  "diff_digest": {"algorithm": "sha256", "format": "git-diff-binary-full-index-find-renames-v1", "sha256": "<64-hex>"},
  "authored_blob_manifest": {"artifact_path": "<absolute>", "sha256": "<64-hex>", "mode": "0400"},
  "worktree_inventory": {"artifact_path": "<absolute>", "sha256": "<64-hex>", "mode": "0400", "format": "complete-worktree-inventory-nul-v2"},
  "ignored_state": {"format": "shay-ignored-content-manifest-v2", "before_records": "<strict-file-identity>", "after_records": "<strict-file-identity>", "before_manifest": "<strict-file-identity>", "after_manifest": "<strict-file-identity>"},
  "live_profile_sentinel": {"format": "shay-live-profile-build-temporal-content-manifest-v3", "before": "<strict-file-identity>", "after": "<strict-file-identity>"},
  "submodule_state": {"artifact_path": "<absolute>", "sha256": "<64-hex>", "mode": "0400", "format": "git-submodule-status-recursive-v1"},
  "environment": "<closed v4 manifest, summary, provenance, root-digest, and reviewed-SHA binding>",
  "board_ledger_state": "<closed board identities/query snapshot plus candidate-local ledger prefix snapshot and append-only anchor>",
  "review_procedure": {"artifact_path": "<absolute>", "sha256": "<64-hex>", "mode": "0400", "format": "shay-closed-review-procedure-v3"}
}
```

Candidate selection is explicit external authority, not a directory timestamp or
lexical guess. Under the existing `execution-events.lock`, the append-only
`candidate-selection.jsonl` hash chain records each selected candidate, while an
atomically replaced mode-0600 `active-candidate.json` names and hashes the registry's
last row, normalized candidate directory, and exact binding path/bytes. The candidate binding additionally contains `review_procedure` with the exact path, SHA-256,
format `shay-closed-review-procedure-v3`, and mode `0400`. The procedure manifest recursively
binds the single external `review_phase0_candidate.py` entrypoint, the legacy build support it
actually calls, every initialization/validation support script, `candidate-metadata.json`, the closed `verifier-self-test.json` current-property inventory and its exact `legacy-test-case-map.json` retired non-authoritative historical inventory, all
R0 E0009/E0011 evidence, final documentation validation, operational note, authored-blob
manifest, complete build-window content-hash sentinels, board snapshot, immutable ledger
prefix/anchor, the failed-review evidence, untouched research-note copies, and content-bearing
pinned GitHub source snapshots with their strict manifest, plus v4
manifest/summary/provenance, and all referenced regular inputs with exact path/hash/mode.
Its DAG is acyclic: leaves and metadata feed the procedure, the procedure feeds the binding,
the binding feeds the append-only selection registry, and the registry feeds the atomic pointer.
Metadata contains no binding or procedure SHA. The closed verifier validates every metadata
field/reference independently, cross-checks each repository input's bytes and Git mode against
the candidate tree, and every standalone review result records both verifier and procedure SHA,
the full pointer-verification digest, and measured timing.
Any drift fails closed.

The bound verifier has one callable schema-v25 current-property self-test suite. It emits a
sorted named inventory of directly executed behavioral acceptances and counterexamples; source-literal
and token-presence checks are not acceptance evidence. The separately archived schema-v4 `legacy-test-case-map.json` retains 78 historical
Round 3/4 labels only as a retired non-authoritative historical inventory. It makes no
equivalence or acceptance claim; current behavior is gated solely by the active property tests
and documentation validation. No retired test body remains callable.

R0 candidate construction and every R1-R8 `build-phase-select` construction hold the exclusive ledger and candidate-selection locks and check lifecycle eligibility before changing selection authority. For R0, a content-addressed mode-0400 prepared document is issued through a mode-0600 append-only registry before any candidate staging directory exists. That immutable preparation restricts the only staging destination to its transaction directory. `resume-select` first requires that exact issued v2 preparation (and its issued seal when present); a shaped directory without it fails before reads, rewrites, cleanup, or selection, and no legacy pre-journal resume path exists. After construction, an immutable seal binds the complete candidate artifact/index inventory and exact active-predecessor invalidation/registry/pointer replacement bytes; its `temporary_path` values are reserved compatibility fields that current code never creates, selects, rewrites, or deletes. Any populated legacy path blocks. Registry/pointer replacement instead uses the content-addressed retained-prior CAS, and only then may the candidate stage be atomically published. An immutable selected record closes the transaction. Recovery first compares the complete discovered preparation set with independently immutable `prepared` registry rows. An unissued or missing preparation fails before cleanup, abandonment, registry append, or selection mutation; discovery never promotes a document into authority. For issued transactions only, recovery verifies already-applied publication and exact installed/replacement plus mode-0400 retained/prior mutation tuples, completes only missing steps in order, fsyncs affected directories, and rejects divergent, unowned, or out-of-containment state without deleting a displaced authority. If an unsealed or sealed preselection preparation belongs to a superseded tool, recovery first issues an immutable abandoned record binding the seal when present. A preparation that crashed before staging binds a truthful `preserved_absent` state while its transaction-owned parent is held and revalidated. For an existing stage, the tool holds the no-follow root descriptor across the append and revalidates the root plus every readable top-level regular file's exact bytes and inode metadata. A mode-0400 `.shay-retained-authority` child is intentionally opaque: only its own inode metadata and sorted child-name namespace are bound, descendant bytes are labeled uninspectable without execute permission, and the tool never changes permissions or traverses, deletes, repairs, publishes, selects, or infers those descendants as authority. Sealed abandonment is allowed only while the original main registry/pointer remain exact and no candidate publication or invalidation occurred; failed transaction evidence is never silently erased.

R1-R8 write their durable transaction journal before staging/pending publication or receipt consumption. It binds all intended hashes and the full invalidation/registry/pointer replacement bytes, and records prepared, pending-published, candidate-published, receipt-consumed, and selected states. `resume-phase-select` reconciles the exact staging/pending/candidate/receipt/invalidation/registry/pointer facts and deterministically completes every before/after fsync, no-clobber directory rename, or retained-prior CAS boundary without losing or double-consuming the issued receipt. Generic cleanup preserves the candidate-staging directory named by a valid prepared journal. Authority-file temporaries are not cleanup targets; an unexpected legacy temporary blocks and is preserved. Every journal/candidate-staging directory creation, rename, atomic pointer or registry install, and cleanup fsyncs its affected parent directory. A capture that publishes an unselected candidate before failing remains immutable inactive history and is invalidated only by the next successful locked selection. No reviewer can observe a partial selection; after release, last-row
`supersedes` equals the exact inactive-directory set and exactly one non-invalidated
directory is active.

The registry
and pointer are deliberately outside the Git candidate binding to avoid a circular
hash. Reviewers accept exactly one active directory: the pointer target.
For R1-R8, `run-phase-tests` materializes the exact tested Git tree into a fresh external
no-hardlink verification checkout and executes every contracted command only against
those immutable tree bytes. Its enforced macOS sandbox starts with default-deny file writes
and allows only the exact fresh output/temp plus declared isolated Node dependency/build
directories; source/configuration and every novel absolute or symlink-escaped destination
remain unwritable for the entire command, so a transient write-and-restore attempt is denied. It runs every non-acquisition
local step through the deny-network probe. A composite Node command is split so only exact
`npm ci --ignore-scripts --no-audit --no-fund` dependency acquisition may use unrestricted
network, honestly labeled; type-check, tests, build, and every other step remain
sandbox-network-denied. Node vulnerability status remains unassessed. It then
issues a receipt ID through its protected append-only registry and stores immutable tool-owned manifest/JSONL receipts binding argv, cwd,
environment allowlist, timing, exit status, stdout/stderr bytes, validated artifacts,
interpreter, source-tree inventory, checkout before/after identity, and v4 provenance.
Each closed execution-step row also carries the bound tool SHA plus exact phase,
integration-base, tested-tree, and sandboxed-subprocess capture identity; a caller-shaped
step missing that origin cannot derive R8 markers.
The tool itself issues the exact terminal phase-evidence row only after those receipts
exist; caller-authored terminal PASS claims are rejected. The in-Git rows bind the tested
source content digest over changed paths excluding the phase-evidence file and R8 proof,
never a self-referential final tree SHA. The final candidate may differ from the tested tree
only by that issued append-only extension at the phase-evidence path and, for R8 alone, by
the freshly runner-generated proof path; the final tree exists only in the external binding
and execution ledger. The builder and reviewer compare Git trees
and reject every other post-test source or configuration change while requiring the
tested and candidate source changed-path sets to remain identical, with only the contracted R8 proof addition permitted. `build-phase-select` derives the rename-aware Git tree,
allowed/protected paths, authored blobs, index/worktree/submodule state, phase evidence,
dependencies, and temporal live/ignored guards; it assembles the complete candidate in
the disposable root and atomically publishes it before selection. An interrupted
preselection build remains inactive until `resume-phase-select` revalidates the exact
orphan and finishes selection under the same lock. Missing receipts, a forged PASS
string, unlisted/protected paths, environment drift, or partial candidate bytes fail.

Every other lowercase-40-hex directory has an immutable mode-0400 `invalidation.json` with
strict candidate identity, binding/index file identities, a complete sorted content-hash
artifact inventory, explicit safety metadata, reason, timestamp, and invalidation status.
The registry tail—not static documentation—is the exhaustive superseded inventory. Every
`supersedes` entry must itself be lowercase 40-hex. Before review,
the last registry row's sorted, duplicate-free `supersedes` set must equal exactly the
set of every other lowercase-40-hex candidate directory: no missing directory, missing
entry, future/nonexistent entry, or unregistered inactive directory is accepted.
Missing invalidations, more than one non-invalidated directory, registry or pointer
drift, or either side of that set equality failing closes the gate.

All three canonical objects must be byte-identical. The bound `candidate_index` is the
newly created authoritative mode-0400 stored copy, sealed with macOS `UF_IMMUTABLE`: its path,
bytes, mode=0400, uid/gid, nlink, device/inode, size, mtime_ns, and flags are candidate
invariants. Reviewers never provide that path to Git. Each byte-copies it to
a private mode-0600 disposable file below the external test-run root, uses only the
copy as `GIT_INDEX_FILE`, removes only that disposable copy after closing Git handles,
sets `GIT_OPTIONAL_LOCKS=0`, and proves the stored artifact is unchanged. The Round 14
mode-drift audit records the exact earlier failure: an independent reviewer passed the
authoritative path directly to `git write-tree` without `GIT_OPTIONAL_LOCKS=0`; Git's lockfile
rename preserved bytes but replaced the inode at mode 0644. That superseded artifact is
evidence only and is never chmod-repaired. Concurrent-review stress must prove the newly
sealed artifact remains byte- and metadata-identical. The digest is over the exact output of
`git diff --binary --full-index --no-ext-diff --find-renames
<integration_base_sha> <candidate_tree_sha>`.

The sole bound review entrypoint is
`/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/test-runs/r0-proof-closure-v7/review_phase0_candidate.py`.
Every invocation is `/usr/bin/env -i` with the pinned PATH, locale,
`PYTHONDONTWRITEBYTECODE=1`, and disposable external HOME/TMP/cache/coverage paths. The
exact verifier CLI is `review_phase0_candidate.py --repo /Users/famtastic-fritz/Development/FAMtastic/shay-shay --base cf6bb95e3dc12e0d4b8eadef2c33be2b39ad21b6 --pointer /Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/evidence/candidate-bindings/SHAY-AGENT-R0/active-candidate.json --run-root <fresh-absolute-external-root> verify-pointer --output <fresh-absolute-result-path>`. The typed-review CLI replaces
`verify-pointer` with `review --review-type verification|anti_pattern|quality --reviewer <identity> --dispatch-id <orchestrator-task-id> --decision passed|failed --findings-json <closed-findings-json> --output <fresh-result-path>`;
the later recorder CLI replaces it with `record-reviews --recorder <distinct-recorder-identity> --result <one-to-three immutable typed results> --output <fresh-recorder-result.json>`. Failed results may be recorded immediately; a full passing gate still requires one current result of each type. The same bound entrypoint also exposes `run-phase-tests --output <fresh-result.json>`, `build-phase-select --receipt-id <64-hex-issued-id>`, `resume-phase-select --candidate <orphan-directory>`, `prepare-commit --actor <identity> --output <fresh-result.json>`, `record-commit --actor <identity> --staging-receipt-id <64-hex-issued-id>`, R0-only `record-push-bootstrap --actor <identity>`, R1-R8 provider-backed `record-push-ci --actor <identity> --github-token-file <mode-0400-external-path>`, R2-only `record-reconciliation --actor <identity> --report-output <fresh-durable-external-path>`, `record-kanban --actor <identity>`, and R8-only `record-finalize --actor <identity> --github-token-file <mode-0400-external-path>`, each with its own fresh `--output`. `prepare-commit` is intentionally invoked only after exact staging; its output contains the deterministic `commit_tree_argv`, base64 message stdin, closed `commit_environment`, `commit_workdir`, expected commit SHA, compare-and-swap `update_ref_argv`, and retry policy. A normal `git commit`, hook, signing, or caller-chosen message is outside authority.
`--dry-structural` omits decision/findings and never records a review. The dispatch identifier is at most 255 characters and accepts either a slash-path orchestrator task ID or the safe encoded form actually assigned here, for example `root-r0-final-verification-round10`; whitespace, empty segments, traversal, and global reuse across any historical batch or supersession fail. The entrypoint
resolves the pointer under a shared lock and revalidates the requirement-specific closure. R0
reruns documentation/source/citation/protected/v4/board/ledger checks. R1-R8 load the exact
frozen authority from integration-base Git objects; recompute changed paths including both
rename endpoints, authored blobs, pre-stage inventory, submodules, v4, and protected identities;
validate the complete phase-local event chain and every dependency C ancestry; and never run the
R0-only documentation validator. Every phase recomputes
ignored-content manifests before and after, validates the immutable build-time live-profile
sentinels without reading current `~/.shay`, uses only a private stored-index copy, parses each
captured manifest in one bounded linear pass, and removes the disposable root. The standalone
result has exact `{severity,code,message,path,line}` findings, only low/medium/high/blocker
severity, and only passed/failed decisions. A failed gate remains external history. The
findings file must already be mode-0400/nlink-1, while every review/recorder result
path must be a fresh nonexistent external leaf. Inputs and outputs must be normalized,
effective-user-owned regular files outside the repository, shared v3 state, immutable
v4 environment, live `~/.shay`, protected Obsidian roots, and the complete durable
`~/.local/share/shay-agent-transactions` authority tree. Run roots, inputs, and outputs may
neither contain nor be contained by any protected root; symlink/realpath overlap also fails.
The run root must start as an empty mode-0700 owned directory. Before any child is created the
tool writes a closed ownership marker binding its exact path/inode/tool. Cleanup validates that
marker and preflights the entire tree for ownership, hardlinks, special files, and immutable
flags before changing or deleting one entry. An unmarked nonempty path or partial immutable
seal therefore fails without partial cleanup. Descriptor/path inode drift also fails. The
registry-selected inactive set is invalidated/unreviewed historical. After E0011, any candidate byte/blob,
stored-index byte or metadata,
referenced immutable inventory, ignored/submodule state, bound live temporal sentinel, v4 provenance/full-manifest/root
digest, or allowlist mutation requires all three reviews to rerun. Only then may the
exact reviewed bytes be committed once as C and pushed with C as the remote and
downstream dependency tip.

Separately orchestrator-dispatched reviewers never append the ledger. Each writes one new mode-0400 result artifact
with its exact path and SHA. A distinct recorder uses the same bound entrypoint's
`record-reviews` command with one to three unique `--result` paths and a recorder identity.
This makes a failed result and partial three-row batch durably recordable without self-attestation.
It cannot provide or alter decisions/findings: it verifies distinct types and reviewer identities,
then acquires the exclusive lock and, while holding it, reruns/verifies the selected
pointer/candidate/binding/procedure/tool hashes, each result artifact identity, the embedded
pointer-verification digest/timing, and the bound prefix plus complete lifecycle-valid suffix
immediately before appending missing events. An identical existing result is a no-op; a replacement
review first emits `review_set_superseded`; selecting a different candidate first emits
`candidate_superseded`, invalidating all old passes. Wrong result hashes, duplicate identities,
a missing type at the commit gate, phase/base drift, or prefix mutation fail before append. Local immutable-file evidence narrows but cannot cryptographically
prove reviewer cognition, agent-task identity, or independence: the local gate proves only
distinct identity strings, artifacts, and binding. The orchestrator must dispatch three separate
reviewer tasks and retain their task IDs/provenance when available; this procedural independence
remains mandatory.

Pre-stage review inventory is intentionally category-sensitive. The real index is
clean while reviewers bind the candidate through private disposable stored-index
copies, so authored files appear in
their actual committed/unstaged/untracked categories. After all three PASS records,
the commit agent may establish only the exact final authorized real-index staged state
for the allowlisted authored paths. Local proof cannot determine how many `git add`
invocations produced that final state and makes no such claim. It does **not** compare post-stage categories or the real index-file
hash to their pre-stage values. It instead requires the real-index tree, full
candidate diff digest, and authored blob manifest to match the reviews; requires
ignored/bound-live-sentinel/submodule/v4 bindings unchanged; requires no authored path left
unstaged/untracked and no unlisted path present; and captures the new post-stage
inventory shape/hash as commit evidence. Repository content and branch tip then stay
fixed at C.

The immutable candidate procedure always validates the board/SQLite and ledger snapshot
bytes captured before review; it does not recompute those temporal leaves from the later
mutable board. After the three PASS rows are recorded, the commit agent first stages the
exact four R0 manifest paths with `git add -A -- <the exact four paths>` and no other path.
Only then does `prepare-commit` run under both locks. It separately validates the current
ledger as the candidate prefix plus the required supersession and ordered
verification/anti-pattern/quality PASS rows, and the board as the captured projection plus
only the sole review recorder's exact `phase_gate=review` public add_comment comment/event.
Any other task, link, run, status, schema, comment, event, or board-file drift fails.

Before a new R0 candidate can be selected, a separate top-level
`prepare-commit-integration` command runs a non-recursive two-stage gate. Stage 1
emits the complete current named-suite result and documentation result. Stage 2
uses only dependency-injected paths below one fresh marker-owned external root and
invokes the unchanged production candidate builder, pointer verifier, three typed
PASS reviews with distinct reviewer/dispatch identities, `record-reviews`, the public
board `add_comment`, exact four-path Git staging, `prepare-commit`, and receipt/registry
reopen against a real disposable clone and authority. The integration candidate is
forbidden from self-binding this result. The next real candidate must copy and bind
the exact content-addressed issued integration receipt alongside its Stage 1 proofs.
The integration registry is append-only: under its own no-follow lock it records one
content-addressed `prepared` transaction before Stage 2 can run, and an `issued` row
must reference that exact preparation and receipt identity. A crash may leave only the
prepared row; retry reuses it and cannot authorize a receipt-only filesystem orphan.
All board validation in this lifecycle holds the authoritative DB/JSON through
no-follow descriptors, writes exact mode-0400 disposable copies, and opens only the
copied DB with SQLite `immutable=1` plus `query_only=ON`; any authoritative `-wal` or
`-shm` sidecar blocks before projection.

The prior post-CAS cross-tool selected record is retained only as immutable
history. Validation reopens its exact stored chain, candidate, original producer
archive, reconstruction provenance, and recorded recovery-authorizer identity;
the current verifier neither reruns that historical authorizer proof nor uses it
as selection or commit authority. A fresh successor must instead bind this
current tool's complete Stage 1 result and issued Stage 2 integration receipt and
invalidate the historical active candidate exactly once under the normal locks.

The resulting content-addressed staging authorization binds the active pointer, tool,
attempt/branch, parent HEAD, exact path/blob/mode set, real index tree/identity, full diff,
pre/post inventory, ignored/live/submodule/v4 invariants, review-transition digest, and the
exact raw commit object. For R0 its message is exactly
`docs: freeze Shay agent enhancement contract`. The commit agent executes only the returned
`/usr/bin/git ... commit-tree <tree> -p <parent>` argv with its base64-decoded exact stdin,
closed cwd and minimal author/committer/date environment, verifies stdout equals the issued
expected C, then runs only the returned compare-and-swap
`git -c core.hooksPath=/dev/null update-ref refs/heads/<branch> <expected-C> <parent>`. `commit-tree` cannot move the
branch; an object-before-ref crash is idempotent, and a competing ref tip is rejected.
Every deterministic receipt, preparation, and registry namespace is acquired and created through
a descriptor-relative `O_DIRECTORY|O_NOFOLLOW` walk. Publication and fsync remain relative to that
verified parent descriptor, so a symlink-preplanted receipt or registry directory fails before any
outside target write. New-name directory publication additionally uses
`renameatx_np(RENAME_EXCL)`, so a target created at the rename syscall is never clobbered.
Existing-authority replacement uses `RENAME_SWAP`, validates the displaced old inode/hash/mode,
and seals that prior inode mode `0400` under the exact content-addressed
`.shay-retained-authority` operation slot. It never unlinks a displaced authority or a
caller-controlled temporary name. Retry requires the exact installed/replacement and
retained/prior tuple. If the target changes at the exchange syscall, the tool swaps back
atomically and preserves the concurrent entry and prior authority without content, mode,
ownership, link-count, size, or modification-time mutation. Selection transaction
`temporary_path` values are closed legacy-reserved fields only; current code never creates,
selects, rewrites, or deletes them, and any populated pathname blocks the mutation.
`record-commit` runs only after exact C exists. Under both locks it revalidates the active
pointer, complete immutable closure, governing/tool hashes, three result bytes, authorized
review/board transition, stored candidate index, clean real index/worktree, and C's exact raw
bytes/tree/parent/message/author/committer/branch. Ledger fsync precedes receipt consumption;
commit-before-ledger and ledger-before-consumption retries recover, a full retry is a semantic
no-op, and stale or divergent reuse fails.

The separate external recorder/writer uses an exclusive `fcntl.flock`, validates the immutable
candidate prefix and the full JSONL lifecycle/hash chain while locked, and constructs the
old bytes plus each missing canonical UTF-8 line in a same-directory mode-0600 temporary.
It rechecks the live inode/prefix, fsyncs the replacement, atomically exchanges it with the
ledger, seals the displaced exact prior ledger mode `0400` in its content-addressed retained
history slot, fsyncs both directories, revalidates, and releases only afterward. No prior
ledger inode is deleted. A
deterministic idempotency key returns an existing semantically identical event as a
no-op; conflicting reuse fails. A crash after one or two review rows resumes with
only the missing rows, and a full retry is a no-op. A partial old line, stale prefix,
or divergent/orphan temporary cannot become history. The logical byte prefix is always
append-only; earlier history is never reordered, sorted, or repaired.

R2's implementation reconciler reads under a shared lock only the canonical repository ledger, exact phase-local
paths, external execution ledger, and exact board database. The sole
`record-reconciliation` materializes accepted C in a fresh external no-hardlink checkout,
executes the exact reconciler blob from C with exact current inputs under read locks and a
macOS sandbox that denies writes to source/repository/live/v3/v4/Obsidian/shared inputs,
binds protected-state before/after hashes,
captures a fresh immutable success or retryable failure report, and independently validates
the exact latest canonical trace rows and complete phase-local bytes against frozen authority,
the external lifecycle ledger, and exact board task/link/comment/event/task-run identities and content hashes.
The independent projection recognizes only the exact phase-start and candidate-review `add_comment`
records paired with their exact commented events; arbitrary known-task events, forged latest trace
branches, unreferenced runs, duplicates, and missing/hash-mismatched lifecycle identities fail
rather than treating the script's PASS text as authority. It validates that result against the exact
R2 candidate/C, phase evidence, current ledger prefix, and board snapshot before
appending; the reconciler itself does not append. It reconciles board links
and task status with pre-review facts, all three identical review bindings, C, remote
equality, completion, and dependency tips; it neither scans heuristically nor mutates.
R8 alone copies R1-R7 phase-local pre-review-through-verification lines byte-for-byte
into the canonical ledger before its candidate is built. It builds final in-repository
evidence/status from a frozen pre-candidate external-ledger prefix and explicitly
states that R8 review, commit, push, completion, and finalization are later facts.
`record-kanban` imports the public `complete_task` domain API only from a clean
write-confined materialization of accepted C, verifies the exact nine-task/eleven-link
contract and eligible active state, and calls it directly against the real program SQLite
database so native BEGIN/COMMIT and WAL/SHM coordination remain authoritative. It never replaces
the live database inode. Before the call it atomically issues a protected derived-path journal
under an owner-controlled transaction root outside repository/v3/v4/live/Obsidian. The journal
advances through prepared, domain-applied, and ledger-appended. The tool calls accepted-C
`complete_task` against the real database inside one outer `BEGIN IMMEDIATE` transaction and
temporarily joins its public write scopes to that connection, so target completion, claim/current-run
closure, failure reset, completion event/run, and dependent promotion commit atomically or roll back
together. Before that domain transaction, the journal binds the candidate board snapshot to exactly
one post-build `phase_gate=review` public `add_comment` row and its matching `commented` event; any
other comment, event, run, task, or link delta fails. When a ready task has no current run, the public
API synthesizes a terminal run with the authoritative enum `status=completed,outcome=completed`;
`done` is the task status, not the synthesized-run status. A crash after that one commit or after ledger fsync resumes from the exact result and
content hashes without repeating the domain call. Reconciliation binds every completed run
field: active runs retain their pre-completion id/task/profile/step/runtime/heartbeat/start
fields and close as status `done`; synthetic runs derive profile/step from the immutable
pre-review task and require null runtime/heartbeat; both require ordered non-null terminal
times, outcome `completed`, exact summary/metadata, null error/claim/expiry/PID, cleared
`current_run_id`, and the ledger-bound full row hash. Unrelated event injection, an incomplete
claim/current-run/task-run terminal state, and any other task/link/run mutation fail. No raw SQL
completion or mutable journal claim is authority.
Mutable worktree code and raw SQL are never execution authority. After all three R8 external reviews, `record-commit`
binds the selected clean committed tree, provider-backed `record-push-ci` derives origin
and the GitHub repository from Git and uses the bound Python standard-library HTTPS/TLS
client to bind workflow path and numeric ID,
the push run, exact required successful jobs, and GitHub Actions receipt bytes. A first bootstrap
or CI record constructs one closed content-addressed provider observation directly inside the
canonical ledger event. It embeds the exact canonical raw query/response bytes, their content hash,
one authoritative observation timestamp, and the normalized path/time-independent semantic projection.
The lifecycle ledger `remote_ref` binds that exact chain; there is no observation registry and no
parallel caller receipt path. Fabricated, unbound, split-clock, or semantically inconsistent observations fail. Only
a successful receipt permits `record-kanban` to perform and read back the single task
mutation. R0 is the explicit bootstrap exception: the baseline workflow runs only
`main` and ignores these governance documents, so R0 records remote equality as
`CI-not-applicable-bootstrap`, never as passed. Mandatory branch CI begins with R1
after R1 repairs `.github/workflows/tests.yml` and is required through R8.
R1 owns the stable branch dispatcher and the `test`/`e2e` jobs; R8 alone may extend
that workflow with the terminal `shay-upgrade-proof` job. The closed mapping is:

| Exact branch | Requirement selected by the workflow | Required successful jobs |
| --- | --- | --- |
| `codex/shay-agent-phase1-baseline-e2e` | `SHAY-AGENT-R1` | `test`, `e2e` |
| `codex/shay-agent-phase2-trace-reconciler` | `SHAY-AGENT-R2` | `test`, `e2e` |
| `codex/shay-agent-phase3-durable-lifecycle` | `SHAY-AGENT-R3` | `test`, `e2e` |
| `codex/shay-agent-phase4-typed-safety` | `SHAY-AGENT-R4` | `test`, `e2e` |
| `codex/shay-agent-phase5-memory-provenance` | `SHAY-AGENT-R5` | `test`, `e2e` |
| `codex/shay-agent-phase6-client-contract` | `SHAY-AGENT-R6` | `test`, `e2e` |
| `codex/shay-agent-phase7-operator-ux` | `SHAY-AGENT-R7` | `test`, `e2e` |
| `codex/shay-agent-phase8-acceptance` | `SHAY-AGENT-R8` | `test`, `e2e`, `shay-upgrade-proof` |

For R1-R7, `e2e` selects and executes only the mapped requirement's current closed
phase-command set and validates its semantic assertions; it must not silently run a
different phase or collapse to a generic smoke test. `test` preserves the baseline
regression job. The R3/R4 and R5/R6 composed-tree commands remain local pre-freeze
receipts bound in both candidates; single-branch CI validates their required receipt
closure but does not synthesize a different composition. R8 preserves both jobs and
adds the exact terminal proof job. An
unknown `codex/shay-agent-*` branch, duplicate mapping, branch/requirement mismatch,
missing required job, or a successful run for a different head SHA fails the provider
gate. A failed-CI successor uses only
`<exact-branch>-successor-<64-lowercase-hex-attempt-id>`; the ledger-bound attempt ID
must equal the suffix and the workflow maps it to the same table row. Any other suffix
or unbound successor fails. R2-R7 do not edit the workflow; they consume R1's reviewed
mapping. R8 may only
add its own mapping/job and may not weaken R1-R7 gates.
Every phase binding freezes its exact attempt ID and branch. A failed CI attempt preserves
its old remote tip and authorizes only a distinct successor branch; branch reuse,
force-push, and committing a superseded attempt fail. `record-finalize` then
recomputes the clean R8 C/tree/index, status/trace blobs, board JSON/SQLite projection,
and exact current ledger tip, re-queries every accepted remote ref plus authoritative
GitHub workflow/run/jobs/artifact metadata, and independently derives each normalized CI
anchor from the exact raw provider response before `program_finalized`. The R8 proof's immutable pre-review board/ledger snapshot is retained;
finalization separately computes the complete post-completion SQLite schema/table projection,
including `task_runs`, plus the board/ledger state and stored full projection hash. It accepts
valid candidate/review-set supersession history only when the active successor then has exactly
three current passes, commit, provider push, and the complete target/event/run/failure-reset/
dependent-promotion delta; invalid and superseded candidates remain ineligible.
Before any terminal provider call, the finalizer holds the protected no-follow ledger lock and
atomically appends generation 1 `program_finalization_query_issued`, or the next in-budget contiguous
generation after an exact retry-exhaustion closure. Each issued schema-v4 row is the only authority
for its generation. Its canonical payload binds the accepted candidate tree/binding/tool, fresh nonce and
issue time, exact completed pre-final ledger prefix/count/tip/time, all nine
provider/repository/remote/branch/ref/head targets and generation-unique derived query IDs, a fixed
30-second absolute wall-clock deadline per request, fixed per-response and aggregate byte caps,
the candidate-global generation number, and the exact prior exhaustion reference when generation
is greater than one.

Queries execute in memory with during-read caps: `git ls-remote` is drained concurrently from
stdout/stderr, and every stdlib-HTTPS DNS/connect/header/body-read operation shares one absolute
monotonic deadline rather than resetting a socket inactivity timeout. Each response/stream is
limited to 8 MiB and one attempt to 64 MiB. Overflow or deadline closes/terminates the producer
instead of buffering or slow-dripping past the bound. Immediately before every provider primitive,
the finalizer appends `program_finalization_query_started`, which binds the issued query ID,
exact canonical argv/cwd/scrubbed-environment/no-shell descriptor or HTTPS request descriptor,
attempt/call sequence, and a conservative maximum observable-byte reservation. The first such
row increments the outer retry-attempt count before I/O. Within each outer attempt the call
sequence resets to one and may consume only the exact ordered 49-call prefix: R0 remote equality,
then for each R1-R8 the remote, workflow, runs, run, jobs, and artifacts queries. Failure stops that
prefix; a 50th, repeated, skipped, or reordered call is invalid. The matching `program_finalization_query_result`
binds exact completed, failed, or interrupted evidence and reconciles actual bytes. A crash with
no result is recovered as interrupted at the full reservation charge; a durable result without
the attempt closure is failed before any new provider work. Thus neither crash window replays a
query or reuses an attempt sequence. A transient network/provider/credential/signal/timeout/rate-limit/size failure then appends
the nonterminal `program_finalization_query_attempt_failed` row. It preserves exact base64
stdout/stderr/diagnostic bytes under one joint 64 KiB failed-attempt retention cap, hashes, observed
and retained byte counts, truncation flags, exit/signal/timeout/provider status, query identity,
actual UTC request start/end, and measured monotonic elapsed. Successful prefix responses are
discarded and re-run, not duplicated into every failed row.
The same issued nonce/query plan permits at most sixteen attempts. Attempts zero through fifteen
may later succeed. The exact sixteenth transient failure is followed by
`program_finalization_retry_exhausted`, which binds all sixteen exact attempt rows and closes the
generation without claiming program completion. Automatic retry authority is candidate-wide and
finite: no more than three generations, 48 started attempts, or 64 MiB of all observed or conservatively reserved provider bytes.
Successful git and HTTP results preserve exact wire bytes so replay recomputes observed versus
retained totals; a cap-trigger byte is charged even though it is not retained beyond the closed
failure-evidence limit. At that boundary the tool appends
`program_finalization_retry_budget_exhausted`, closes the exact active issuance/current attempt or
last generation exhaustion, returns `blocked_needs_owner_action`, and performs no further provider
call. Repeated invocation is byte-idempotent and makes zero provider calls. There is no automatic
reset; no automatic retry authorization or same-UID JSON override exists. Only a separately reviewed future code/config change
outside this automation may alter the finite bound. A later success from an active in-budget generation appends
`program_finalized` with complete capped raw response bytes/content hashes and independently
derived normalized facts for all nine targets. `program_finalization_abandoned` is terminal only
for irrecoverable issued-plan or semantic-integrity failure and contains recomputable raw failure
evidence. Terminal rows bind the issuance and every intervening failed-attempt row by event ID,
sequence, line SHA, and transaction ID. No finalizer
registry, file receipt, object namespace, seal, closure, rename, cleanup, unlink, or deletion path
exists, so filesystem-only residue can never become evidence authority.

A crash before issuance leaves nothing. A crash after the issued row recovers only that pending
ledger transaction and reuses its nonce/query plan; a crash after a started row closes that exact
reservation as interrupted at its full charge, and a crash after a result closes the already
consumed attempt without another provider call. A crash after the sixteenth attempt but before
its exhaustion row appends the missing deterministic exhaustion closure. Exhausted history remains
immutable; a successor is automatic only inside the initial finite budget, and budget exhaustion
requires a separately reviewed future code/config change outside this automation. Candidate-global counters and query IDs never
reset. Retryable failures and exhausted generations never claim program completion, while a
parallel/forged/replayed grant, pending issuance, counter reset, or reused query ID is rejected. A crash
after the terminal append is an idempotent retry. Already-finalized is detected and fully
replay-validated before issuing anything or performing provider I/O; it returns the existing
terminal row byte-for-byte with zero provider calls. Missing, duplicated, replayed, oversized, or tampered issue,
raw, normalized, or query evidence; changed provider facts; missing credentials; and network
failure all fail closed. No repository byte or branch tip moves afterward.

For every R0-R8 event, `protected_custom_manifest_id` is a mechanically resolved
reference: exact equality with `protected_custom_manifest.manifest_id` in
`docs/architecture/shay-custom-capability-contract.yaml` applies that manifest's
`forbidden_path_patterns` in addition to the event's narrower `forbidden_paths`.
This shared guard always excludes `/Users/famtastic-fritz/.shay/**`, credentials and
secrets, voice/STT/TTS, filming, `PERSONA.md`, `SOUL.md`, and `docker/SOUL.md`.
Unknown or missing manifest IDs fail validation.

`planning_anchor_sha` is the shared source-audit anchor, not implementation ancestry.
It remains null in proposal rows. R0's immutable `implementation_started` row already
records both base values at
`cf6bb95e3dc12e0d4b8eadef2c33be2b39ad21b6`; recovery never duplicates or rewrites
that fact. Before v3 setup, `origin/main` drift/pin validation must still confirm that
anchor; a mismatch requires the documented drift procedure and reviewed plan update
first. R1-R8 populate their base values in their first phase-local implementation
event from externally proven dependency tips.

### Closed Phase command and path manifests

The following machine block is authoritative together with the capability contract and
the latest trace rows. Local absolute interpreter paths bind this workstation's evidence;
they are not defaults in committed runners. CI supplies its own attested absolute paths.
For a phase, the applicable test set is exactly: (a) the executable command strings in
its current `test_contract_relinked` row and the byte-equal machine block below; (b) the
non-executable acceptance assertions in that same `tests` array, derived from those
receipts; and (c) for R3/R4 or R5/R6, the applicable tool-issued compatibility-barrier
receipt defined above. Words such as focused, full, E2E, integration, or stress elsewhere
in this plan name categories; they neither add an unlisted top-level command nor permit an
applicable command to be skipped. Only an explicit current contract relink may change
that set before implementation starts.

<!-- SHAY_PHASE_CONTRACTS_V2_BEGIN -->
```json
{
  "requirements": {
    "SHAY-AGENT-R1": {
      "allowed_paths": [
        ".github/workflows/tests.yml",
        "docs/architecture/adr-shay-archived-parent-semantics.md",
        "docs/architecture/evidence/shay-agent-r1-events.jsonl",
        "scripts/run_tests.sh",
        "shay_cli/kanban_db.py",
        "tests/e2e/test_shay_baseline_e2e.py",
        "tests/shay_cli/test_kanban_core_functionality.py",
        "tests/shay_cli/test_kanban_db.py",
        "tests/stress/test_atypical_scenarios.py",
        "tests/stress/test_subprocess_e2e.py",
        "ui-tui/package-lock.json",
        "ui-tui/src/__tests__/externalCli.test.ts",
        "ui-tui/src/app/slash/commands/setup.ts",
        "ui-tui/src/lib/externalCli.ts"
      ],
      "latest_event_id": "SHAY-AGENT-R1:E0006",
      "tests": [
        "SHAY_PHASE_RUN_ROOT=$(mktemp -d /Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/test-runs/SHAY-AGENT-R1.XXXXXX) && trap 'chmod -R u+w \"$SHAY_PHASE_RUN_ROOT\" 2>/dev/null || true; rm -rf \"$SHAY_PHASE_RUN_ROOT\"' EXIT && mkdir -p \"$SHAY_PHASE_RUN_ROOT/home\" \"$SHAY_PHASE_RUN_ROOT/shay-home\" \"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" SHAY_HOME=\"$SHAY_PHASE_RUN_ROOT/shay-home\" SHAY_PROMPT_MEMORY_VAULT=\"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json scripts/run_tests.sh",
        "SHAY_PHASE_RUN_ROOT=$(mktemp -d /Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/test-runs/SHAY-AGENT-R1.XXXXXX) && trap 'chmod -R u+w \"$SHAY_PHASE_RUN_ROOT\" 2>/dev/null || true; rm -rf \"$SHAY_PHASE_RUN_ROOT\"' EXIT && mkdir -p \"$SHAY_PHASE_RUN_ROOT/home\" \"$SHAY_PHASE_RUN_ROOT/shay-home\" \"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" SHAY_HOME=\"$SHAY_PHASE_RUN_ROOT/shay-home\" SHAY_PROMPT_MEMORY_VAULT=\"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json scripts/run_tests.sh --e2e",
        "SHAY_PHASE_RUN_ROOT=$(mktemp -d /Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/test-runs/SHAY-AGENT-R1-node.XXXXXX) && trap 'chmod -R u+w \"$SHAY_PHASE_RUN_ROOT\" 2>/dev/null || true; rm -rf \"$SHAY_PHASE_RUN_ROOT\"' EXIT && mkdir -p \"$SHAY_PHASE_RUN_ROOT/home\" \"$SHAY_PHASE_RUN_ROOT/npm-cache\" \"$SHAY_PHASE_RUN_ROOT/repo\" && GIT_INDEX_FILE=\"$SHAY_PHASE_RUN_ROOT/candidate-index\" git read-tree HEAD && GIT_INDEX_FILE=\"$SHAY_PHASE_RUN_ROOT/candidate-index\" git add -A -- ui-tui/package-lock.json ui-tui/src/lib/externalCli.ts ui-tui/src/app/slash/commands/setup.ts ui-tui/src/__tests__/externalCli.test.ts && SHAY_NODE_TREE=$(GIT_INDEX_FILE=\"$SHAY_PHASE_RUN_ROOT/candidate-index\" git write-tree) && git archive \"$SHAY_NODE_TREE\" ui-tui | tar -xf - -C \"$SHAY_PHASE_RUN_ROOT/repo\" && cd \"$SHAY_PHASE_RUN_ROOT/repo/ui-tui\" && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" FNM_DIR=/Users/famtastic-fritz/.local/share/fnm npm_config_cache=\"$SHAY_PHASE_RUN_ROOT/npm-cache\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json /opt/homebrew/Cellar/fnm/1.39.0/bin/fnm exec --using 24.19.0 -- node --version | grep -Fx v24.19.0 && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" FNM_DIR=/Users/famtastic-fritz/.local/share/fnm npm_config_cache=\"$SHAY_PHASE_RUN_ROOT/npm-cache\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json /opt/homebrew/Cellar/fnm/1.39.0/bin/fnm exec --using 24.19.0 -- npm --version | grep -Fx 11.17.0 && test \"$(jq -r .lockfileVersion package-lock.json)\" = 3 && test \"$(jq -r '.packages[\"node_modules/eslint-plugin-react-compiler\"].dependencies[\"hermes-parser\"]' package-lock.json)\" = ^0.25.1 && test \"$(jq -r '.packages[\"node_modules/eslint-plugin-react-hooks\"].dependencies[\"hermes-parser\"]' package-lock.json)\" = ^0.25.1 && test \"$(jq -r '.packages[\"node_modules/hermes-parser\"].version' package-lock.json)\" = 0.25.1 && test \"$(jq -r '.packages[\"node_modules/hermes-estree\"].version' package-lock.json)\" = 0.25.1 && ! jq -e '.packages[\"node_modules/shay-parser\"] or .packages[\"node_modules/shay-estree\"]' package-lock.json >/dev/null && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" FNM_DIR=/Users/famtastic-fritz/.local/share/fnm npm_config_cache=\"$SHAY_PHASE_RUN_ROOT/npm-cache\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json /opt/homebrew/Cellar/fnm/1.39.0/bin/fnm exec --using 24.19.0 -- npm ci --ignore-scripts --no-audit --no-fund && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" FNM_DIR=/Users/famtastic-fritz/.local/share/fnm npm_config_cache=\"$SHAY_PHASE_RUN_ROOT/npm-cache\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json /opt/homebrew/Cellar/fnm/1.39.0/bin/fnm exec --using 24.19.0 -- npm run type-check && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" FNM_DIR=/Users/famtastic-fritz/.local/share/fnm npm_config_cache=\"$SHAY_PHASE_RUN_ROOT/npm-cache\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json /opt/homebrew/Cellar/fnm/1.39.0/bin/fnm exec --using 24.19.0 -- npm test -- src/__tests__/externalCli.test.ts",
        "baseline evidence at cf6bb95: clean-cache npm ci fails 404 on rename-damaged shay-parser/shay-estree; integrity-matched cached tarballs reach type-check, which fails on invalid launchShay-ShayCommand and resolveShay-ShayBin identifiers; this is a required R1 repair, not a passing gate",
        "post-repair lockfile retains lockfileVersion 3, restores authoritative hermes-parser/hermes-estree 0.25.1 dependencies, URLs, and integrity, contains no shay-parser/shay-estree entry, and clean-registry npm ci succeeds",
        "fresh database: five concurrent same-key creates return one ID and one non-archived row; two distinct keys return two tasks",
        "existing tests/stress/test_atypical_scenarios.py intent passes without skip or weakening",
        "exact external SHAY_TEST_PYTHON and SHAY_TEST_ENV_PROVENANCE validate Python 3.11, pip check, all+dev provenance, and never auto-install or fall back",
        "two isolated SHAY_HOME runs leave byte-identical owner live-profile path/hash/mtime sentinels"
      ]
    },
    "SHAY-AGENT-R2": {
      "allowed_paths": [
        "docs/architecture/evidence/shay-agent-r2-events.jsonl",
        "scripts/reconcile_shay_agent_trace.py",
        "tests/scripts/test_reconcile_shay_agent_trace.py"
      ],
      "latest_event_id": "SHAY-AGENT-R2:E0006",
      "tests": [
        "SHAY_PHASE_RUN_ROOT=$(mktemp -d /Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/test-runs/SHAY-AGENT-R2.XXXXXX) && trap 'chmod -R u+w \"$SHAY_PHASE_RUN_ROOT\" 2>/dev/null || true; rm -rf \"$SHAY_PHASE_RUN_ROOT\"' EXIT && mkdir -p \"$SHAY_PHASE_RUN_ROOT/home\" \"$SHAY_PHASE_RUN_ROOT/shay-home\" \"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" SHAY_HOME=\"$SHAY_PHASE_RUN_ROOT/shay-home\" SHAY_PROMPT_MEMORY_VAULT=\"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json scripts/run_tests.sh tests/scripts/test_reconcile_shay_agent_trace.py",
        "read-only reconciliation cross-checks canonical and phase-local pre-review facts, external execution-ledger hash chain/reviews/commit/push/completion, exact board tasks/links, and dependency tips"
      ]
    },
    "SHAY-AGENT-R3": {
      "allowed_paths": [
        "docs/architecture/adr-shay-durable-task-run-ownership.md",
        "docs/architecture/evidence/shay-agent-r3-events.jsonl",
        "gateway/platforms/api_server.py",
        "shay_cli/kanban_db.py",
        "shay_cli/kanban_run_adapter.py",
        "tests/gateway/test_api_server_runs.py",
        "tests/integration/test_kanban_restart_recovery.py",
        "tests/shay_cli/test_kanban_db.py",
        "tests/shay_cli/test_kanban_run_adapter.py",
        "tests/stress/test_concurrency.py"
      ],
      "latest_event_id": "SHAY-AGENT-R3:E0006",
      "tests": [
        "R1 same-key/different-key regressions and original atypical scenario pass unchanged",
        "legacy duplicate migration preserves rows, reconciles deterministically, and is idempotent",
        "SHAY_PHASE_RUN_ROOT=$(mktemp -d /Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/test-runs/SHAY-AGENT-R3.XXXXXX) && trap 'chmod -R u+w \"$SHAY_PHASE_RUN_ROOT\" 2>/dev/null || true; rm -rf \"$SHAY_PHASE_RUN_ROOT\"' EXIT && mkdir -p \"$SHAY_PHASE_RUN_ROOT/home\" \"$SHAY_PHASE_RUN_ROOT/shay-home\" \"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" SHAY_HOME=\"$SHAY_PHASE_RUN_ROOT/shay-home\" SHAY_PROMPT_MEMORY_VAULT=\"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json scripts/run_tests.sh tests/shay_cli/test_kanban_db.py tests/shay_cli/test_kanban_run_adapter.py tests/gateway/test_api_server_runs.py",
        "SHAY_PHASE_RUN_ROOT=$(mktemp -d /Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/test-runs/SHAY-AGENT-R3.XXXXXX) && trap 'chmod -R u+w \"$SHAY_PHASE_RUN_ROOT\" 2>/dev/null || true; rm -rf \"$SHAY_PHASE_RUN_ROOT\"' EXIT && mkdir -p \"$SHAY_PHASE_RUN_ROOT/home\" \"$SHAY_PHASE_RUN_ROOT/shay-home\" \"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" SHAY_HOME=\"$SHAY_PHASE_RUN_ROOT/shay-home\" SHAY_PROMPT_MEMORY_VAULT=\"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json scripts/run_tests.sh --e2e tests/integration/test_kanban_restart_recovery.py",
        "same service/API request before and after restart adds no task, run, or event transition",
        "killed-mid-tool recovery is interrupted/uncertain or retry-required without false completion; external-effect exactly-once is not claimed",
        "R3 records phase-local evidence only; canonical common proof and bundle are R8-owned"
      ]
    },
    "SHAY-AGENT-R4": {
      "allowed_paths": [
        "docs/architecture/evidence/shay-agent-r4-events.jsonl",
        "model_tools.py",
        "plugins/safety_policy/__init__.py",
        "plugins/safety_policy/ledger.py",
        "plugins/safety_policy/plugin.yaml",
        "plugins/safety_policy/policy.py",
        "run_agent.py",
        "shay_cli/plugins.py",
        "tests/integration/test_typed_approval_clients.py",
        "tests/plugins/test_safety_policy.py",
        "tests/run_agent/test_run_agent.py",
        "tests/shay_cli/test_plugins.py",
        "tests/test_model_tools.py",
        "tests/tools/test_approval.py",
        "tools/approval.py"
      ],
      "latest_event_id": "SHAY-AGENT-R4:E0006",
      "tests": [
        "SHAY_PHASE_RUN_ROOT=$(mktemp -d /Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/test-runs/SHAY-AGENT-R4.XXXXXX) && trap 'chmod -R u+w \"$SHAY_PHASE_RUN_ROOT\" 2>/dev/null || true; rm -rf \"$SHAY_PHASE_RUN_ROOT\"' EXIT && mkdir -p \"$SHAY_PHASE_RUN_ROOT/home\" \"$SHAY_PHASE_RUN_ROOT/shay-home\" \"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" SHAY_HOME=\"$SHAY_PHASE_RUN_ROOT/shay-home\" SHAY_PROMPT_MEMORY_VAULT=\"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json scripts/run_tests.sh tests/shay_cli/test_plugins.py tests/test_model_tools.py tests/run_agent/test_run_agent.py tests/tools/test_approval.py tests/plugins/test_safety_policy.py",
        "SHAY_PHASE_RUN_ROOT=$(mktemp -d /Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/test-runs/SHAY-AGENT-R4.XXXXXX) && trap 'chmod -R u+w \"$SHAY_PHASE_RUN_ROOT\" 2>/dev/null || true; rm -rf \"$SHAY_PHASE_RUN_ROOT\"' EXIT && mkdir -p \"$SHAY_PHASE_RUN_ROOT/home\" \"$SHAY_PHASE_RUN_ROOT/shay-home\" \"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" SHAY_HOME=\"$SHAY_PHASE_RUN_ROOT/shay-home\" SHAY_PROMPT_MEMORY_VAULT=\"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json scripts/run_tests.sh --e2e tests/integration/test_typed_approval_clients.py",
        "concurrent deny/block/timeout/hook error produces zero checkpoint/ref/process/dispatch/external-effect changes while sequential order remains unchanged",
        "docker/singularity/modal/daytona/vercel_sandbox remain explicit isolated-backend containment cases, not host-hardline assertions"
      ]
    },
    "SHAY-AGENT-R5": {
      "allowed_paths": [
        "agent/memory_manager.py",
        "agent/memory_provider.py",
        "docs/architecture/evidence/shay-agent-r5-events.jsonl",
        "run_agent.py",
        "tests/agent/test_memory_prefetch_trace.py",
        "tests/agent/test_memory_provider.py",
        "tests/fixtures/memory_provenance_benchmark_v1.json",
        "tests/integration/test_memory_provenance_profiles.py",
        "tests/run_agent/test_run_agent.py",
        "tests/tools/test_memory_provenance.py",
        "tests/tools/test_memory_tool.py",
        "tools/memory_provenance.py",
        "tools/memory_tool.py"
      ],
      "latest_event_id": "SHAY-AGENT-R5:E0006",
      "tests": [
        "SHAY_PHASE_RUN_ROOT=$(mktemp -d /Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/test-runs/SHAY-AGENT-R5.XXXXXX) && trap 'chmod -R u+w \"$SHAY_PHASE_RUN_ROOT\" 2>/dev/null || true; rm -rf \"$SHAY_PHASE_RUN_ROOT\"' EXIT && mkdir -p \"$SHAY_PHASE_RUN_ROOT/home\" \"$SHAY_PHASE_RUN_ROOT/shay-home\" \"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" SHAY_HOME=\"$SHAY_PHASE_RUN_ROOT/shay-home\" SHAY_PROMPT_MEMORY_VAULT=\"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json scripts/run_tests.sh tests/tools/test_memory_provenance.py tests/tools/test_memory_tool.py tests/agent/test_memory_provider.py tests/agent/test_memory_prefetch_trace.py tests/run_agent/test_run_agent.py",
        "SHAY_PHASE_RUN_ROOT=$(mktemp -d /Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/test-runs/SHAY-AGENT-R5.XXXXXX) && trap 'chmod -R u+w \"$SHAY_PHASE_RUN_ROOT\" 2>/dev/null || true; rm -rf \"$SHAY_PHASE_RUN_ROOT\"' EXIT && mkdir -p \"$SHAY_PHASE_RUN_ROOT/home\" \"$SHAY_PHASE_RUN_ROOT/shay-home\" \"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" SHAY_HOME=\"$SHAY_PHASE_RUN_ROOT/shay-home\" SHAY_PROMPT_MEMORY_VAULT=\"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json scripts/run_tests.sh --e2e tests/integration/test_memory_provenance_profiles.py",
        "SHAY_PHASE_RUN_ROOT=$(mktemp -d /Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/test-runs/SHAY-AGENT-R5.XXXXXX) && trap 'chmod -R u+w \"$SHAY_PHASE_RUN_ROOT\" 2>/dev/null || true; rm -rf \"$SHAY_PHASE_RUN_ROOT\"' EXIT && mkdir -p \"$SHAY_PHASE_RUN_ROOT/home\" \"$SHAY_PHASE_RUN_ROOT/shay-home\" \"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" SHAY_HOME=\"$SHAY_PHASE_RUN_ROOT/shay-home\" SHAY_PROMPT_MEMORY_VAULT=\"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json scripts/run_tests.sh --e2e tests/integration/test_memory_provenance_profiles.py -k test_memory_provenance_benchmark_gate",
        "the deterministic benchmark gate reads exactly tests/fixtures/memory_provenance_benchmark_v1.json and enforces phase_5_memory_benchmark_contract without network, LLM, or owner paths",
        "two isolated non-live SHAY_HOME profiles with distinct session namespaces cannot retrieve or modify each other; no multi-tenant authority is claimed"
      ]
    },
    "SHAY-AGENT-R6": {
      "allowed_paths": [
        "acp_adapter/server.py",
        "acp_adapter/session.py",
        "cli.py",
        "docs/architecture/adr-shay-client-domain-contract.md",
        "docs/architecture/evidence/shay-agent-r6-events.jsonl",
        "gateway/platforms/api_server.py",
        "shay_cli/domain_contract.py",
        "tests/acp/test_server.py",
        "tests/cli/test_cli_domain_contract.py",
        "tests/gateway/test_api_server_runs.py",
        "tests/integration/test_cross_client_contract.py",
        "tests/shay_cli/test_domain_contract.py",
        "tests/tui_gateway/test_protocol.py",
        "tui_gateway/server.py",
        "ui-tui/src/__tests__/gatewayClient.test.ts",
        "ui-tui/src/gatewayClient.ts"
      ],
      "latest_event_id": "SHAY-AGENT-R6:E0006",
      "tests": [
        "SHAY_PHASE_RUN_ROOT=$(mktemp -d /Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/test-runs/SHAY-AGENT-R6.XXXXXX) && trap 'chmod -R u+w \"$SHAY_PHASE_RUN_ROOT\" 2>/dev/null || true; rm -rf \"$SHAY_PHASE_RUN_ROOT\"' EXIT && mkdir -p \"$SHAY_PHASE_RUN_ROOT/home\" \"$SHAY_PHASE_RUN_ROOT/shay-home\" \"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" SHAY_HOME=\"$SHAY_PHASE_RUN_ROOT/shay-home\" SHAY_PROMPT_MEMORY_VAULT=\"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json scripts/run_tests.sh tests/shay_cli/test_domain_contract.py tests/cli/test_cli_domain_contract.py tests/gateway/test_api_server_runs.py tests/tui_gateway/test_protocol.py tests/acp/test_server.py",
        "SHAY_PHASE_RUN_ROOT=$(mktemp -d /Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/test-runs/SHAY-AGENT-R6.XXXXXX) && trap 'chmod -R u+w \"$SHAY_PHASE_RUN_ROOT\" 2>/dev/null || true; rm -rf \"$SHAY_PHASE_RUN_ROOT\"' EXIT && mkdir -p \"$SHAY_PHASE_RUN_ROOT/home\" \"$SHAY_PHASE_RUN_ROOT/shay-home\" \"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" SHAY_HOME=\"$SHAY_PHASE_RUN_ROOT/shay-home\" SHAY_PROMPT_MEMORY_VAULT=\"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json scripts/run_tests.sh --e2e tests/integration/test_cross_client_contract.py",
        "SHAY_PHASE_RUN_ROOT=$(mktemp -d /Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/test-runs/SHAY-AGENT-R6-node.XXXXXX) && trap 'chmod -R u+w \"$SHAY_PHASE_RUN_ROOT\" 2>/dev/null || true; rm -rf \"$SHAY_PHASE_RUN_ROOT\"' EXIT && mkdir -p \"$SHAY_PHASE_RUN_ROOT/home\" \"$SHAY_PHASE_RUN_ROOT/npm-cache\" \"$SHAY_PHASE_RUN_ROOT/repo\" && GIT_INDEX_FILE=\"$SHAY_PHASE_RUN_ROOT/candidate-index\" git read-tree HEAD && GIT_INDEX_FILE=\"$SHAY_PHASE_RUN_ROOT/candidate-index\" git add -A -- ui-tui/src/gatewayClient.ts ui-tui/src/__tests__/gatewayClient.test.ts && SHAY_NODE_TREE=$(GIT_INDEX_FILE=\"$SHAY_PHASE_RUN_ROOT/candidate-index\" git write-tree) && git archive \"$SHAY_NODE_TREE\" ui-tui | tar -xf - -C \"$SHAY_PHASE_RUN_ROOT/repo\" && cd \"$SHAY_PHASE_RUN_ROOT/repo/ui-tui\" && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" FNM_DIR=/Users/famtastic-fritz/.local/share/fnm npm_config_cache=\"$SHAY_PHASE_RUN_ROOT/npm-cache\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json /opt/homebrew/Cellar/fnm/1.39.0/bin/fnm exec --using 24.19.0 -- node --version | grep -Fx v24.19.0 && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" FNM_DIR=/Users/famtastic-fritz/.local/share/fnm npm_config_cache=\"$SHAY_PHASE_RUN_ROOT/npm-cache\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json /opt/homebrew/Cellar/fnm/1.39.0/bin/fnm exec --using 24.19.0 -- npm --version | grep -Fx 11.17.0 && test \"$(jq -r .lockfileVersion package-lock.json)\" = 3 && test \"$(jq -r '.packages[\"node_modules/eslint-plugin-react-compiler\"].dependencies[\"hermes-parser\"]' package-lock.json)\" = ^0.25.1 && test \"$(jq -r '.packages[\"node_modules/eslint-plugin-react-hooks\"].dependencies[\"hermes-parser\"]' package-lock.json)\" = ^0.25.1 && test \"$(jq -r '.packages[\"node_modules/hermes-parser\"].version' package-lock.json)\" = 0.25.1 && test \"$(jq -r '.packages[\"node_modules/hermes-estree\"].version' package-lock.json)\" = 0.25.1 && ! jq -e '.packages[\"node_modules/shay-parser\"] or .packages[\"node_modules/shay-estree\"]' package-lock.json >/dev/null && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" FNM_DIR=/Users/famtastic-fritz/.local/share/fnm npm_config_cache=\"$SHAY_PHASE_RUN_ROOT/npm-cache\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json /opt/homebrew/Cellar/fnm/1.39.0/bin/fnm exec --using 24.19.0 -- npm ci --ignore-scripts --no-audit --no-fund && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" FNM_DIR=/Users/famtastic-fritz/.local/share/fnm npm_config_cache=\"$SHAY_PHASE_RUN_ROOT/npm-cache\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json /opt/homebrew/Cellar/fnm/1.39.0/bin/fnm exec --using 24.19.0 -- npm run type-check && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" FNM_DIR=/Users/famtastic-fritz/.local/share/fnm npm_config_cache=\"$SHAY_PHASE_RUN_ROOT/npm-cache\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json /opt/homebrew/Cellar/fnm/1.39.0/bin/fnm exec --using 24.19.0 -- npm test -- src/__tests__/gatewayClient.test.ts",
        "the R6 Node proof inherits the externally complete reviewed R1 rename-damage repair, rejects shay-parser/shay-estree lock entries, requires authoritative hermes-parser/hermes-estree 0.25.1 entries, and runs package-lock v3 npm ci, the actual type-check script, and the focused gatewayClient Vitest test in an external disposable copy; repository ui-tui/node_modules and ignored state remain untouched"
      ]
    },
    "SHAY-AGENT-R7": {
      "allowed_paths": [
        "docs/architecture/evidence/shay-agent-r7-events.jsonl",
        "plugins/operator_view/__init__.py",
        "plugins/operator_view/commands.py",
        "plugins/operator_view/plugin.yaml",
        "shay_cli/doctor.py",
        "tests/integration/test_operator_view.py",
        "tests/plugins/test_operator_view.py",
        "tests/shay_cli/test_doctor.py"
      ],
      "latest_event_id": "SHAY-AGENT-R7:E0006",
      "tests": [
        "SHAY_PHASE_RUN_ROOT=$(mktemp -d /Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/test-runs/SHAY-AGENT-R7.XXXXXX) && trap 'chmod -R u+w \"$SHAY_PHASE_RUN_ROOT\" 2>/dev/null || true; rm -rf \"$SHAY_PHASE_RUN_ROOT\"' EXIT && mkdir -p \"$SHAY_PHASE_RUN_ROOT/home\" \"$SHAY_PHASE_RUN_ROOT/shay-home\" \"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" SHAY_HOME=\"$SHAY_PHASE_RUN_ROOT/shay-home\" SHAY_PROMPT_MEMORY_VAULT=\"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json scripts/run_tests.sh tests/plugins/test_operator_view.py tests/shay_cli/test_doctor.py",
        "SHAY_PHASE_RUN_ROOT=$(mktemp -d /Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/test-runs/SHAY-AGENT-R7.XXXXXX) && trap 'chmod -R u+w \"$SHAY_PHASE_RUN_ROOT\" 2>/dev/null || true; rm -rf \"$SHAY_PHASE_RUN_ROOT\"' EXIT && mkdir -p \"$SHAY_PHASE_RUN_ROOT/home\" \"$SHAY_PHASE_RUN_ROOT/shay-home\" \"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" SHAY_HOME=\"$SHAY_PHASE_RUN_ROOT/shay-home\" SHAY_PROMPT_MEMORY_VAULT=\"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json scripts/run_tests.sh --e2e tests/integration/test_operator_view.py",
        "R7 records phase-local evidence only; canonical common proof and bundle are R8-owned"
      ]
    },
    "SHAY-AGENT-R8": {
      "allowed_paths": [
        ".github/workflows/tests.yml",
        "docs/architecture/evidence/shay-agent-r8-events.jsonl",
        "docs/architecture/evidence/shay-agent-upgrade-evidence.json",
        "docs/architecture/shay-agent-enhancement-trace.jsonl",
        "docs/architecture/shay-current-state-diagrams.md",
        "docs/status/shay-agent-enhancement-final-checklist.md",
        "docs/status/shay-agent-enhancement-status.md",
        "scripts/run_shay_upgrade_proof.sh",
        "tests/e2e/test_shay_upgrade_proof.py"
      ],
      "latest_event_id": "SHAY-AGENT-R8:E0007",
      "tests": [
        "SHAY_PHASE_RUN_ROOT=$(mktemp -d /Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/test-runs/SHAY-AGENT-R8.XXXXXX) && trap 'chmod -R u+w \"$SHAY_PHASE_RUN_ROOT\" 2>/dev/null || true; rm -rf \"$SHAY_PHASE_RUN_ROOT\"' EXIT && mkdir -p \"$SHAY_PHASE_RUN_ROOT/home\" \"$SHAY_PHASE_RUN_ROOT/shay-home\" \"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" SHAY_HOME=\"$SHAY_PHASE_RUN_ROOT/shay-home\" SHAY_PROMPT_MEMORY_VAULT=\"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json SHAY_UPGRADE_PROOF_OUTPUT=\"$SHAY_PHASE_RUN_ROOT/shay-agent-upgrade-proof.json\" scripts/run_shay_upgrade_proof.sh",
        "SHAY_PHASE_RUN_ROOT=$(mktemp -d /Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/test-runs/SHAY-AGENT-R8.XXXXXX) && trap 'chmod -R u+w \"$SHAY_PHASE_RUN_ROOT\" 2>/dev/null || true; rm -rf \"$SHAY_PHASE_RUN_ROOT\"' EXIT && mkdir -p \"$SHAY_PHASE_RUN_ROOT/home\" \"$SHAY_PHASE_RUN_ROOT/shay-home\" \"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" && env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 HOME=\"$SHAY_PHASE_RUN_ROOT/home\" SHAY_HOME=\"$SHAY_PHASE_RUN_ROOT/shay-home\" SHAY_PROMPT_MEMORY_VAULT=\"$SHAY_PHASE_RUN_ROOT/prompt-memory-vault\" SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json scripts/run_tests.sh --e2e tests/e2e/test_shay_upgrade_proof.py",
        "scripts/run_shay_upgrade_proof.sh emits exactly six R8-owned PASS markers and a closed-schema external evidence artifact with all assertions true, copied byte-for-byte before candidate freeze",
        "R1-R7 pre-review-through-verification ingestion is byte-for-byte and final evidence/status bind a frozen pre-candidate external-ledger prefix",
        "candidate verification worktree remains inventory-identical while proof writes an external temp artifact copied byte-for-byte before candidate freeze",
        "R8 changed-path validation rejects either frozen Phase 0 governing file and accepts only the reviewed E0007 manifest",
        "status page explicitly states R8 final reviews, commit, push, Kanban completion, and program_finalized are later external facts not attested in-repository",
        "three external reviews bind one R8 candidate; one commit C remains local/remote tip; completion and program_finalized append externally with no repository mutation after C",
        "changed cutoff input, duplicate finalization, an event after finalization, or self-referential Git claim fails nonzero"
      ]
    }
  },
  "schema_version": 2
}
```
<!-- SHAY_PHASE_CONTRACTS_V2_END -->

The frozen R8 E0007 phrase that the proof script "emits" six marker lines describes
reporter output, not acceptance authority. The bound verifier ignores candidate-controlled
marker/assertion strings and derives the six markers only after validating its six closed
kind-specific projections: Git tree/base/manifests; complete R1-R7 lifecycle; ignored/live/v4
content hashes plus behavioral rollback; exact reviewed R5 candidate/C/completion/test and
phase-evidence bytes; all issued protocol receipts; and exact sandboxed CLI E2E command,
exit, output, source-blob, and fresh proof digests. Negative behavioral fixtures alter each
relation and must fail.

The isolated Phase 0 baseline run is intentionally red and is evidence, not a bypass:
clean-cache `npm ci` returns 404 for rename-damaged `shay-parser@0.25.1`; seeding the two
integrity-identical tarball blobs reaches `tsc`, which then rejects the committed invalid
`launchShay-ShayCommand` and `resolveShay-ShayBin` identifiers. Phase 1 owns the exact
lockfile/source repair and a focused `externalCli` regression. Its post-repair Node gate
must use clean public-registry resolution; the cache reconstruction is not an acceptance
path.

R6's later Node command is grounded in `ui-tui/package.json`: `type-check` is `tsc --noEmit
-p tsconfig.json`, `test` is `vitest run`, and the focused existing test is
`ui-tui/src/__tests__/gatewayClient.test.ts`. It operates only in its disposable external
copy and cache, inherits the externally complete reviewed Phase 1 repair, rejects any
remaining `shay-parser`/`shay-estree` lock entry, and confirms the authoritative
`hermes-parser`/`hermes-estree` 0.25.1 entries before `npm ci`. Phase 1 branch CI provisions
the pinned Node/npm versions; R6 does not edit the workflow or inherited baseline files.

### Isolated program board

This program uses Shay's real named-board implementation, not a new project table.
For the active `local-state-v3` attempt, both `SHAY_HOME` and `SHAY_KANBAN_HOME` are pinned to
`/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3`,
and `SHAY_KANBAN_BOARD` is `shay-agent-enhancement-2026-09-13`. Under the current
`kanban_home()`/`boards_root()`/`kanban_db_path()` resolver, the exact database is:

`/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/kanban/boards/shay-agent-enhancement-2026-09-13/kanban.db`

The same source resolver yields these other exact active paths:

- board directory: `/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/kanban/boards/shay-agent-enhancement-2026-09-13`
- metadata: `/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/kanban/boards/shay-agent-enhancement-2026-09-13/board.json`
- database: `/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/kanban/boards/shay-agent-enhancement-2026-09-13/kanban.db`
- workspaces: `/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/kanban/boards/shay-agent-enhancement-2026-09-13/workspaces`
- logs: `/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/kanban/boards/shay-agent-enhancement-2026-09-13/logs`
- evidence: `/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/evidence`
- test runs: `/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/test-runs`

The exact board name is `Shay Agent Enhancement 2026-09-13` and the exact board
description is `program_id=SHAY-AGENT-ENHANCEMENT-2026-09-13`. The stable program
identity is `SHAY-AGENT-ENHANCEMENT-2026-09-13`; the initialized tasks use exact keys
`SHAY-AGENT-ENHANCEMENT-2026-09-13:R0` through `:R8`. R0's drift-checked base
remains `cf6bb95e3dc12e0d4b8eadef2c33be2b39ad21b6`. The v3 setup operator already
validated the 29-row historical prefix, appended E0006, wrote/hashed the initialization
artifacts, initialized the fresh v3 ledger and board, created and read back all nine
tasks/links, and appended E0007 plus all R1-R8 E0004 relinks. Current operators only
validate those objects read-only. They never rerun initialization, reuse a retired
task, switch the current board, or start the dispatcher.

The historical initialization key map was constructed completely in memory and the
literal `R` is part of every suffix. On every later entry, read back and assert exact
dictionary equality with all nine expected keys, uniqueness, order, task IDs, and
parents before any permitted task comment/status write. The failed v2 algorithm
`requirement.rsplit('R', 1)[1]`, numeric conversion, and all v3 task creation or repair
remain forbidden.

Board setup starts in a scrubbed child environment. Reject inherited `SHAY_HOME`,
`SHAY_KANBAN_HOME`, `SHAY_KANBAN_BOARD`, `SHAY_KANBAN_DB`, and
`SHAY_KANBAN_WORKSPACES_ROOT`; leave the direct database/workspace overrides unset;
then pin only the three exact values above. The source precedence is explicit:
`SHAY_KANBAN_HOME` controls `kanban_home()`, `SHAY_HOME` is its fallback input,
`SHAY_KANBAN_DB` bypasses `kanban_db_path()`, `SHAY_KANBAN_WORKSPACES_ROOT` bypasses
`workspaces_root()`, and `SHAY_KANBAN_BOARD` bypasses the current-board file.

Before **any later authorized task write**, resolve without creating and assert the exact program
root, board directory, metadata file, database, workspaces directory, and log
directory through `kanban_home()`, `board_dir()`, `board_metadata_path()`,
`kanban_db_path()`, `workspaces_root()`, and `worker_logs_dir()`. Each must equal its
contract path and be contained below the resolved program root; the direct override
variables must remain absent. Existing append/lock files must be regular,
effective-user-owned, mode 0600, and `st_nlink=1`; symlinks, aliases into either
retired root, hardlinks, and special files fail closed. New validators/tests use this
process-envelope shape after v4 is finalized:

```text
/usr/bin/env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin LANG=C.UTF-8 \
  PYTHONDONTWRITEBYTECODE=1 \
  HOME=<v3-test-run>/home \
  SHAY_PROMPT_MEMORY_VAULT=<v3-test-run>/prompt-memory-vault \
  TMPDIR=<v3-test-run>/tmp XDG_CACHE_HOME=<v3-test-run>/xdg-cache \
  PIP_CACHE_DIR=<v3-test-run>/pip-cache UV_CACHE_DIR=<v3-test-run>/uv-cache \
  COVERAGE_FILE=<v3-test-run>/coverage \
  SHAY_HOME=/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3 \
  SHAY_KANBAN_HOME=/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3 \
  SHAY_KANBAN_BOARD=shay-agent-enhancement-2026-09-13 \
  /Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python \
  <authorized-read-only-validator-or-phase-test>
```

The fresh `HOME` and `SHAY_PROMPT_MEMORY_VAULT` directories above are created below
the same disposable phase/profile root before Python starts. The clean environment
means all inherited Kanban variables and `SHAY_HOME` are absent before the command
sets only the values its declared read-only board validation or isolated test profile
requires. Test profiles use their own disposable `SHAY_HOME`, never the active v3
program root shown for the board validator. No process may import Shay, pytest, or a
stress program before those paths are pinned.

The historical initialization command is not rerun. Its exact program/self-check/result
files and hashes are validated read-only and support the existing v3 board truth only.
They do not cure E0008 timing or establish an immutable active environment.

The unsuffixed Python environment/provenance with historical provenance SHA-256
`8a7ae52cd999b8766761d3f1b2e4f557e2fc27e69a0438c38893f1692c124478`
is retired read-only after five pip `__pycache__` files received post-freeze mtimes.
Do not invoke, chmod, repair, delete, or copy it. The active environment is
`/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311`;
it was bootstrapped once from the pinned Python 3.11 base, installed with exact
`.[all,dev]`, checked and frozen under `PYTHONDONTWRITEBYTECODE=1` plus external
cache/TMP paths, provenance-marked, fully manifested, and locked read-only. Every
manifest entry records relative path, type, mode, uid, gid, size, regular-file SHA-256
or symlink target, and nlink. Current work only recomputes the entire manifest and root
digest before and after every review/test and fails on any difference; it never
installs, chmods, repairs, deletes, or otherwise mutates v4.

Both `board.json` and `kanban.db` exist. Require both, reject authoritative `-wal` or
`-shm` sidecars, and hold their common parent plus both leaves by no-follow descriptors
while binding inode/ownership/mode/link/hash before and after the read. Publish exact
mode-0400 copies only below the disposable run root, parse copied metadata, and verify
the exact slug, name, description/program ID, all task keys and fields, and dependency
links. Open only the copied DB with SQLite URI `immutable=1` and `query_only=ON`; fail
on malformed metadata, partial state, duplicate keys, unexpected program metadata, or
link mismatch. Never open the authoritative DB via SQLite and never call
`create_board`, `write_board_metadata`, `init_db`, or `create_task`; missing state is
a blocker, not permission to recreate it.

The initialized active ledger lives at
`/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/evidence/execution-events.jsonl`
with sibling lock `execution-events.lock`. Validate the sequence-1 genesis, full file
prefix SHA-256 `235eb62b238cd2eee3b595e53e77686ab556129ea13066a5f8858f4d21f06422`,
regular-file type, ownership, mode 0600, nlink 1, and path containment read-only. Each
candidate captures the complete current prefix as immutable candidate-local bytes plus
line-count/event-sequence/hash-chain-tip metadata. Later authorized events may extend that
prefix only through the strict schema/transition/hash chain and fsync protocol under the lock;
this never authorizes a Git path or live `~/.shay` path.

The superseded `drive-documents-v1` program root remains where it was created. Its
ledger contains only genesis and has `st_nlink=2` due to a Google Drive temporary
hardlink, so the setup attempt is `blocked` and `retired_read_only`. The unsuffixed
`local-state-v2` program root also remains in place as `invalid_setup` and
`retired_read_only`: its nine exact task refs are frozen in the contract, its board
metadata SHA-256 is `660fc0331e7570a8775385735091b3c9bb7575dbb77ea60258d5fa5e58683cd2`,
and its ledger, initialization summary, and database hashes are the values required
by R0 E0006. Neither task set, link graph, ledger, lock, or setup artifact may be
commented, completed, blocked, archived, deleted, repaired, or opened for write. The
v3 ledger starts a fresh genesis and never copies or hashes either retired genesis
into its chain. The unsuffixed Python environment is separate historical evidence but
is no longer reusable; current nlink 1 does not reactivate it or the v1 ledger.

After setup, a phase uses `add_comment` only on its own task to record start; it does
not fake `running` or call `claim_task`. The repository `kanban_ref` may be `in_progress`
while the actual dependency-controlled task remains `ready`/`todo`. The source
`VALID_STATUSES` set has no `review` value, so after tests and all three reviews the
orchestrator records the exact comment `phase_gate=review candidate_tree_sha=<sha>
diff_sha256=<sha256>` and requires the task to remain in its dependency-derived
nonterminal `ready` status; `todo` or any other status blocks commit. Evidence may
justify `block_task`. `complete_task` is permitted only after the reviewed
implementation commit exists and `git ls-remote` proves the exact feature-branch
remote SHA equals it; a commit or push failure leaves the task non-done. The R2
reconciler process only reads the exact database, external ledger, canonical trace,
and exact phase evidence; a separate orchestrator may append its reconciliation event
or comment/complete R2 after validating output. After completion read-back, append
`kanban_completed` only externally. R8 reads all tasks and builds a redacted
pre-candidate snapshot/hash in its in-repository evidence/status files; it may update
only R8. Board state cannot substitute for repository verification, external review,
remote equality, or merge approval.

Only requirement/branch/commit/test/review metadata and redacted errors may be
stored. Credentials, customer data, messages, production IDs, voice/persona content,
and owner profile data are forbidden. Never delete or archive any program board
automatically; retain both retired attempts read-only and the active v3 state for owner handoff. These
exact external operational writes are not Git `changed_paths` and do not expand
repository evidence or code-diff allowlists. The ban on
`/Users/famtastic-fritz/.shay/**` remains absolute for this program.

## 8. Global guardrails for every implementation phase

- [ ] Fetch `origin/main` before every phase and verify its current tip has not
  invalidated the pinned source facts, protected hashes, path manifest, or reviewed
  dependency tip. Treat this as a drift check, not as the branch ancestry.
- [ ] Base each dependent phase in an isolated worktree on its reviewed dependency
  tip and record that actual tip SHA. Integrate only the separately listed reviewed
  dependency commits, then record the resulting pre-edit HEAD. Do not merge or rebase
  `origin/main` into the dependency branch without separate merge authority.
- [ ] Stop if the target worktree is dirty or if another agent is editing an
  overlapping path.
- [ ] Before bootstrap, tests, or authored changes, capture the full raw NUL-delimited
  `git status --ignored=matching --porcelain=v1 -z` bytes for audit; extract its
  `!! ` records without newline parsing and hash that ordered NUL stream. Also build a
  sorted NUL manifest of every file from
  `git ls-files --others --ignored --exclude-standard -z` with type, mode, size, and
  file-byte or symlink-target SHA-256. Store both outside the repository. Repeat
  before review and commit. Nonignored status may change only within the phase
  allowlist; the ignored-record digest and per-file manifest must equal the entry
  baseline. Any ignored-path addition, removal, or byte/metadata change fails closed.
  The default allowed ignored-artifact set is empty.
- [ ] Create one branch per capability; never implement directly on `main`.
- [ ] Create an allowed-path manifest before edits. Treat every unlisted path as
  read-only.
- [ ] Make the exact phase-local evidence JSONL the first authored change for R1-R8
  and append only pre-review facts through verification; never overwrite, sort, or
  delete prior events. R0's explicit exception records its actual base before external
  setup, then board links and verification before candidate construction.
- [ ] Resolve the phase's program-board task by its exact idempotency key; require it
  to exist with the expected links before claiming completion. R2 remains read-only.
- [ ] At entry and exit, verify `SHAY-PROTECTED-CUSTOM-BASELINE-v1` from the
  capability contract, including the SHA-256 values for `PERSONA.md`, `SOUL.md`, and
  `docker/SOUL.md`; any mismatch blocks the phase.
- [ ] Record forbidden paths, including persona/identity, voice, filming, credentials,
  live `~/.shay`, and unrelated custom plugins/skills.
- [ ] For every process/test profile, start from a scrubbed environment and create one
  disposable phase/profile root below the exact external test-run root. Before any
  Shay, pytest, stress, or plugin import, unset `HOME`, `SHAY_HOME`,
  `SHAY_PROMPT_MEMORY_VAULT`, `SHAY_KANBAN_HOME`, `SHAY_KANBAN_DB`,
  `SHAY_KANBAN_WORKSPACES_ROOT`, and `SHAY_KANBAN_BOARD`; then set `HOME`, `SHAY_HOME`,
  and `SHAY_PROMPT_MEMORY_VAULT` to three distinct descendants of that root. Repeat
  with a second distinct profile root and prove neither profile can read or write the
  other's home, Shay home, prompt-memory vault, Kanban database, caches, or artifacts.
- [ ] Before the first isolated import and after the last stress subprocess, compare
  byte-identical external sorted-NUL sentinels for every existing owner-profile path
  below `/Users/famtastic-fritz/.shay`, recording relative path, type, mode, size,
  `mtime_ns`, and regular-file or symlink-target SHA-256 but never file contents. Any
  path, hash, or mtime change fails the phase.
- [ ] For every test process set `PYTHONDONTWRITEBYTECODE=1`, use pytest
  `-p no:cacheprovider`, and direct `TMPDIR`, `XDG_CACHE_HOME`, `PIP_CACHE_DIR`,
  `UV_CACHE_DIR`, `COVERAGE_FILE`, logs, databases, and scratch evidence below the
  external test-run root. Never create a venv, cache, temp file, proof file, or test
  database inside the repository.
- [ ] Use only the immutable v4 Python environment. Recompute its complete lstat-based
  file/directory/symlink manifest and root digest immediately before and after every
  review and every test command. Require exact byte equality with the E0010/E0011
  pinned manifest, regular-file nlink 1, no special files, and no writable regular
  file or directory. Never invoke pip without the full no-bytecode/external-cache
  envelope; any manifest drift fails closed.
- [ ] Prefer Shay's plugin hooks or existing registries before editing core.
- [ ] Preserve the old reader/path behind a disabled-safe compatibility flag until
  parity and rollback are proven.
- [ ] Do not stage broadly. Stage only explicit reviewed pathspecs.
- [ ] Run focused tests, the canonical full wrapper, explicit E2E, stress tests, and
  diff checks in the order specified by the phase.
- [ ] Capture exact commands, exit codes, versions, timestamps, assertions, artifact
  hashes, and any skipped or blocked proof.
- [ ] Run an independent anti-pattern review and a separate code-quality review.
- [ ] Before review, inventory the complete worktree with
  `git diff --name-status -z --find-renames integration_base_sha..HEAD`,
  `git diff --cached --name-status -z --find-renames`,
  `git diff --name-status -z --find-renames`,
  `git ls-files --others --exclude-standard -z`,
  `git status --ignored=matching --porcelain=v1 -z`, and
  `git submodule status --recursive`. Validate every committed, staged, unstaged,
  untracked, rename/copy source and destination, and submodule path against the
  current phase allowlist. Validate inherited
  `planning_anchor_sha..integration_base_sha` changes separately against the union
  of all transitively reachable reviewed primary and integrated dependency manifests.
- [ ] Populate schema-v5 `dependency_commits` only from completed accepted-C ledger
  events. Prove with Git object and merge-base ancestry that `implementation_base_sha`
  equals the primary C and every required primary/parallel C is contained in
  `integration_base_sha`; R5, R6, and R8 fail if either parent is omitted.
- [ ] Bind `phase_contract` to the exact integration-base blobs for the frozen plan,
  capability contract, and canonical trace plus the requirement's exact allowlist,
  evidence path, current event, tests, and protected manifest. For R1-R8, recompute
  authored blobs from candidate Git objects (including both rename endpoints), parse
  and compare the complete category inventory and recursive submodule bytes, revalidate
  v4 provenance, and parse the phase-local JSONL from the exact next
  `implementation_started` through a captured passing `verification`. Never substitute
  the R0-only four-document validator for these later-phase checks.
- [ ] Require `HEAD == integration_base_sha` and a clean real index. Build the review
  candidate with one disposable `GIT_INDEX_FILE` outside the repository, seed it using
  `git read-tree HEAD`, stage only every changed allowlisted authored path with
  `git add -A -- <exact-paths>` (including deletions and both validated rename sides),
  and first record `git write-tree` as `candidate_tree_sha`. Next copy the closed build
  index to a newly created authoritative `candidate-index` below the external candidate
  directory with exact mode 0400, effective uid/gid, and nlink 1; bind its normalized
  path, SHA-256, mode, uid, gid, and nlink. Then derive the canonical authored-file blob
  manifest from `candidate_tree_sha`; only afterward complete the binding with the full
  diff and non-tree artifacts. Store below the external candidate-binding root exact hashed artifacts/refs for the
  category-sensitive pre-stage worktree inventory, ignored-state
  baseline/current plus per-file manifests, live-profile sentinel before/after,
  recursive submodule state, v4 environment provenance, complete environment manifest,
  environment root digest, immutable execution-ledger prefix/anchor, and content-bearing
  research snapshots/manifest. The complete live-profile manifests are captured only before
  and after candidate construction; routine reviewers validate those immutable temporal files
  without rehashing current `~/.shay`. All three separately dispatched reviewers copy the stored index
  to private disposable mode-0600 files, point Git only at those copies, prove the
  stored index unchanged, and emit standalone immutable results with a byte-identical complete
  binding. A separate recorder validates all three and appends their exact artifact-bound
  projections. Any candidate byte, stored-index byte/metadata, referenced immutable artifact,
  submodule, ignored state, bound live temporal sentinel,
  environment binding, or allowlist mutation invalidates all three reviews.
- [ ] The commit agent starts with the still-clean real index and must establish exactly
  the final authorized staged path/tree transition for `<exact-reviewed-pathspecs>`;
  the evidence does not claim how many `git add` invocations occurred. Post-stage categories and
  the real index-file hash are expected to differ from pre-stage and are not compared
  for equality. Require instead that real-index `git write-tree`, the staged full-diff
  digest, and the authored blob manifest equal all three review bindings; stable
  ignored/live/submodule/environment refs and hashes remain equal; no authored path is
  left unstaged/untracked; and no unlisted path is present. Capture the post-stage
  category-sensitive inventory shape/hash as commit evidence. The stored candidate-index
  is never copied into or compared byte-for-byte with the real index and must remain
  unchanged. Mismatch aborts and requires a fresh clean-index candidate plus all three reviews.
  The single C tree must equal `candidate_tree_sha`; append reviews, C, verified push,
  and task completion only to the external ledger.
- [ ] Commit and push only a verified feature branch using explicit reviewed
  pathspecs, leaving C as the permanent local/remote/dependency program tip.
  Opening a PR, merging, releasing, enabling live behavior, changing
  credentials, taking destructive action, or changing production remains separate.
- [ ] After commit/push require `git status --porcelain=v2 --untracked-files=all` to
  be empty and require `git rev-parse HEAD` to equal the SHA returned by
  `git ls-remote origin refs/heads/<exact-branch>`. Only after that equality may the
  task become done and external `kanban_completed` append.
- [ ] Before any later owner-authorized squash merge, refresh `origin/main`, verify
  it has not invalidated the stack, and compare the dependency-tip diff for unrelated
  reversions. Do not perform that merge/rebase step under this implementation-only
  approval.

## 9. Phase 0 — Documentation discovery and custom-capability freeze

Goal: establish what Shay already does so researched patterns cannot become duplicate
systems or overwrite custom behavior.

### Discovery checklist

- [x] Read `AGENTS.md` and record its testing, plugin, prompt-cache, profile, TUI,
  and merge-safety rules.
- [x] Run the research preflight. Verdict: `partially researched`.
- [x] Review the current broader-research note and prior anti-drift/architecture
  notes before adding new conclusions.
- [x] Dispatch independent read-only capability, E2E, and plugin/skill discovery
  lanes with mandatory evidence contracts.
- [x] Create `docs/architecture/shay-custom-capability-contract.yaml` containing
  each capability, owning files/APIs, side effects, current tests, and preservation
  requirement.
- [x] Create `docs/architecture/shay-agent-enhancement-trace.jsonl` using the trace
  record above.
- [x] Create line-labelled current-state diagrams for task lifecycle, tool policy,
  memory writes, and the four client adapters.
- [x] Mark every roadmap item as `already exists`, `partial`, `absent`, or
  `not runtime-proven`.
- [x] Identify exact allowed files for Phase 1 and explicitly deny all others.

### Documentation references

- `AGENTS.md`
- `docs/research-artifact-capture-protocol.md`
- `scripts/research_preflight.py`
- `docs/plans/2026-06-19-shay-intelligence-control-plane-brief.md`
- `docs/plans/intelligence-autonomy-hyperswarm-plan-2026-07-02.md`
- the source-confirmed APIs listed in Sections 5 and 6

### Verification

- [x] Every capability row cites at least one exact source location and one existing
  test or an explicit `unproven` marker.
- [x] Every proposed change has exactly one existing owner or a written ownership
  decision; no parallel databases, registries, or chat surfaces appear.
- [x] `git diff --check` passes and only Phase 0 documentation artifacts changed.
  The active v3 ledger/board and E0006/E0007/E0004 relinks already exist and are
  validated read-only. Immutable v4 and E0009/E0010/E0011 satisfy the repository
  verification prerequisites; the fresh closed-procedure R0 candidate is pending exactly three external
  candidate-bound reviews.

### Anti-pattern guards

- [x] Reject plans based only on README claims or NotebookLM summaries.
- [x] Reject `greenfield` designs for capabilities Shay already owns.
- [x] Reject blanket replacements of textual `~/.shay`; distinguish user-facing
  examples, diagnostics, default-root behavior, and true profile-path defects.
- [x] Implementation is approved by the 2026-09-13 user directive quoted above;
  this does not supply merge approval.

Current Phase 0 evidence: the drift-checked actual base remains
`cf6bb95e3dc12e0d4b8eadef2c33be2b39ad21b6`. The first setup attempt,
`drive-documents-v1`, created an external environment, a genesis-only execution ledger,
and nine linked board tasks, but its ledger was observed with `st_nlink=2` because of a
Google Drive temporary hardlink. That historical failure violated the required single-link preflight, so
the entire v1 attempt is blocked and retired read-only; it is not Phase 0 success.
Any later nlink 1 observation does not reactivate it.

The second setup attempt, `local-state-v2`, created an external Python 3.11
environment/provenance plus a genesis ledger and nine internally linked board tasks.
Its initialization program stripped the literal `R`, however, so the task keys are
`:0` through `:8`. The v2 program state is therefore `invalid_setup` and
`retired_read_only`; its tasks/ledger are not execution authority and will not be
repaired in place. Its unsuffixed environment is now also retired read-only because
five pip `__pycache__` files have post-freeze mtimes. The exact 29 repository rows
already written for v1/v2 remain byte-for-byte
immutable at full SHA-256
`4cfe0dcfc84051f3f02fa721e0b87fbbb19c859442f816cd8741f5ffbaeffa9f`.

The active `non-synced-v3` setup is now initialized pre-review at
`/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3`.
R0 E0006 `setup_blocked`, the hashed external initialization program/unit self-check,
v3 ledger/board, nine exact `:R0` through `:R8` relinks, and historical E0008 are
present and read back. The 40 exact trace rows remain immutable at SHA-256
`cdd456f0deddf68134554c8acfbb4116a98b6cf68cea941b4d14b1bcacbe0c1f`.
E0008's execution timing is invalid, so it is not an active verification PASS. The
immutable v4 environment is finalized and E0009/E0010/E0011 supersede E0008 with
captured verification evidence. Every inactive candidate named by the last candidate-selection registry row's exact
`supersedes` set is invalidated, unreviewed history. The registry, rather than static
Git documentation, is the complete inactive-directory inventory and avoids a
self-referential tree. The fresh current candidate binds its stored index and closed
review procedure and is pending three external reviews. Candidate construction derives every
published artifact path in memory and writes the final destination-bound JSON bytes once, before
metadata/procedure hashes are closed; it never rewrites a staged candidate leaf, and any retained-authority
directory or remaining staging prefix fails before sealing. Phase 1 may start only after all three R0
reviews pass, exactly one R0 C is committed, origin is verified at C, the R0 board task
is done/read back, and external `kanban_completed` records that chain;
merge approval remains separate and null.

## 10. Phase 1 — Repair the baseline and create a real E2E gate

Goal: make the pre-enhancement baseline trustworthy before changing architecture.

### Environment and harness checklist

- [ ] First authored path:
  `docs/architecture/evidence/shay-agent-r1-events.jsonl`; append only under the
  global phase-local evidence contract.
- [ ] Make the committed runner portable: `scripts/run_tests.sh --e2e` requires both
  `SHAY_TEST_PYTHON` and `SHAY_TEST_ENV_PROVENANCE` as caller-supplied absolute paths.
  It resolves and validates an executable Python 3.11 interpreter plus a strict,
  effective-user-owned, single-link provenance file proving editable `.[all,dev]`, a
  successful dependency check, the current `pyproject.toml` hash, and any applicable
  lock hashes. It rejects a Python environment or provenance file inside the Git
  checkout, below the real user home at `.shay`, at either retired environment path,
  or reached through an undeclared fallback. It never selects `.venv`, `venv`, or a
  live Shay venv in E2E mode and never installs or repairs dependencies.
- [ ] In this local orchestration only, pass
  `SHAY_TEST_PYTHON=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/bin/python`
  and
  `SHAY_TEST_ENV_PROVENANCE=/Users/famtastic-fritz/.local/share/shay-agent-enhancement-2026-09-13-v4/python311/shay-agent-environment-provenance.json`.
  The orchestrator separately brackets every command with the pinned v4 complete
  manifest/root-digest verifier. These machine-specific paths and hashes are local
  evidence, not literals that the committed runner requires on another machine.
- [ ] Remove the wrapper's auto-install behavior for program/E2E mode. A missing
  package is a failed preflight; the wrapper never installs or repairs packages in any
  environment.
- [ ] Record Python, Node, package-manager, OS, architecture, and dependency-lock
  hashes in the evidence bundle.
- [ ] Repair only the observed UI rename damage: in `ui-tui/package-lock.json`, restore
  the authoritative `hermes-parser` and `hermes-estree` 0.25.1 dependency names, package
  keys, registry URLs, and unchanged npm integrity values; require both React ESLint
  plugins to depend on `hermes-parser`, and leave no `shay-parser` or `shay-estree` key.
- [ ] Restore valid `launchShayCommand` and `resolveShayBin` identifiers in
  `ui-tui/src/lib/externalCli.ts` and its setup caller, preserving the existing `SHAY_BIN`
  override and default `shay` executable behavior. Add the focused
  `ui-tui/src/__tests__/externalCli.test.ts` regression without broad TUI refactoring.
- [ ] In an external disposable Git-tree copy with external HOME/npm cache, pinned fnm
  1.39.0, Node 24.19.0, npm 11.17.0, and lockfileVersion 3, prove clean-registry `npm ci`,
  `npm run type-check`, and `npm test -- src/__tests__/externalCli.test.ts` all pass.
  Repository `ui-tui/node_modules` and ignored state must remain byte-identical.
- [ ] Repair the missing `Path` import in
  `tests/stress/test_subprocess_e2e.py` and prove the real subprocess lifecycle runs.
- [ ] Repair the stale `spawn_failures` test reference without weakening the current
  `consecutive_failures` contract.
- [ ] Make the minimum fresh-database idempotency repair in `create_task(...)`: the
  active-key lookup and insertion must be transactionally race-safe so at least five
  concurrent creators return one task ID and leave one non-archived row.
- [ ] Keep that repair narrow. Do not reconcile historical duplicates, add a legacy
  migration, define service/API idempotency, or claim restart durability in R1; those
  are R3 responsibilities.
- [ ] Decide and document archived-parent dependency semantics, then make creation,
  recompute, claim, and tests agree in the narrowly owned ADR
  `docs/architecture/adr-shay-archived-parent-semantics.md`.
- [ ] Add an explicit E2E mode to `scripts/run_tests.sh`; the default focused/unit
  behavior must remain compatible.
- [ ] Define `scripts/run_tests.sh --e2e [additional pytest paths or flags]`
  exactly: require the two absolute environment variables above, validate the portable
  provenance and hermetic environment before importing pytest or Shay; run pytest for
  `tests/e2e/test_shay_baseline_e2e.py` plus any supplied paths without the default
  integration/E2E exclusions; then run
  `tests/stress/test_concurrency.py`, `tests/stress/test_subprocess_e2e.py`, and
  `tests/stress/test_atypical_scenarios.py` as standalone Python programs through
  their `main()` entry points; fail on the first nonzero command.
- [ ] Update `.github/workflows/tests.yml` so pushes to `main` and
  `codex/shay-agent-*`, existing pull requests to `main`, and optional
  `workflow_dispatch` all run the appropriate gates. Under `$RUNNER_TEMP`, CI creates
  a fresh Python 3.11 environment from the checkout's `pyproject.toml` and dependency
  lock inputs, installs exact `.[all,dev]`, runs the dependency check, writes a strict
  provenance marker and external disposable HOME/SHAY_HOME/prompt-vault roots, then
  passes `SHAY_TEST_PYTHON` and `SHAY_TEST_ENV_PROVENANCE` to the same committed
  `scripts/run_tests.sh --e2e` command. CI never relies on a developer-machine v4 path.
- [ ] The feature-branch push is already authorized and its successful branch `test`
  and `e2e` checks satisfy the CI phase gate. Creating a PR is an optional later owner-
  authorized handoff; PR creation, PR review, and merge are not Phase 1 completion
  requirements and are not performed under implementation-only authority.

### Phase-local baseline proof contract

- [ ] Add an explicit baseline/E2E mode to `scripts/run_tests.sh`; reserve
  `scripts/run_shay_upgrade_proof.sh` and common evidence integration for serialized
  R8 after R3-R7 are reviewed.
- [ ] Write phase-local R1 evidence under its declared repository path plus temporary
  test outputs below
  `/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/test-runs`,
  never live profile state; require every invoked baseline command to exit 0.
- [ ] Record base SHA, dirty state, commands, exit codes, timestamps, environment,
  test counts, skipped tests, and artifact hashes only for the R1 wrapper, complete
  E2E/stress execution, live-profile isolation, archived-parent semantics, and the
  narrow fresh-database idempotency fix.
- [ ] Run two profile envelopes. Each begins from scrubbed `HOME`, `SHAY_HOME`,
  `SHAY_PROMPT_MEMORY_VAULT`, and all four Kanban override variables, then pins a fresh
  HOME, Shay home, and prompt-memory vault below only that profile's external test
  root before Python imports anything. Fixtures assert no owner-home/live-vault read or
  write, no path escape, and no cross-profile database, memory, vault, cache, log, or
  artifact spillover.
- [ ] Do not emit lifecycle, safety, memory, protocol, or CLI-upgrade `PASS:` markers
  and do not create
  `docs/architecture/evidence/shay-agent-upgrade-evidence.json` in R1. Those
  assertions and that artifact belong only to R8 after R3-R7 are reviewed.

### Verification

- [ ] `scripts/run_tests.sh tests/<focused-path>` passes.
- [ ] `scripts/run_tests.sh` passes.
- [ ] The new explicit E2E mode passes.
- [ ] The Phase 1 hermetic Node baseline gate passes clean-registry `npm ci`, typecheck,
  and the focused external-cli test after proving the repaired hermes lock graph and
  valid launcher identifiers; cached reconstruction of the current broken graph is not
  accepted.
- [ ] `scripts/run_tests.sh --e2e` passes and proves all three standalone stress
  programs were invoked; do not pass their files to pytest.
- [ ] The original atypical concurrent-idempotency scenario passes without a skip,
  warning conversion, or relaxed assertion; a focused fresh-database regression also
  proves five same-key writers produce one ID/row and two distinct keys produce two.
- [ ] Two distinct temporary `SHAY_HOME` runs produce no writes to the owner's live
  profile, and the before/after live-profile path/hash/mtime sentinel manifests are
  byte-identical.
- [ ] The phase-start, pre-review, and pre-commit ignored-path status/file manifests
  are byte-identical, with no new or modified ignored repository artifact.
- [ ] GitHub Actions `test` and `e2e` jobs pass on the pushed feature branch without
  requiring a PR. If a PR is later owner-authorized, its duplicate checks may also
  pass but are not the authority for this phase completion.

### Anti-pattern guards

- [ ] Do not delete failing scenarios, convert assertions into warnings, or classify
  missing dependencies as passing tests.
- [ ] Do not add brittle catalog/version/count snapshots; test behavioral invariants.

Exit evidence: honest phase-local R1 results for the baseline wrapper, full E2E/stress
execution, the minimal fresh-database race fix, and archived-parent semantics. This
is a prerequisite for, not a substitute for, R8's capability proof.

## 11. Phase 2 — Enforce the anti-drift trace graph

Goal: prevent a researched recommendation or approved plan from silently losing its
task, pre-review evidence, external review/commit/push proof, or completion.

### Checklist

- [ ] First authored path:
  `docs/architecture/evidence/shay-agent-r2-events.jsonl`; append only under the
  global phase-local evidence contract.
- [ ] Reconcile the 2026-05-31 anti-drift design with current Kanban schemas before
  coding; do not assume those older paths or statuses remain current.
- [ ] Keep one append-only in-repository pre-review trace plus the single exact
  append-only external execution ledger; never duplicate an authority.
- [ ] Link `recommendation → plan → Kanban task → repository verification → external
  review → implementation commit C → verified remote C → Kanban completion`.
- [ ] Derive completion from terminal task state plus verified artifacts; never
  store an unsupported `done` label.
- [ ] Detect at minimum:
  - approved plan with no implementing task;
  - recommendation with no plan/task;
  - task marked complete without evidence;
  - build evidence attached to a stale non-terminal task;
  - changed file not listed in the phase manifest;
  - implementation requirement with no regression test;
  - stale branch that would revert newer `main` changes.
- [ ] Produce a read-only human report and machine-readable result with nonzero exit
  on material drift.
- [ ] Under a shared ledger lock, verify JSONL hash chain/schema/transitions,
  byte-identical three-review candidate/non-tree bindings, commit-tree equality,
  remote equality, task read-back, and the reviewed dependency tip used by each child.
- [ ] Keep heuristic links as suggestions requiring confirmation; do not mutate task
  status from fuzzy matching.
- [ ] Expose and prove only the read-only reconciler gate in R2. Defer canonical
  common-proof and PR-checklist integration to serialized R8, which owns those paths.

### Verification

- [ ] Fixture: every healthy chain is accepted.
- [ ] Fixture: each orphan class fails independently with the expected requirement ID.
- [ ] Fixture: rerunning the reconciler is idempotent.
- [ ] Fixture: heuristic links never auto-complete or rewrite a task.
- [ ] Fixture: an unrelated user-modified file is reported and left untouched.

### Rollback

- [ ] Both ledgers are additive/exportable within their distinct fact boundaries;
  disabling enforcement deletes or rewrites neither.
- [ ] Disabling enforcement leaves a read-only warning mode; it does not delete
  history or alter task state.

Exit evidence: every requirement has a queryable repository pre-review chain and,
where it progressed, a matching external execution chain, or an honest blocked/proposed
state.

## 12. Phase 3 — Harden the existing durable task/run lifecycle

Goal: extend Shay's Kanban ledger rather than introduce another task database.

### Architecture decision checklist

- [ ] Write an ADR naming responsibilities:
  - `SessionDB` owns conversations/messages;
  - Kanban owns durable tasks, runs, events, claims, retry, and terminal state;
  - cron owns schedules, not task truth;
  - `ProcessRegistry` owns live process handles, not durable completion truth;
  - batch checkpoints remain batch-specific;
  - API/TUI/ACP/CLI are adapters over the same domain state.
- [ ] Confirm that this ownership model does not break existing `/background`, goal,
  gateway, or batch behavior before implementation.
- [ ] Keep `gateway/platforms/api_server.py` in the R3 packet so the durable service
  can replace process-memory `/v1/runs` authority behind a compatibility flag;
  reserve the broader four-client domain mapping for serialized R6.

### Idempotency and event checklist

- [ ] Preserve R1's fresh-database transactional behavior and rerun its original
  atypical plus focused same-key/different-key tests unchanged; do not introduce a
  second idempotency path or weaken the one-ID/one-row assertion.
- [ ] Detect historical active-key duplicates, choose a deterministic canonical row,
  and preserve every noncanonical row for audit; never discard user records silently.
- [ ] Add an additive migration and durable uniqueness/enforcement strategy only
  after that historical reconciliation policy is documented and tested.
- [ ] Expose and prove the existing monotonic `task_events.id` as the durable replay
  sequence; do not add a parallel event-sequence column unless an ADR proves the
  existing ID cannot satisfy a measured contract.
- [ ] Make terminal transitions single-writer and idempotent.
- [ ] Record reason, actor/client, task/run/session IDs, timestamps, and retry lineage.
- [ ] Make stop/cancel durable, terminal, single-writer, and idempotent. R3 must prove
  that status/events survive worker and gateway restart, that recovery never changes a
  cancelled run to completed, and that no new dispatch is scheduled from cancelled
  state. Because R3 does not yet contain R4's effect ledger/interception, the stronger
  claim that no in-flight or nested tool effect occurs after cancellation is reserved
  for the R8 composed proof.
- [ ] Persist approval-wait state without persisting secrets.

### API adapter checklist

- [ ] Replace process-memory `/v1/runs` authority with a feature-flagged adapter over
  the existing durable ledger.
- [ ] Keep event delivery replayable from a cursor and deduplicate reconnects.
- [ ] Preserve the legacy API reader for one compatibility window.
- [ ] On restart, report recovered, failed, cancelled, or waiting honestly; never
  synthesize completion.

### Required tests

- [ ] Five concurrent creates with one idempotency key return one task ID and one row.
- [ ] A legacy fixture with duplicate active keys migrates without record loss;
  repeated reconciliation is idempotent and old/new readers resolve the same
  canonical ID.
- [ ] Repeating one service/API request before and after restart creates no additional
  task, run, or event transition.
- [ ] Claim, retry, approval wait, deny, cancel, complete, and fail each produce one
  authoritative transition.
- [ ] Kill a worker mid-tool and recover to an explicit `interrupted`/`uncertain` or
  retry-required state without false completion or duplicate task/run/event
  transitions. R3 does not claim that an unknown external effect executed exactly
  once.
- [ ] Kill the gateway and prove API status/events survive and replay.
- [ ] Call stop repeatedly and prove idempotent terminal behavior.
- [ ] Run old and new readers against the additive schema.
- [ ] Before either R3 or R4 candidate freeze, pass the shared R3+R4 composed-tree
  compatibility barrier: approval wait survives restart; deny/cancel remains terminal;
  a cancelled run cannot schedule a new dispatch; and the exact tool-issued receipt
  binds both tested-tree SHAs, the common R2 base, composed-tree SHA, argv, exit, and
  result artifacts. This is compatibility evidence, not R3 external-effect exactly-once
  proof.

### Rollback

- [ ] Copy the pre-migration database before migration in tests/canary.
- [ ] The feature flag restores the legacy API adapter without downgrading or deleting
  ledger data.

Exit evidence: R3 records only phase-local lifecycle/restart results in
`docs/architecture/evidence/shay-agent-r3-events.jsonl`. It does not run the common
proof runner or create the canonical R8 evidence artifact.

## 13. Phase 4 — Add deterministic cross-tool safety as a plugin-first layer

Goal: extend current shell-focused approval protection to typed external side effects
without scattering policy through tools.

### Plugin checklist

- [ ] Start from the truthful current seam: `pre_tool_call` recognizes only
  `{"action": "block"}`; no block means dispatch continues, `PluginManager` swallows
  callback exceptions, and `model_tools.py`/`run_agent.py` swallow hook-dispatch
  exceptions. Do not call this an interactive approval API.
- [ ] Prototype a bundled plugin using `PluginContext.register_hook(...)` and
  `get_pre_tool_call_block_message(...)` for deterministic allow/block policy; do not
  patch each concrete tool.
- [ ] Because the required matrix includes typed interactive approval, add a generic,
  plugin-neutral approval extension across exactly `shay_cli/plugins.py`,
  `model_tools.py`, `run_agent.py`, and `tools/approval.py`. It must resolve
  allow/block/request-approval once, route through existing client approval
  machinery, fail closed on timeout or hook failure, and preserve terminal hardline
  denial. The safety plugin may consume this extension; no plugin-only prompt path is
  acceptable.
- [ ] In the concurrent executor, parse and completely resolve the typed
  `pre_tool_call` decision **before** `CheckpointManager.ensure_checkpoint`, any
  checkpoint ref/object write, process registration, agent-level interception, or
  tool dispatch. A deny/block/timeout/hook error must return the synthetic failure
  with zero checkpoint, ref, process, handler, or external-effect side effects. Only
  an allowed call may cross into checkpoint/ref creation. Keep the already policy-
  before-checkpoint sequential order and its behavior unchanged.
- [ ] Define versioned effect classes: read, local reversible write, destructive local
  write, credential/account, external message/publish, payment/spend, and production.
- [ ] Define rule IDs and task-scoped allowed filesystem roots.
- [ ] Resolve symlinks before path authorization.
- [ ] Preserve hardline command denials in host-capable environments regardless of
  policy mode or YOLO state. Keep the current Docker, Singularity, Modal, Daytona,
  and Vercel Sandbox bypasses explicit; prove their containment in separate
  backend-isolation tests rather than applying host hardline assertions to them.
- [ ] Add retry ceilings, duplicate-effect keys, and no-progress hard stops.
- [ ] Make durable `tool_call_id` and `effect_id` keys authoritative for external
  effect deduplication. This R4 ledger, not R3 task/run idempotency, owns the
  exactly-once synthetic external-effect guarantee across retry and restart.
- [ ] Treat `execute_code` and every environment/composite backend as a parent effect.
  Before dispatch, enumerate and persist a stable child `tool_call_id`/`effect_id` for
  every nested effect, bind each child to its parent and ordered request digest, and run
  normal policy/deduplication for each child. If a backend cannot enumerate stable child
  IDs before the first effect, deny the parent before dispatch; a nested effect may not
  inherit an unbounded blanket approval.
- [ ] Add preflight and runtime USD ceilings using provider-reported usage when
  available; report `unknown`, never an estimate presented as authority. The bounded
  unknown-cost rule is fail closed: a cost-bearing call without an authoritative
  provider maximum or a maximum encoded in the request and authoritatively enforced
  by the provider at or below the
  remaining ceiling is denied before dispatch as `cost_unknown`; missing authoritative
  actual usage after an admitted call marks cost unknown and blocks every later
  cost-bearing call in that task/run until reconciled. Reads and local operations may
  proceed only when their effect class declares them non-spend.
- [ ] Write append-only decisions with rule ID, client, session, task/run, tool call,
  requested effect, outcome, and timestamp; never log secrets.
- [ ] Plugin disabled must reproduce the pre-phase behavior except that existing
  hardline protections remain active.

### Required tests

- [ ] `tests/shay_cli/test_plugins.py`: structured typed directives, legacy block
  compatibility, invalid return rejection, and callback-exception fail-closed mode.
- [ ] `tests/test_model_tools.py`: one policy resolution per core-dispatched tool,
  no dispatch after block/deny/timeout, and no double hook firing.
- [ ] `tests/run_agent/test_run_agent.py`: the same behavior for agent-level plus
  sequential and concurrent tool paths. A phase-local concurrent-denial fixture must
  snapshot checkpoint refs/objects, ProcessRegistry state, dispatch counters, and the
  fake external-effect counter before/after and prove all remain unchanged.
- [ ] `tests/tools/test_approval.py`: generic typed request/allow/deny/timeout flow
  while hardline commands remain unconditionally blocked on local, SSH, and other
  host-capable backends.
- [ ] Dedicated isolation fixtures for `docker`, `singularity`, `modal`, `daytona`,
  and `vercel_sandbox` prove that effects cannot escape their declared boundary;
  these tests do not assert host-level hardline interception.
- [ ] Filesystem escape, symlink traversal, sensitive path, and hardline shell cases.
- [ ] Approval timeout/failure always denies across CLI, TUI, API, and ACP.
- [ ] Concurrent approval sessions do not leak permission.
- [ ] Fake external-effect counter executes exactly once across retry, reconnect,
  and restart.
- [ ] `execute_code` and every composite/environment backend either persists stable,
  ordered parent/child effect IDs before dispatch and deduplicates every child, or
  fails closed with zero child effects; retries cannot mint new child identities.
- [ ] Budget refuses before the configured ceiling is exceeded.
- [ ] Unknown preflight maximum denies before dispatch, and missing post-call actual
  usage prevents any later cost-bearing call; neither path reports unknown as zero.
- [ ] Audit rows are complete, ordered, redacted, and replayable.
- [ ] Before either R3 or R4 candidate freeze, pass and bind the same R3+R4
  compatibility-barrier receipt described in Phase 3. Any input-tree change invalidates
  both candidates' receipt closure.

### Anti-pattern guards

- [ ] No prompt-only safety rules.
- [ ] No broad permanent allowlist created by tests or setup.
- [ ] No live payment, message, publish, credential, or production calls in proof.
- [ ] No plugin-specific branch added to core if a generic hook is sufficient.

Exit evidence: the same synthetic policy matrix passes through every client adapter.

## 14. Phase 5 — Add versioned memory provenance and promotion

Goal: borrow Letta/MemFS provenance patterns without replacing Shay's built-in memory
or identity.

### Schema checklist

- [ ] Establish a versioned provenance envelope containing:
  `schema_version`, `content_hash`, `write_origin`, `source`, `session_id`,
  `parent_session_id`, `tool_call_id`, `task_id`, `created_at`, confidence,
  and `supersedes_or_tombstones`.
- [ ] Keep raw evidence immutable and represent corrections as superseding records.
- [ ] Separate working context, candidate durable memory, curated durable memory,
  and protected identity/persona.
- [ ] Implement only candidate-to-curated ordinary-memory promotion through the public
  `MemoryStore.promote_candidate(record_id, decision_id)` operation, requiring a
  same-profile, exact-record, single-use
  owner-review decision. Ordinary writes, recall, restarts, confidence, repetition,
  model output, and external-provider mirrors never auto-promote. Identity/persona and
  high-impact standing-rule promotion remains intentionally unavailable and fails
  closed in R5; `PERSONA.md`, `SOUL.md`, and `docker/SOUL.md` remain byte-identical.
- [ ] Begin with existing file/SQLite/git conventions; do not add a vector database
  without a measured retrieval failure and benchmark.
- [ ] Preserve the actual ownership split: `run_agent.py` instantiates the built-in
  `MemoryStore` directly, while `MemoryManager` is instantiated only for a configured
  external provider and does not contain the built-in store.
- [ ] Base R5 on the reviewed R4 tip so its `run_agent.py` work inherits the generic
  typed-policy seam. Wire the reviewed provenance envelope through the real
  `run_agent.py` built-in `MemoryStore` construction and write path; provider-only
  tests are insufficient evidence for built-in memory.
- [ ] Use built-in `MemoryStore` write APIs for the authoritative file path and
  `MemoryProvider.on_memory_write(...)` plus manager lifecycle hooks only for the
  configured external-provider path and its current mirror bridge.
- [ ] Keep recall additions in the cache-safe per-turn/user-message path.

### Required tests

- [ ] A real agent memory write persists the full envelope and survives restart.
- [ ] Two isolated non-live `SHAY_HOME` profiles with distinct session namespaces
  cannot retrieve or modify each other's memory. The provenance envelope continues
  to carry session, parent-session, task, and tool-call identifiers.
- [ ] Replace/remove actions preserve provenance history and tombstones.
- [ ] An ordinary candidate record remains candidate through repeated recall/write and
  restart. A matching single-use owner decision plus the public promotion operation
  creates one curated superseding record; missing, reused, cross-profile, stale, or
  mismatched decisions fail without promotion. Protected identity/persona targets are
  rejected even when presented to the memory promotion operation.
- [ ] Hostile recalled text remains data and cannot become instructions.
- [ ] External-provider failure falls back without corrupting built-in memory.
- [ ] Older records remain readable.
- [ ] Persona, soul, and owner files remain byte-identical.
- [ ] Before either R5 or R6 candidate freeze, pass the shared composed-tree optional-
  field barrier. It begins from the accepted R3+R4 composition, applies the R6 delta
  relative to R3 and then the R5 delta relative to R4, and proves `effect` and
  `memory_provenance` contract fields are safely absent for legacy producers and
  validated when populated. Both phase candidates bind the same tool-issued receipt,
  exact input/base/composed-tree SHAs, argv, exit, and artifacts.

### Evaluation

- [ ] Create the reviewed fixture
  `tests/fixtures/memory_provenance_benchmark_v1.json`. It is a closed JSON object
  `{schema_version,seed,corpus,queries}` with `schema_version=1`, `seed=20260913`,
  exactly 32 corpus records, and exactly 16 queries. Corpus IDs are `memory-001`
  through `memory-032`; each record is exactly
  `{id,target,content,source,created_at,confidence,supersedes_or_tombstones}`.
  Query IDs are `query-001` through `query-016`; each query is exactly
  `{id,text,expected_record_ids,forbidden_record_ids,required_provenance_fields}`.
  IDs and arrays are sorted and duplicate-free, timestamps are fixed RFC3339 values,
  targets are `memory` or `user`, and the literal fixture content plus its SHA-256 is
  the reviewed corpus authority. No generated, random, vendor, network, or live-profile
  data may enter a measured run.
- [ ] Run an offline paired `MemoryStore` protocol in two clean worktrees: baseline is
  the externally reviewed pre-R5 dependency tip (R4 C), candidate is the R5 candidate
  tree, and both use the same validated caller-supplied immutable v4 Python 3.11 all+dev environment,
  interpreter/provenance bytes, host/hardware fingerprint, fixture bytes, and fixed
  seed. Each side gets fresh scrubbed HOME/SHAY_HOME/prompt-vault/Kanban state below
  its own external profile root; it loads the 32 records through public `MemoryStore`
  writes, closes, reopens, performs the 16 queries through the reviewed offline recall
  entry point, and records exact cited record IDs and serialized provenance. Network,
  external memory providers, LLM calls, filesystem caches shared between sides, and
  owner paths are forbidden.
- [ ] Perform one unmeasured warmup for each side, then five measured paired rounds.
  Odd rounds run baseline then candidate; even rounds run candidate then baseline.
  Recreate both profile roots for every round. Use `time.perf_counter_ns()` around only
  the query call. For each round, compute query-level p95 with nearest-rank index
  `ceil(0.95*N)-1`; aggregate each side as the median of its five round p95 values.
  Provenance precision is expected cited IDs divided by all cited IDs (empty citations
  score 0); required-field omission is missing required fields divided by required
  fields; stale-fact rate is forbidden IDs cited divided by all cited IDs (empty is 0).
  `token_p95` uses the deterministic project-independent estimator
  `ceil(len(canonical UTF-8 retrieval payload bytes)/4)` per query and the same
  nearest-rank/median aggregation. Record raw query rows, round p95 values, medians,
  fixture/interpreter/provenance/commit hashes, order, seed, and hardware fingerprint.
- [ ] Technical acceptance thresholds are fixed by this reviewed R0 contract under the
  existing implementation directive: candidate provenance precision must equal 1.0,
  required-field omission rate must equal 0, stale-fact rate must equal 0,
  candidate median `token_p95` must be at most `baseline*1.10+32`, and candidate median
  latency p95 must be at most `max(baseline*1.25, baseline+5ms)`. These are not left for
  later owner improvisation. Any threshold failure, protocol mismatch, environment or
  hardware mismatch, owner-path access, network access, fixture drift, or prompt-cache
  regression rejects R5. Merge approval remains null and separate.

Exit evidence: provenance and recall benchmark bundle with protected files hashed
before and after. Multi-tenant memory authority is absent and outside this phase; R5
does not claim tenant isolation.

## 15. Phase 6 — Define one versioned client domain contract

Goal: borrow Goose's shared-core pattern while preserving Shay's existing adapters.

### Contract checklist

- [ ] Source-map CLI, TUI JSON-RPC, gateway API, ACP, sessions, approvals, and Kanban
  before editing.
- [ ] Record the owner and compatibility decision in
  `docs/architecture/adr-shay-client-domain-contract.md` before adapter code.
- [ ] Define versioned schemas for capability, task, run, session, event, approval,
  usage, and error objects.
- [ ] Implement one adapter-neutral public service seam in
  `shay_cli/domain_contract.py` with exact operations `inspect_task(task_id)`,
  `list_task_events(task_id, after_event_id)`, `cancel_task(task_id, actor)`,
  `retry_task(task_id, actor)`, and `resume_task(task_id, actor)`. These operations
  delegate to the R3 Kanban authority; they do not create client-local lifecycle state.
- [ ] Use the same identifiers and status vocabulary in every adapter.
- [ ] Specify ordering, replay cursor, deduplication, terminal states, cancellation,
  unknown-field tolerance, and incompatible-version behavior.
- [ ] Declare which fields are authoritative, derived, unavailable, or client-local.
- [ ] Define optional typed `effect` and `memory_provenance` projections. Their absence
  means unavailable, never zero/empty/safe; populated values must validate their
  versioned schema and authority reference. R6 can prove absence on its R3 ancestry and
  must accept truthful populated fixtures at the R5+R6 compatibility barrier.
- [ ] Keep current transports; add adapters rather than forcing one wire protocol on
  all clients.
- [ ] Preserve the central command registry and real TUI embedding.
- [ ] Keep legacy contract fixtures for one compatibility window.

### Required tests

- [ ] Submit a task in one client; inspect, approve/deny, stop, and resume it from a
  second client against one ledger.
- [ ] Reconnect and replay events without loss or duplication.
- [ ] Restart the gateway and prove client-visible lifecycle truth is unchanged.
- [ ] Additive unknown fields are ignored safely; incompatible versions fail clearly.
- [ ] Contract fixtures pass for CLI, TUI, API, and ACP adapters.
- [ ] Each of the five public service operations above is exercised through at least
  two adapters against one durable ledger, with stable error and terminal semantics.
- [ ] Before either R5 or R6 candidate freeze, pass and bind the same R5+R6 composed-
  tree receipt described in Phase 5. Any input or dependency-tree change invalidates
  both candidates' receipt closure.
- [ ] No test relies only on mocked session state for the final E2E gate.

### Anti-pattern guards

- [ ] No second command registry.
- [ ] No second chat transcript/composer in the dashboard.
- [ ] No API response that claims a capability because code exists but is disabled or
  unavailable at runtime.

Exit evidence: versioned contract fixtures and a real cross-client journey.

## 16. Phase 7 — Improve the CLI without duplicating existing commands

Goal: borrow Aider/OpenCode operator clarity while retaining Shay's personality,
command vocabulary, and TUI.

### Discovery gate

- [ ] Inventory current `/status`, `/usage`, `/model`, `/background`, `/stop`,
  `/resume`, `/rollback`, goals, Kanban, approvals, `shay doctor`, and TUI surfaces.
- [ ] Mark each proposed feature as extend, alias, compose, or absent; do not add a
  duplicate command with a new name.

### Checklist

- [ ] Add explicit inspect/plan/write authority presentation without treating a mode
  label as permission.
- [ ] Show durable task/run ID, lifecycle state, last event, waiting reason, provider,
  model, and verified usage/cost availability.
- [ ] Add consistent inspect, event-tail, cancel, retry, and resume UX over the shared
  contract by consuming R6's exact public `inspect_task`, `list_task_events`,
  `cancel_task`, `retry_task`, and `resume_task` operations. R7 must not query Kanban
  directly or introduce a second lifecycle service.
- [ ] Extend `shay doctor` to report E2E dependency parity, writable/path scope,
  protocol compatibility, and durable-ledger readiness.
- [ ] Provide structured/machine-readable output with stable exit codes and no ANSI
  leakage.
- [ ] Surface proposed versus executed file changes. Because R7 inherits R3/R6 but
  not R4/R5, typed checkpoint/effect and memory-provenance fields must remain
  explicitly unavailable until R8 integrates the reviewed R5 delta; R7 may not infer
  them from source presence.
- [ ] Add the operator view through plugin command registration. The current plugin
  slash-command registry does not automatically populate classic global help,
  `gateway_help_lines`, or TUI `commands.catalog`; those surfaces are out of R7's
  exact write set and must not be claimed as synchronized or available.
- [ ] Use `display_shay_home()` for output and `get_shay_home()` for state.

### Required tests

- [ ] Plugin command discovery/help and direct `shay doctor` output stay internally
  consistent. Classic global help, gateway help, autocomplete, and TUI catalog remain
  unchanged and are explicitly reported as unavailable for the new plugin command.
- [ ] Machine mode is parseable and contains no spinner/ANSI leakage.
- [ ] Missing cost/provider data is reported as unavailable, not zero.
- [ ] Legacy command names and aliases remain compatible.
- [ ] The same task IDs and states appear through CLI and another adapter.
- [ ] Paths with spaces, Unicode, and multiple profiles remain correct.

Exit evidence: R7 records only its real subprocess CLI/operator journey in
`docs/architecture/evidence/shay-agent-r7-events.jsonl`. Only serialized R8 runs the
common proof and creates the canonical bundle.

## 17. Phase 8 — Full end-to-end acceptance and rollout

Goal: prove the entire upgraded lifecycle, then roll it out reversibly.

### Synthetic journey matrix

- [ ] Read-only task completes with no approval and no unintended writes.
- [ ] Reversible local write requests approval, creates a checkpoint, records the
  effect, and rolls back successfully.
- [ ] Destructive/sensitive request is denied by a hardline or typed policy rule.
- [ ] Duplicate task/effect requests execute once.
- [ ] Worker crash and gateway restart recover the same task/run without false
  completion.
- [ ] Approval wait survives restart; timeout denies.
- [ ] Provider failure respects retry and USD ceilings and records the terminal reason.
- [ ] Memory write records provenance and recall cites the correct record.
- [ ] Cross-client inspect/approve/stop/resume uses one authoritative state.
- [ ] Cancellation's durable terminal state is composed with R4 interception/effect
  truth: after cancellation, including across approval wait, worker crash, gateway
  restart, and nested/composite tools, no new or in-flight child tool effect is
  dispatched or recorded. This is the first full no-post-cancel-tool-effect claim;
  R3 alone intentionally made only durable lifecycle/no-new-scheduling claims.
- [ ] CLI machine output and human output remain truthful.
- [ ] The bundled operator plugin remains disabled by default; evidence reports it as
  unavailable until a separate owner-gated enable action. Rollback is disable/remove
  from enabled plugin state, never a claim that bundled source equals activation.
- [ ] Two isolated non-live `SHAY_HOME` profiles and their session namespaces remain
  isolated; no multi-tenant memory authority is claimed.
- [ ] Voice, filming, persona, soul, credentials, and unrelated custom code remain
  byte-identical.
- [ ] Launcher and profile paths work from a non-repository current directory and a
  supported alternate environment layout.
- [ ] Revalidate and consume the already-passing R3+R4 and R5+R6 compatibility receipt
  hashes and their exact input/composed-tree identities. Missing, superseded, or drifted
  pair evidence blocks R8 before canonical integration/proof; R8 does not create a
  first-time compatibility waiver.

### Proof classification

- `locally proven`: the isolated synthetic harness passed locally.
- `test-provider proven`: a specifically named provider's test mode passed with
  redacted IDs/evidence.
- `production smoke-tested`: an explicitly authorized, non-destructive production
  check passed; this does not imply unrestricted production readiness.
- `launch-blocked`: any required gate is absent or failed.

### Canonical proof artifact

- [ ] Only R8 may run `scripts/run_shay_upgrade_proof.sh`; the hardened tool emits the six exact
  terminal markers: `PASS: baseline`, `PASS: lifecycle`, `PASS: safety`,
  `PASS: memory`, `PASS: protocol`, and `PASS: CLI journey`. Candidate-controlled runner
  strings are reporter output only and are never marker authority. The bound tool derives those
  six ordered markers only from six closed semantic observations recomputed from the tested Git
  tree/base, external lifecycle prefix, protected-state and rollback receipts, memory provenance,
  complete issued protocol receipts, and the sandboxed CLI E2E behavior receipt; a missing,
  duplicated, reordered, or caller-shaped observation fails. It separately starts the bundled
  operator plugin enabled/active in an isolated disposable Shay home, proves the new path
  functions, executes the exact flag-off command, then proves the legacy path functions and
  protected state remains intact. The proof's
  single `rollback_results` row binds that real rollback command/output receipt; it does
  not fabricate six rollback rows from the ordinary PASS markers. Its exact totals distinguish
  `executed_commands=2`/`passed_commands=2` (the two contracted top-level commands) from
  `validated_semantic_evidence=6`. The enabled-to-disabled rollback is a tool-issued internal
  semantic sub-step of the applicable proof command, not a third contracted command, and the six
  gates never inflate the execution count. The CLI
  observation binds only preserved issued receipt/stdout/source-blob digests, never a digest of
  discarded raw runner bytes.
- [ ] Only R8 may create the final common
  `docs/architecture/evidence/shay-agent-upgrade-evidence.json`. Validate its closed schema,
  require every capability assertion to be `true`, and include base/integration SHAs,
  dirty state, exact commands and exit codes, timestamps, environment, counts,
  skipped/blocked proof, artifact hashes, protected-file hashes, feature flags,
  tool-derived markers, and rollback results. Include the exact pre-candidate external-ledger path, cutoff
  sequence/event, prefix hash, board-snapshot hash, and state
  `r1_r7_complete_r8_pre_review`. A missing dependency or skipped required test is not
  a pass.
- [ ] Freeze exact repository cutoffs: R1-R7 phase-local files through their final
  verification/blocked pre-review line and R8 through its verification line. Under a
  shared lock also freeze the external ledger through every complete R1-R7 chain.
  Record line counts, last event IDs/sequences, SHA-256 values, and hash-chain tip.
- [ ] Validate every cutoff, R1-R7 external review/commit/remote/completion chain,
  dependency tip, protected hash, and board read-back before canonical writes. In a
  separate verification worktree representing the R8 temporary candidate tree,
  require exact before/after inventory bindings while proof writes only to a fresh
  external temporary path. On failure, leave canonical/status/evidence bytes absent or
  byte-identical.
- [ ] After proof passes but before candidate freeze, copy the external artifact
  byte-for-byte to `docs/architecture/evidence/shay-agent-upgrade-evidence.json`;
  verify byte equality, SHA-256, and closed schema. It is an ordinary reviewed R8
  candidate byte, not a later finalization change.
- [ ] Copy R1-R7 pre-review-through-verification lines byte-for-byte into canonical
  trace and build final evidence/status from the frozen pre-candidate external-ledger
  snapshot. The in-repository artifacts record the cutoff and explicitly say R8 final
  reviews, commit, push, task completion, and program finalization are not yet facts.
- [ ] Freeze one R8 candidate, record its three current independent passing results,
  commit the exact tree and invoke `record-commit`; then invoke provider-backed
  `record-push-ci` so `git ls-remote` and GitHub Actions independently bind the remote
  branch/head/workflow/run/conclusion/jobs and artifact-metadata receipt. Complete/read back R8, then
  invoke `record-finalize`, which recomputes the actual clean R8 C/tree/index, status
  and canonical-trace blobs/count/tip, preserves the immutable candidate-bound PRE-REVIEW
  board/ledger snapshot, computes a separate full POST-COMPLETION SQLite schema/table
  projection including task runs, and proves the only delta is valid supersession history
  followed by the active R8 candidate's three current reviews, commit, push, exact public-
  domain task/event/run/failure-reset/dependent-promotion transition, and lifecycle rows.
  Do not change repository bytes or branch tip afterward. An identical rerun still
  first replays the immutable retry budget before any provider call, then re-queries every
  accepted remote/CI receipt only through the ledger-issued query plan before read-only success;
  changed provider facts,
  unrelated board/ledger mutation, changed/later input, a second
  finalization, or any event after finalization fails nonzero.

### PR and release checklist

- [ ] Every phase is a separate reviewed candidate and pushed reviewable feature
  branch, or an explicitly justified dependency stack; no giant cross-cutting merge.
  Branch CI on `codex/shay-agent-*` plus the three external candidate-bound reviews
  are phase completion gates. PR creation is optional and owner-gated, not required
  for implementation completion.
- [ ] Before final review, fetch current `origin/main` as a drift check, verify it has
  not invalidated the pinned contract, and keep each branch based on its reviewed
  dependency tip. Any later rebase/merge into `main` requires explicit merge
  approval.
- [ ] Use the GitHub connector read-only to compare pushed commits, enumerate every
  changed file, and inspect branch checks/artifacts. Count unresolved review threads
  only if the owner separately authorizes a PR.
- [ ] Use `claude-mem:babysit` only after a PR exists by explicit owner authorization;
  it is not invoked merely to satisfy a phase completion gate.
- [ ] Require owner review before merge.
- [ ] Canary on a disposable profile with all new feature flags off, then enable one
  phase at a time.
- [ ] Verify rollback before enabling the next phase.
- [ ] Capture final C, test counts, evidence hash, external-ledger cutoff/final hash,
  flags, rollback command, and remaining blocked gates in the external user handoff.
- [ ] Treat this capability contract and plan as frozen reviewed governance. R8's
  exact E0007 allowlist is the sole write authority; its governed outputs include the
  canonical trace, diagrams, final checklist, proof evidence, status page, runner,
  E2E test, phase-local evidence, and CI workflow. Updating the external Obsidian research ledger is an optional,
  owner-directed follow-up outside the repository write scope and is not a release
  or completion requirement.

Exit evidence before owner handoff: clean reviewed/pushed feature-branch stack tips at
the single candidate commits C, passing branch CI, canonical evidence bundle, final
external execution chain, and tested rollback for every flag. If owner-authorized PRs
exist, they additionally require zero unresolved review threads. PR creation, review,
and merge are not performed absent explicit authorization; owner merge approval remains
a separate later gate.

If a pushed reviewed candidate fails mandatory CI, its already-recorded local
`implementation_commit_recorded` remains immutable but it is not an accepted dependency C.
Provider-backed `record-push-ci` emits `ci_verification_failed` with the durable GitHub
receipt. Preserve the failed tip and record the attempt as blocked in the external ledger,
while the Kanban requirement deliberately remains active `ready`/`running` rather than being
falsely blocked. `start-successor` validates the ledger-bound failed-CI provider observation and
the exact local Git DAG commit/tree/base facts, then authorizes a fresh candidate only on a new
attempt ID and distinct successor branch. The recorder emits `candidate_superseded` tied to that
failed-CI event, making every old pass/commit ineligible; all three reviews rerun. Every
successor/no-op/terminal recorder repeats the ledger-plus-local proof without an undeclared
network call. Branch reuse or inclusion of the failed tip in the accepted successor DAG fails.
Only a successor with authoritative remote equality and CI success may reach completion. The
finalizer's provider helpers may run only inside the active issued query plan and share its one
candidate-wide observed-byte counter.

## 18. Proposed branch/work packet sequence

| Order | Branch purpose | Primary paths | Depends on |
| --- | --- | --- | --- |
| 0 | Capability contract and trace ledger | `docs/architecture/`, `docs/plans/` | none |
| 1 | Baseline/E2E harness and rename-damage repair | Python harness paths plus `ui-tui/package-lock.json`, launcher/setup sources, focused external-cli test | 0 |
| 2 | Anti-drift reconciler | trace/audit script, fixtures, docs | 1 |
| 3 | Kanban idempotency and durable run service | exact R3 packet below | externally complete 2 C |
| 4 | Typed safety policy and generic approval seam | exact R4 packet below | externally complete 2 C |
| 5 | Memory provenance through built-in and external paths | exact R5 packet below | complete 4 C; start only after 3 and 4 external chains complete |
| 6 | Versioned contract and client adapters | exact R6 packet below | complete 3 C; start only after 3 and 4 external chains complete |
| 7 | Plugin-based operator UX and doctor output | exact R7 packet below | externally complete 6 C |
| 8 | Serialized common proof and documentation integration | exact R8 packet below | complete primary 7 C, integrate complete 5 C; 3 and 4 inherited |

### Fresh-context execution packets R3-R8

Every packet starts in a new session and isolated worktree. Re-read `AGENTS.md`, this
plan, the capability contract, current diagrams, the immutable canonical seed, the
exact phase-local pre-review evidence inherited from dependencies, and the matching
external execution-ledger chains under a shared lock; fetch `origin/main` and use its
tip only to check whether newer main invalidates the pin, contract, protected hashes,
manifest, or dependency. Base the packet on the single externally proven dependency C
whose candidate tree matched all three review records and whose verified remote SHA
equals C; record it as `implementation_base_sha`.
Integrate only the packet's listed additional reviewed dependencies; before any other
authored edit, create the packet's exact evidence JSONL with an
`implementation_started` line recording the post-integration HEAD as
`integration_base_sha`. The phase-local file stops at verification; later review,
commit, push, and completion facts append only to the external execution ledger. Do
not merge or rebase `origin/main` into
the stack under implementation-only approval. Require a clean worktree; verify
`SHAY-PROTECTED-CUSTOM-BASELINE-v1`; and treat every path not explicitly listed for
that packet as read-only. The SHA
`cf6bb95e3dc12e0d4b8eadef2c33be2b39ad21b6` is the Phase 0 planning anchor, not
permission to start a future packet from stale main.

R3 — branch `codex/shay-agent-phase3-durable-lifecycle`, worktree
`/Users/famtastic-fritz/Development/FAMtastic/worktrees/shay-agent-phase3-durable-lifecycle`.
It may write only:

- `shay_cli/kanban_db.py`
- `shay_cli/kanban_run_adapter.py`
- `tests/shay_cli/test_kanban_db.py`
- `tests/shay_cli/test_kanban_run_adapter.py`
- `tests/stress/test_concurrency.py`
- `tests/integration/test_kanban_restart_recovery.py`
- `gateway/platforms/api_server.py`
- `tests/gateway/test_api_server_runs.py`
- `docs/architecture/adr-shay-durable-task-run-ownership.md`
- `docs/architecture/evidence/shay-agent-r3-events.jsonl`

Prove concurrent idempotency, existing `task_events.id` cursor ordering, terminal
single-write behavior, cancellation, worker and gateway restart, durable API replay,
and legacy/additive reads. R3 owns the durable service over Kanban and the existing
HTTP adapter for that service; broader cross-client contract mapping remains R6.

R4 — branch `codex/shay-agent-phase4-typed-safety`, worktree
`/Users/famtastic-fritz/Development/FAMtastic/worktrees/shay-agent-phase4-typed-safety`.
It may write only:

- `shay_cli/plugins.py`
- `model_tools.py`
- `run_agent.py`
- `tools/approval.py`
- `plugins/safety_policy/plugin.yaml`
- `plugins/safety_policy/__init__.py`
- `plugins/safety_policy/policy.py`
- `plugins/safety_policy/ledger.py`
- `tests/shay_cli/test_plugins.py`
- `tests/test_model_tools.py`
- `tests/run_agent/test_run_agent.py`
- `tests/tools/test_approval.py`
- `tests/plugins/test_safety_policy.py`
- `tests/integration/test_typed_approval_clients.py`
- `docs/architecture/evidence/shay-agent-r4-events.jsonl`

Prove legacy block compatibility, fail-closed typed resolution, the generic
interactive approval flow, hardline precedence, path/symlink enforcement,
idempotent synthetic effects, USD cutoff, and redacted ordered decisions. In
particular, the concurrent denial proof must show typed policy runs before checkpoint
or ref creation and produces zero checkpoint/ref/process/tool/effect changes. Preserve
the explicit Docker, Singularity, Modal, Daytona, and Vercel Sandbox isolation-test
exceptions; this ordering requirement does not convert them into host-hardline paths.

R5 — branch `codex/shay-agent-phase5-memory-provenance`, worktree
`/Users/famtastic-fritz/Development/FAMtastic/worktrees/shay-agent-phase5-memory-provenance`.
It may write only:

- `tools/memory_provenance.py`
- `tools/memory_tool.py`
- `agent/memory_provider.py`
- `agent/memory_manager.py`
- `run_agent.py`
- `tests/tools/test_memory_provenance.py`
- `tests/tools/test_memory_tool.py`
- `tests/agent/test_memory_provider.py`
- `tests/agent/test_memory_prefetch_trace.py`
- `tests/run_agent/test_run_agent.py`
- `tests/integration/test_memory_provenance_profiles.py`
- `tests/fixtures/memory_provenance_benchmark_v1.json`
- `docs/architecture/evidence/shay-agent-r5-events.jsonl`

R5 bases on the reviewed R4 tip; it is not parallel with R4. Prove the real
`run_agent.py` built-in `MemoryStore` receives the envelope, plus immutable
versions/tombstones, restart, isolation between two non-live `SHAY_HOME` profiles and
their session namespaces, hostile recall treatment, provider failure fallback,
old-record compatibility, cache stability, and byte-identical protected files. The
envelope retains session, parent-session, task, and tool-call identifiers. No
multi-tenant memory authority exists at baseline, so tenant isolation is out of scope.
The fixed 32-record/16-query fixture, offline paired R4-tip-versus-R5-candidate
protocol, five alternating measured rounds after warmup, exact metrics, and numeric
acceptance thresholds in Phase 5 are mandatory candidate evidence.

R6 — branch `codex/shay-agent-phase6-client-contract`, worktree
`/Users/famtastic-fritz/Development/FAMtastic/worktrees/shay-agent-phase6-client-contract`.
It may write only:

- `shay_cli/domain_contract.py`
- `docs/architecture/adr-shay-client-domain-contract.md`
- `cli.py`
- `gateway/platforms/api_server.py`
- `tui_gateway/server.py`
- `ui-tui/src/gatewayClient.ts`
- `ui-tui/src/__tests__/gatewayClient.test.ts`
- `acp_adapter/server.py`
- `acp_adapter/session.py`
- `tests/shay_cli/test_domain_contract.py`
- `tests/cli/test_cli_domain_contract.py`
- `tests/gateway/test_api_server_runs.py`
- `tests/tui_gateway/test_protocol.py`
- `tests/acp/test_server.py`
- `tests/integration/test_cross_client_contract.py`
- `docs/architecture/evidence/shay-agent-r6-events.jsonl`

Record the owner decision in `docs/architecture/adr-shay-client-domain-contract.md`,
map the R3 durable service
into the existing adapters, and prove versioning, replay, restart, cancellation,
unknown-field tolerance, and one cross-client lifecycle. Do not replace transports
or ACP/TUI-local slash-command exceptions. R6 inherits the externally complete reviewed
Phase 1 package-lock and launcher repair; it may not edit those R1-owned files, and its
external-copy Node gate must run typecheck plus the focused gateway client test.

R7 — branch `codex/shay-agent-phase7-operator-ux`, worktree
`/Users/famtastic-fritz/Development/FAMtastic/worktrees/shay-agent-phase7-operator-ux`.
It may write only:

- `plugins/operator_view/plugin.yaml`
- `plugins/operator_view/__init__.py`
- `plugins/operator_view/commands.py`
- `shay_cli/doctor.py`
- `tests/plugins/test_operator_view.py`
- `tests/shay_cli/test_doctor.py`
- `tests/integration/test_operator_view.py`
- `docs/architecture/evidence/shay-agent-r7-events.jsonl`

Extend inspection through plugin command registration and existing doctor output;
do not create a second registry or duplicate built-in command. Prove human/machine
output, stable exit codes, no ANSI leakage, missing-cost honesty, profile-safe paths,
and the same durable IDs visible through another adapter. The plugin remains disabled
by default and is reported unavailable absent a separate owner-gated enable action.
R7 does not claim its plugin command appears in classic global help,
`gateway_help_lines`, autocomplete, or TUI `commands.catalog`, because its write set
does not own those surfaces. Typed checkpoint/effect and memory-provenance fields are
also unavailable in R7 ancestry and become integrable only when R8 adds reviewed R5 C
to the R7/R6 ancestry.

R8 — branch `codex/shay-agent-phase8-acceptance`, worktree
`/Users/famtastic-fritz/Development/FAMtastic/worktrees/shay-agent-phase8-acceptance`.
It may write only:

- `scripts/run_shay_upgrade_proof.sh`
- `tests/e2e/test_shay_upgrade_proof.py`
- `.github/workflows/tests.yml`
- `docs/architecture/shay-agent-enhancement-trace.jsonl`
- `docs/architecture/shay-current-state-diagrams.md`
- `docs/architecture/evidence/shay-agent-r8-events.jsonl`
- `docs/architecture/evidence/shay-agent-upgrade-evidence.json`
- `docs/status/shay-agent-enhancement-status.md`
- `docs/status/shay-agent-enhancement-final-checklist.md`

R8 is the only R3-R8 packet allowed to integrate the common proof runner, CI gate,
canonical trace, diagrams, final checklist, proof evidence, or final in-repo status
page. This plan and the capability contract are frozen Phase 0 authority and are not
R8 write paths.
It bases on externally proven R7 C and integrates externally proven R5 C. Before
candidate construction it freezes R1-R7 phase-local files through verification plus a
shared-lock external-ledger prefix through complete R1-R7 chains; validates them and
the board; copies only repository pre-review records byte-for-byte into canonical
trace; runs the common proof against the temporary candidate with output external;
and copies the validated proof into its normal candidate paths. The in-repository
status/evidence records its exact external cutoff and honestly says R8's reviews,
commit, push, completion, and finalization occur later. Three external reviews then
bind this one candidate; `record-commit` binds the exact clean committed tree, and
provider-backed `record-push-ci` binds authoritative origin equality plus GitHub Actions
receipt bytes before its task is completed/read back. Only afterward does
`record-finalize` recompute repository, trace, board, and current ledger terminal facts
and append `program_finalized`. Repository bytes and the branch tip remain fixed at C. External
Obsidian ledger edits remain out of scope and optional.

R1 is based on externally complete R0 C and R2 on externally complete R1 C; complete
means three candidate-bound passes, exactly one C, verified remote C, board done/read-
back, and external `kanban_completed`. After R2 reaches that full chain, R3 and R4 may run in parallel because their
authored paths are disjoint. After both external chains reach completion, R5 bases on
R4 C while R6 bases on R3 C; R5 and R6 may run in parallel because their authored
path sets are disjoint. R4 and R5 may not run in parallel. R7 consumes externally
complete R6 C. R8 bases on externally complete R7 C and integrates complete R5 C
delta; R3 is inherited through R6/R7 and R4 through R5. R3/R6 intentionally share
`gateway/platforms/api_server.py` and `tests/gateway/test_api_server_runs.py`, while
R4/R5 intentionally share `run_agent.py` and its focused tests; those are serialized
inheritance, not concurrent authored edits. Each packet validates authored paths from
its post-integration base and inherited paths against the union of dependency
manifests. These feature-branch integrations do not authorize merge to `main`.

## 19. Definition of done

- [ ] Every research recommendation has a traceable disposition: adopted, evaluated,
  reference-only, or rejected with evidence.
- [ ] No parallel task database, command registry, memory authority, or chat surface
  was introduced.
- [ ] Every changed behavior is disabled-safe, migration-safe, and rollback-tested.
- [ ] All focused, full, E2E, stress, protocol, and cross-client gates pass.
- [ ] Evidence files are machine-readable, hashed, and agree with human summaries.
- [ ] No live credentials, owner profile, identity/persona, filming, voice, or unrelated
  custom code changed.
- [ ] GitHub branch CI is clean for every pushed R1-R8 `codex/shay-agent-*` tip; R0 instead has the explicit CI-not-applicable-bootstrap remote-equality receipt. If an owner-
  authorized PR exists, its checks and actionable review threads are also clean; the
  absence of a PR is not a phase failure.
- [ ] Owner explicitly approves each merge and any later live enablement.

Until every applicable item is proven, report the narrow achieved evidence class and
the remaining blockers—never simply report “Shay is upgraded.”
