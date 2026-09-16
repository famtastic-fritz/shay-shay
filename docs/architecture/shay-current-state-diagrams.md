# Shay current-state diagrams — `cf6bb95e`

Status: Phase 0 source map; documentation only. Bracketed IDs are stable line
labels. Solid arrows are source-confirmed; dashed arrows are roadmap gaps.

## Task lifecycle

```text
[TL-01] Kanban callers
   -> [TL-02] connect(board) -> SQLite tasks/task_runs/task_events
   -> [TL-03] create_task: idempotency pre-check outside transaction [PARTIAL]
        - - R1 minimum: fresh-database lookup+insert race repair - -> [TL-04]
        - - R3: historical reconciliation+migration+service restart - -> [TL-09]
   -> [TL-04] BEGIN IMMEDIATE: insert task, links, created event
   -> [TL-05] ready | todo awaiting parents | triage
   -> [TL-06] claim_task CAS -> running + task_run + claimed event
   -> [TL-07] heartbeat | reclaim | PID/runtime failure
   -> [TL-08] done | blocked | ready after reclaim; close run + append event
   -> [TL-09] task_events.id monotonic durable sequence + list_events/list_runs [CURRENT]

[TL-10] HTTP /v1/runs dictionaries + SSE queues [PARTIAL; PROCESS MEMORY]
   - - durable Kanban-backed HTTP adapter [ABSENT] - -> [TL-09]
[TL-11] SessionDB conversations/messages [SEPARATE; NOT TASK TRUTH]
```

- TL-02/04/06/09: `shay_cli/kanban_db.py:753-930`, `1173-1187`,
  `1861-1972`, `4736-4754`; tests in `tests/stress/test_concurrency.py:73-97`.
- TL-03: non-unique index at `shay_cli/kanban_db.py:873` and pre-check at
  `1330-1340`; the race fixture is `tests/stress/test_atypical_scenarios.py:689-755`.
- TL-05: archived-parent semantics differ between `shay_cli/kanban_db.py:1355-1366`
  and `1828-1854`; fixture: `tests/stress/test_atypical_scenarios.py:935-973`.
- TL-07/08: `shay_cli/kanban_db.py:1975-2035`, `2351-2415`, `2584-2636`.
- TL-10: `gateway/platforms/api_server.py:578-618`, `2738-2910`, `3099-3287`.
- TL-11: `shay_state.py:309`; `acp_adapter/session.py:186-242`.

Ownership: Kanban remains the only durable task/run/event authority. SessionDB owns
conversation history, cron owns schedules, and ProcessRegistry owns live handles.
R1 owns the minimal fresh-database transactional idempotency fix and the bounded
portability-rename baseline repair. The latter restores `hermes-parser`/`hermes-estree`
lock entries and valid `launchShayCommand`/`resolveShayBin` identifiers, then proves a
clean-registry disposable `npm ci`, typecheck, and focused external-cli test. The
current `shay-parser`/`shay-estree` 404 and invalid TypeScript identifiers are recorded
as a failing baseline, never as an accepted cache bypass. R3 must preserve the Kanban
repair and owns historical duplicates,
durable migration/enforcement, task/run/event transition idempotency, service/API
semantics, and restart proof. A worker killed mid-tool becomes honestly
interrupted/uncertain or retry-required; R3 never infers external-effect exactly-once.
R3 cancellation acceptance is durable terminal state, restart survival, and no new
dispatch scheduling from cancelled state. R4 alone adds durable tool-call/effect keys
and proves external-effect deduplication. Only the R8 composition may claim that no
in-flight or nested child tool effect occurs after cancellation.

## Tool policy

```text
[TP-01] Model tool call
   -> [TP-02] AIAgent sequential/non-overlapping-concurrent executor
        +-- sequential --> [TP-03] pre_tool_call plugin hook (single fire)
        |                    +-- block -> [TP-04] synthetic error; no checkpoint/dispatch
        |                    +-- allow -> [TP-05] CheckpointManager for write/patch or destructive terminal
        +-- concurrent current --> [TP-06] parse each call; CheckpointManager.ensure_checkpoint first [GAP]
        |                            -> [TP-07] pre_tool_call plugin hook (single fire)
        |                                 +-- block -> [TP-08] synthetic error; no dispatch, checkpoint may exist
        |                                 +-- allow -> [TP-09] agent-level intercept or core dispatch
        +-- concurrent R4 target - - > [TP-14] parse + resolve typed pre_tool_call first
                                     +-- deny/block/timeout/error -> [TP-15] synthetic error;
                                     |                               zero checkpoint/ref/process/tool/effect writes
                                     +-- allow -> [TP-16] checkpoint/ref creation
                                                   -> agent-level intercept or core dispatch
   -> [TP-10] model_tools.handle_function_call -> ToolRegistry.dispatch
        +-- host-capable terminal -> [TP-11] hardline + dangerous-command approval
        +-- isolated backend ----> [TP-12] backend-isolation policy/tests
        +-- other ---------------> [TP-13] handler-specific effect [TYPED POLICY ABSENT]
[TP-17] execute_code or composite/environment parent [R4 TARGET]
   - - pre-dispatch ordered durable child IDs -> per-child policy/dedup -> dispatch
   - - child IDs unavailable before effect -> deny parent; zero child effects
[TP-18] cost-bearing effect [R4 TARGET]
   - - authoritative bounded maximum <= remaining USD ceiling -> may dispatch
   - - maximum unknown -> deny cost_unknown; unknown actual -> block later spend
```

- TP-01/02/03/04/05: `run_agent.py:10983-11065`.
- TP-06/07/08/09: `run_agent.py:10546-10631`. In this concurrent path a call
  later blocked by the plugin can still leave checkpoint state; rollback evidence
  must not equate checkpoint creation with tool dispatch.
- TP-03/07: `model_tools.py:763-788`; `shay_cli/plugins.py:1198-1232`,
  `1315-1348`; `run_agent.py:10445-10456`;
  `tests/test_model_tools.py:137-265`.
- TP-10: `model_tools.py:730-850`; `tools/registry.py:151-410`.
- TP-05/06: `run_agent.py:10546-10608`, `11043-11065`;
  `tools/checkpoint_manager.py:575-655`.
- TP-11/12: `tools/approval.py:1020-1057`; tests in
  `tests/tools/test_approval.py` and `tests/acp/test_permissions.py:40-85`.

Ownership: ToolRegistry remains dispatch authority; `pre_tool_call` is the additive
plugin seam; approval retains hardline shell denial in host-capable environments;
checkpoints retain rollback. Docker, Singularity, Modal, Daytona, and Vercel Sandbox
are explicit isolated-backend exceptions in `tools/approval.py`; their safety claim
must be proved by separate containment/isolation tests, not host hardline tests.
Absent: shared effect classes, resolved allowed roots, durable duplicate-effect keys,
one redacted decision ledger, a hard USD cutoff, and a generic typed interactive
approval result. If typed policy needs an interactive decision, the future path must
extend `shay_cli/plugins.py` -> `model_tools.py`/`run_agent.py` ->
`tools/approval.py`; a policy plugin cannot claim that behavior by itself.
R4 must close TP-06 by moving concurrent typed policy resolution ahead of all
checkpoint/ref creation and proving a denial changes no checkpoint refs/objects,
ProcessRegistry rows, dispatch counters, or synthetic effects. The sequential path is
already policy-before-checkpoint and must remain behaviorally unchanged. The isolated-
backend exceptions remain explicit and keep their separate containment proof. Nested
effects never inherit a blanket parent approval: R4 persists stable parent/child
`tool_call_id`/`effect_id` values before dispatch or fails closed. Unknown cost is not
zero; an unbounded cost-bearing call is denied before dispatch, and missing actual
usage stops later spend in the same task/run until reconciled.

## Memory writes

```text
[MW-01] Session start
   +-> [MW-02] run_agent MemoryStore loads profile MEMORY.md/USER.md
   |             -> built-in tool writes + frozen prompt snapshot [AUTHORITATIVE]
   +-> [MW-03] configured memory.provider present?
                 +-- no --> no MemoryManager
                 +-- yes -> [MW-04] MemoryManager orchestrates at most one external provider
[MW-05] Turn
   +-> [MW-06] MemoryStore add/replace/remove
   |             -> injection scan + lock + atomic current-value write/spillover
   +-> [MW-07] external MemoryManager prefetch_all -> sanitized context + proof trace [PATH GAP]
   +-> [MW-08] add/replace metadata -> configured external on_memory_write mirror
[MW-09] immutable built-in provenance/supersession/promotion tiers [ABSENT]
   - - R5 ordinary candidate memory + exact single-use owner decision - -> curated
   - - identity/persona or implicit promotion -> unavailable/deny; protected bytes fixed
```

- MW-02/03/04: `run_agent.py:1913-1998`; `tools/memory_tool.py:52-58`,
  `114-149`, `518-547`; tests in
  `tests/tools/test_memory_tool.py:102-253`.
- MW-04/07: `agent/memory_manager.py:193-251`, `288-333`, `568-586`; tests in
  `tests/agent/test_memory_provider.py:145-250`.
- MW-07: its `Path.home()` trace path at
  `326-331` is a specific profile gap; test: `tests/agent/test_memory_prefetch_trace.py:26-38`.
- MW-06: `run_agent.py:10478-10502`, `11106-11129`;
  `tools/memory_tool.py:311-380`.
- MW-08: `run_agent.py:4358-4382`; `agent/memory_provider.py:262-278`;
  `agent/memory_manager.py:488-542`. Remove is not mirrored by the current bridges.

Ownership: the `run_agent.py` `MemoryStore` remains the separate built-in authority;
snapshots stay stable mid-session. `MemoryManager` exists only for a configured
external provider and orchestrates that provider; it does not own or contain the
built-in store. R5 makes protected identity/persona promotion unavailable; any future
expansion would require separate owner review. The provenance envelope is additive
around both paths, not a memory replacement.
R5 tests two isolated non-live `SHAY_HOME` profiles and distinct session namespaces;
session, parent-session, task, and tool-call IDs remain provenance. Multi-tenant
memory authority is absent and outside the R5 claim. R5 never auto-promotes on write,
recall, repetition, confidence, restart, model output, or provider mirror.

## Four client adapters

```text
[CA-CLI-01] Classic CLI -- ShayCLI.chat/process_command --+
[CA-TUI-01] Ink <-> JSON-RPC tui_gateway ---------------+--> [CA-CORE-01] AIAgent
[CA-API-01] aiohttp HTTP/SSE /v1/runs [PARTIAL] --------+
[CA-ACP-01] ACP + SessionDB conversation restore -------+

[CA-CONTRACT-01] shared versioned domain objects [ABSENT]
 task/run/session/event/approval/usage/error; Phase 6 ADR selects one owner
[CA-SERVICE-01] R6 public seam [TARGET]
 inspect_task | list_task_events | cancel_task | retry_task | resume_task
   -> R3 Kanban truth; R7 consumes this seam, never direct client-local lifecycle state
[CA-OPTIONAL-01] effect | memory_provenance [TARGET]
 absent = unavailable; populated = versioned + authority-bound
```

- CA-CLI-01: `cli.py:2280`, `7238-7500`, `10152`;
  `shay_cli/commands.py:45-315`; tests: `tests/shay_cli/test_commands.py:46-57`.
- CA-TUI-01: `ui-tui/src/gatewayClient.ts:124`;
  `tui_gateway/transport.py:67-219`; `tui_gateway/server.py:2996-3030`,
  `4446`, `5445-5505`; tests: `tests/tui_gateway/test_protocol.py:369-495`.
- CA-API-01: `gateway/platforms/api_server.py:578-618`, `2738-2910`,
  `3099-3287`; tests: `tests/gateway/test_api_server_runs.py:1-8`, `202-468`.
- CA-ACP-01: `acp_adapter/server.py:445-475`, `1071-1155`;
  `acp_adapter/session.py:169-242`, `476-548`; tests: `tests/acp/test_server.py`.
- CA-CORE-01: `run_agent.py:1029`, `11597`, `15473`.
- CA-CONTRACT-01: no current shared schema owner or real four-client fixture.

Ownership: AIAgent remains the common core. `COMMAND_REGISTRY` remains authority for
built-in CLI/gateway vocabulary; plugin commands, ACP-local slash commands, and
documented TUI routing exceptions remain separate supported surfaces. Current
transports stay. The dashboard keeps the real TUI and must not create another
transcript/composer. Runtime capability claims require availability evidence, not
source presence. R6 owns the adapter-neutral five-operation seam; R7 presents it
through the existing plugin command surface without querying Kanban directly.

## Program dependency and evidence flow

```text
[PB-V1] drive-documents-v1: R0 base + board links recorded
   -> ledger st_nlink=2 -> BLOCKED + RETIRED_READ_ONLY
[PB-V2] local-state-v2: genesis + R0-R8 relinks recorded honestly
   -> key derivation dropped literal R -> :0..:8
   -> INVALID_SETUP + RETIRED_READ_ONLY; no task/ledger repair or mutation
   -> unsuffixed Python environment now RETIRED_READ_ONLY after 5 post-freeze pyc writes
[PB-V3] ledger genesis + named board + exact R0..R8 tasks already initialized
   -> R0 E0006 + R0 E0007 + R1-R8 E0004 relinks already appended
   -> exact frozen 40-row trace SHA cdd456f0...
   -> R0 E0008 retained as TIMING_INVALID history (copied start/end timestamps)
   -> [PB-01] v3 ledger/board/tasks/artifacts validated read-only; never recreate/repair
   -> [PB-02] immutable v4 Python 3.11 all+dev environment finalized
   -> [PB-03] pre-lock/full manifests + removed write bits + root digest validated
   -> [PB-04] E0009 verification_invalidated appended
   -> [PB-05] E0010 environment_relinked to v4 manifest/provenance appended
   -> [PB-06] E0011 verification with captured command intervals appended
   -> [PB-06A] R1-R8 E0005 environment_relinked rows append
   -> [PB-06B] R1-R8 E0006 test_contract_relinked rows append
   -> [PB-06C] R8 E0007 freezes Phase 0 governance and exact R8 paths; trace now 60 rows
       -> all eight remain proposed; no implementation started; R1-R7 E0006 and R8 E0007 bind v4 plus exact self-contained commands/path manifests
   -> [PB-07] every prior candidate INVALIDATED/UNREVIEWED in place
       (the registry tail is exhaustive; static examples are intentionally omitted)
   -> [PB-08] fresh tree -> stored index -> authored blobs -> complete binding
   -> [PB-08A] issue a content-addressed immutable mode-0400 R0 preparation journal
       through its append-only issuance registry before creating any candidate staging directory
       -> build only below that transaction-owned staging path -> issue immutable seal
       -> recover every exact publish/invalidation/registry/pointer/selected-record step
       -> ledger-lock append candidate-selection registry -> atomic active pointer
       -> exactly one candidate directory lacks invalidation.json
   -> [PB-09] PENDING: three separately dispatched results resolve pointer; local tooling proves distinct artifacts/IDs, not cognitive independence

[R0 3 reviews + one C + verified remote equality + explicit CI-N/A bootstrap + board done + ledger completion]
   -> R1 full chain -> R2 full chain [READ-ONLY V3 BOARD AUDIT]
                        +-> R3 full chain --+
                        +-> R4 full chain --+-- BOTH terminal chains required
                                             +-> R5 memory (bases R4 C) --+
                                             +-> R6 clients (bases R3 C) -> R7 full chain --+
                                                                                          |
                                     R8 bases complete R7 C, integrates complete R5 C <---+

Each R1-R8 branch:
  require R1-R8 E0005 environment rows + current R1-R7 E0006/R8 E0007 test-contract rows -> exact active-v4 interpreter/provenance/manifest/root
  v3 external-ledger-proven dependency C -> implementation_base_sha
  + listed reviewed integrations -> integration_base_sha
  -> FIRST authored write: exact phase-local append-only events.jsonl
  -> resolve exact active-v3 relinked board task -> implementation -> verification
  -> run-phase-tests materializes the exact Git tree in a fresh no-hardlink checkout
     -> split Node workflow: exact npm-ci acquisition may use unrestricted network;
        type-check/test/build and all other local steps remain OS sandbox network-denied
     -> default-deny all file writes; allow only exact fresh temp/output and declared
        isolated Node dependency/build directories; deny novel and symlink-escaped paths
     -> issue immutable tool-owned argv/env/timing/exit/stream/artifact + checkout before/after receipts
  -> tool issues the exact terminal phase-evidence row; caller PASS is forbidden
  -> evidence binds tested source content excluding its own path/R8 proof; the final tree is external only
  -> only that append-only receipt-bound evidence, plus the fresh derived R8 proof, may differ from the tested Git tree
  -> build-phase-select checks eligibility before mutation and writes a durable journal first:
     prepared -> pending-published -> candidate-published -> receipt-consumed -> selected
     (resume reconciles intended hashes with actual receipt/registry/invalidation/pointer state;
      every fsync/rename/append crash window completes without receipt loss/double consumption)
  -> atomically publish candidate tree + schema-v5 binding
     (exact ledger-derived dependency Cs + frozen phase_contract Git blobs/manifests/tests)
     (category-sensitive pre-stage inventory, authored blobs, ignored baseline/current,
      live-profile before/after, submodules, v4 provenance/full manifest/root digest,
      binary/full-index diff)
  -> reviewers emit immutable typed results; recorder appends passed or failed projections
     (review retry emits review_set_superseded; new candidate emits candidate_superseded)
  -> require ready + add phase_gate=review comment; no invented review status
     -> record-kanban proves candidate snapshot + exactly that add_comment row/event and no other delta
     -> ready-without-run complete_task creates task_runs.status=completed,outcome=completed
  -> require the exact final authorized real-index staged transition; tree/diff/blob + stable non-tree bindings match
     (local evidence does not claim a number of git-add invocations)
     (post-stage categories are captured, not compared to pre-stage categories)
  -> candidate closure revalidates captured pre-review board/ledger leaves, not mutable live board bytes
  -> stage exactly the reviewed paths, then prepare-commit validates the authorized review suffix
     + sole-recorder review comment/event and binds staged path/blob/mode/tree/diff/index/invariants
  -> prepare-commit issues exact raw commit-tree stdin/env/cwd/argv + expected C + CAS update-ref argv
  -> record-commit revalidates receipt + full active closure/results/tool + authorized board/ledger delta
     + actual raw C bytes/tree/index/one parent/message/author/committer/branch
  -> R0: record-push-bootstrap proves origin equality and records CI-not-applicable-bootstrap
  -> R1-R8: record-push-ci derives origin/GitHub via stdlib HTTPS/TLS and proves workflow-ID/path, push run, exact jobs, and artifact metadata only
  -> R2 reconcile executes only the reconciler blob materialized from accepted C in a shared-write-denied sandbox; failure is retryable
  -> record-kanban imports only accepted-C public complete_task, proves 9 tasks/11 links,
     issues a protected derived-path journal, then calls complete_task on the real program DB
     through native SQLite BEGIN/COMMIT/WAL coordination; it never replaces the DB inode
  -> crash recovery queries the exact result, failure reset, completion event/run,
     dependent promotions, idempotency, prior history, and existing ledger row before resuming
     prepared -> domain-applied -> ledger-appended, including ledger-fsync-before-journal-mark
     -> the accepted-C public operation runs inside one outer SQLite BEGIN IMMEDIATE/COMMIT;
        its internal write scopes join that transaction, so completion, failure reset, run closure,
        and dependent promotion either all commit or all roll back
  -> repository bytes and tip stay fixed at C; C remains dependency tip
  -> PR creation/review/merge remains an optional later owner-authorized handoff

R8 pre-candidate cutoff and terminal sequence:
  validate R1-R7 phase files through verification + complete external chains
  -> freeze external-ledger prefix/hash chain and board read-back
  -> copy repository pre-review lines byte-for-byte into canonical trace
  -> proof writes external temp artifact; tool derives six semantic evidence kinds from
     issued receipts/Git/lifecycle/safety observations and copies validated bytes into candidate
     (actual executed/passing command count remains separate from the six evidence kinds;
      no digest refers to discarded raw runner bytes)
  -> status/evidence names the cutoff and honestly marks R8 terminal facts pending
  -> freeze one R8 candidate; three identical external reviews
  -> record-commit -> provider-verified remote + mandatory branch CI success -> accepted C
  -> task done/read-back
  -> record-finalize retains the immutable PRE-REVIEW board/ledger snapshot, recomputes
     the full POST-COMPLETION schema/table/task/event/task_run projection and accepts only
     valid supersession history followed by the exact active R8 three-pass/commit/push/
     complete_task delta; invalid and superseded candidates remain ineligible
  -> replay the immutable candidate-wide retry budget before any provider call
  -> recompute C/tree/index, proof, trace and freshly re-query every accepted remote/CI
     only through the ledger-issued query plan
     (raw bytes independently entail the normalized anchor; idempotent retry keeps them only
      below the disposable run root, removes them after comparison, and changed facts fail)
  -> append external program_finalized; never move repository bytes/tip after C
  -> identical rerun is read-only; changed/later inputs fail
```

A pushed candidate with failed mandatory CI retains its implementation_commit_recorded row
but is not accepted as a dependency C. Provider-backed ci_verification_failed records an
explicit blocked attempt while the Kanban requirement deliberately remains active ready/running.
`start-successor` validates the ledger-bound failed-CI provider observation and its exact
local Git DAG commit/tree/base facts; a fresh distinct-branch selected/reviewed successor
emits candidate_superseded tied to that failure. Every later successor/no-op/terminal
recorder repeats that ledger-plus-local proof without an undeclared network call. The old
passes/commit become ineligible, and branch reuse or inclusion of the failed tip in the
accepted successor DAG fails. The terminal provider reads are authorized only by their
single issued query plan and charged to its candidate-wide observed-byte budget.

R3 and R4 may run in parallel only after R2's full external completion chain. R5 and
R6 may run in parallel only after both R3 and R4 each have three candidate-bound
reviews, one C, verified push C, board done/read-back, and external completion: R5 inherits R4's `run_agent.py` safety seam and wires
provenance through the real built-in `MemoryStore`, while R6 inherits R3's durable
API/Kanban work plus the already reviewed R1 package-lock/launcher repair through its
dependency ancestry. R6 may edit only its gateway client and focused gateway test in
`ui-tui`; the inherited R1 baseline files stay read-only. R4/R5 and R3/R6 shared paths are serialized inheritance, not
concurrent writes. R8 integrates the reviewed R5 delta into reviewed R7 ancestry.
R7 therefore sees R3/R6 truth but not R4/R5 truth: its operator view reports typed
checkpoint/effect and memory-provenance fields as unavailable until R8 integration.
Its bundled plugin remains disabled by default, and plugin command registration does
not imply presence in classic global help, `gateway_help_lines`, autocomplete, or TUI
`commands.catalog`.

Before candidate freeze, each parallel pair meets at a receipt-bound compatibility
barrier. R3+R4 deterministically composes their tested trees over the common R2 base
and exercises approval/cancel/restart. R5+R6 starts from that accepted composition,
applies the R6 delta relative to R3 and then R5 relative to R4, and exercises absent
and populated optional effect/memory-provenance fields. The existing test-receipt
registry binds every base/input/composed tree, exact argv/result/artifact hashes, and
the same receipt hashes into both paired candidate closures. Input drift invalidates
both. Maximum phase concurrency remains two; R8 revalidates rather than invents these
compatibility facts.

The canonical trace starts with an exact immutable 29-row archived-attempt prefix at
full SHA-256 `4cfe0dcfc84051f3f02fa721e0b87fbbb19c859442f816cd8741f5ffbaeffa9f`.
Its first 19 v1 rows also retain prefix SHA-256
`53f6e9f7ef1984a36d9c2ec21a253b083eb2a2109661573fe16464483d8e0b39`;
rows 20-29 preserve the v1 block and invalid-v2 relinks exactly. The only compatibility
exception is those exact bytes. Rows 1-40 are additionally frozen byte-for-byte at
SHA-256 `cdd456f0deddf68134554c8acfbb4116a98b6cf68cea941b4d14b1bcacbe0c1f`.
Rows 30-39 prove E0006, E0007, and all exact-key active-v3 relinks occurred. Row 40
E0008 is preserved but invalid as active verification because its start/end values
were copied from the record time. E0009 invalidates that claim, E0010 binds immutable
v4 provenance/full-manifest/root-digest evidence, and E0011 records captured passing
intervals. R1-R8 E0005 append active-v4 bindings, then R1-R8 E0006 append initial
self-contained command/path contracts without starting implementation. R8 E0007
freezes the Phase 0 capability contract and plan as non-writable R8 authority, adds
the final checklist, and requires an explicit external proof output. R1-R7 E0006 and
R8 E0007 are current, bringing the trace to 60 rows; no prior row is rewritten. The
trace contains only pre-review facts through verification. R2 deterministically reconciles it and the exact
phase-local path map with the board and external execution ledger; it discovers
nothing heuristically and mutates nothing. The external ledger alone stores the three
review results, implementation C, verified remote C, task completion, reconciliation,
and R8 finalization. Since Git receives no post-review facts, one candidate is reviewed,
committed, and pushed once without self-reference.

The active program board and execution ledger are operational state outside Git at
`/Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3`.
The current source resolver places its named-board database at
`kanban/boards/shay-agent-enhancement-2026-09-13/kanban.db` below that root. Each
phase may update only its own task; R2 never writes; R8 exports status but never
automatically deletes or archives the board. These writes are not Git changed paths
and never authorize the live `/Users/famtastic-fritz/.shay` tree.
Setup uses a scrubbed environment: it pins `SHAY_HOME`, `SHAY_KANBAN_HOME`, and
`SHAY_KANBAN_BOARD`, rejects direct DB/workspace overrides, and resolves/asserts the
root, metadata, DB, workspaces, and logs below the exact root before any write. If a
board path exists, raw metadata plus a read-only SQLite task/link audit must match
before `create_board`, `connect`, `init_db`, or any update; mismatches fail closed.
The v3 root is initialized with one genesis event and nine exact `:R0` through `:R8`
tasks. The external setup artifacts, R0 E0006/E0007, and R1-R8 E0004 relinks are
historical facts to validate idempotently, never setup work to repeat. The v1 and v2
program-state attempts remain write-prohibited. The unsuffixed v2 Python environment
is also retired read-only after five post-freeze pip `__pycache__` mutations; current
nlink 1 does not reactivate it, and the v1 ledger's nlink 2 remains a historical block.
The active v4 environment is finalized and locked read-only with a full manifest and
root digest; E0009/E0010/E0011, R1-R8 E0005/E0006, and R8 E0007 test-contract rows are appended. Candidate discovery is
an explicit locked hash-chain, never newest-directory-wins:

```text
[CS-01] shared execution-events.lock
   -> validate candidate-selection.jsonl from byte zero + prior-line hash chain
   -> validate active-candidate.json registry hash + last event + binding path/SHA
   -> inventory every 40-hex directory
      +-- pointer target: no invalidation.json -> exactly one ACTIVE
      +-- all others: strict immutable mode-0400 invalidation.json -> INVALIDATED
   -> validate every supersedes value as lowercase 40-hex
   -> require last-row supersedes == exact set(all inactive 40-hex directories)
   -> unique external disposable root + private mode-0600 stored-index copy
   -> validate immutable candidate-local ledger prefix; accept only a strict appended suffix
   -> R0: verify full documentation/research closure
   -> R1-R8: load bound phase authority; recompute rename-aware paths/authored blobs,
      pre-stage inventory/submodules/v4/protected identities and phase-event chain
   -> prove sequential base is exact or parallel base is exact primary-first reviewed-tip merge
      with Git's deterministic conflict-free tree and no extra/manual authority
   -> load immutable test-command receipts; reject missing/forged PASS strings or artifact drift
   -> validate bound build-time live before/after manifests without reading current ~/.shay
   -> remove private copy; prove stored index unchanged
   -> recompute complete live-v4 manifest/root after review
   -> prove v4, registry, pointer, repository, and disposable-root cleanup unchanged
```

The selection registry and pointer remain outside the Git candidate binding, so no
circular hash exists. The registry tail is the sole exhaustive authority for preserved
invalidated/unreviewed history; this static document contains no candidate list. The
pointer-selected fresh candidate binds a stored mode-0400, `UF_IMMUTABLE` index and is
pending three external reviews. There is no
Kanban `review` status in `VALID_STATUSES`: the review gate is an exact task comment,
with the task required to remain dependency-derived `ready`; any other state blocks.
A task becomes
`done` only after its reviewed implementation commit exists and the feature-branch
remote SHA is verified equal; that completion and all other terminal facts append only
to the external ledger under its strict lock/fsync/hash-chain protocol.

## Closed review procedure

```text
review_phase0_candidate.py + the build support and recorder command it actually calls
+ metadata + validation + E0009/E0011 evidence + operational note + authored blobs
+ build-time live/ignored content sentinels + board snapshot + ledger prefix/anchor
+ failed-review evidence + copied research notes + pinned GitHub content snapshots/manifest
  (successors reuse only the validated immutable selected snapshot; an uncached exact fetch has a hard 90-second timeout and cannot publish partial evidence)
+ v4 verifier/manifest/summary/provenance + every hashed/mode-bound input
                         |
                         v
              review-procedure.json (0400)
                         |  path + SHA + format + mode
                         v
              candidate-binding.json (0400)
                         |  SHA only; no reverse reference
                         v
 candidate-selection.jsonl -> active-candidate.json

candidate-metadata.json contains neither binding SHA nor procedure SHA. The sole bound
`review_phase0_candidate.py` validates pointer/registry/inactive-set twice, every procedure
leaf/metadata field, full documentation and board proof, and the immutable ledger prefix plus
any valid append-only suffix. Reviewers emit standalone mode-0400 results containing the
verifier/procedure hashes and measured pointer-verification proof. They do not append.
A distinct `record-reviews` invocation validates one to three immutable result artifacts,
identities, hashes, and timings under the exclusive lock. It records failures immediately,
resumes partial batches, and emits explicit review-set/candidate supersessions. The immutable
candidate procedure keeps its captured pre-review board/DB leaves; after the exact review
comment/event, the commit agent stages only the reviewed manifest and `prepare-commit` issues a
content-addressed deterministic commit-tree plus compare-and-swap ref authorization. `record-commit`
replays that exact transition and raw C before gating the active selected tree; R0-only `record-push-bootstrap` records remote equality with
CI-not-applicable-bootstrap; R1-R8 `record-push-ci` obtains origin/GitHub workflow/run/jobs/artifact
bytes in a disposable root and embeds their single-timestamp content-addressed observation directly
in the ledger event; `record-reconciliation` and `record-kanban` are the sole terminal writers for those facts;
R8-only `record-finalize` first replays immutable exhaustion/budget state before any provider call,
then recomputes repository/proof/trace/board/ledger and re-queries provider facts only through
the active ledger-issued query plan. Immediately before each provider primitive it appends a
durable query-start reservation for the exact identity, invocation, and maximum byte charge,
then appends the matching completed/failed/interrupted query result. Failed-attempt ancestry uses the ledger-bound failed-CI
provider observation plus the local Git DAG and performs no parallel `ls-remote` query.
Any drift fails; disposable index/copy roots are removed.
```

R0 selection uses content-addressed immutable mode-0400 prepared, sealed, and selected
documents recorded by a mode-0600 append-only issuance registry. The prepared document
exists before any candidate staging directory and restricts it to one exact transaction-owned
path. `resume-select` accepts only that exact issued v2 preparation and its issued seal when
present; an arbitrary shaped candidate directory fails before read, rewrite, cleanup, or
selection, and no legacy pre-journal resume route exists. Only a complete sealed staging tree may be published; its seal binds candidate artifacts,
index, selection row, invalidations, registry/pointer bytes, and deterministic same-directory
temporaries. Recovery first requires the discovered preparation set to equal the independently
issued preparation rows byte-for-byte; an unissued or missing document fails before cleanup,
abandonment, registry append, or selection mutation and can never gain authority by discovery.
For issued transactions, recovery verifies exact before/after hashes, completes already-applied publish,
invalidation, registry, pointer, and selected-record steps in order, fsyncs their parents,
and fails on divergent or unowned state. An unsealed preparation from a superseded tool is
closed by an immutable issued abandoned record. A crash before staging is bound as
`preserved_absent`. When the exact journal-owned stage exists, its no-follow root descriptor is
held while readable top-level bytes and inode metadata are revalidated. A mode-0400 retained-
authority child stays opaque: only its directory identity and sorted child-name namespace are
recorded, descendant bytes are explicitly uninspectable, and nothing is chmodded, traversed,
repaired, deleted, published, or selected.
A superseded-tool preselection seal can use the same fail-closed path only when its original
main registry/pointer are exact and neither candidate publication nor invalidation occurred;
the sealed abandonment record binds both immutable preparation and seal bytes.
R1-R8 use the longer receipt-
consuming journal shown above; generic cleanup preserves a valid prepared staging path.
The bound Round 14 audit identifies the former index-mode writer precisely: a reviewer gave
the authoritative index path to `git write-tree` without `GIT_OPTIONAL_LOCKS=0`, and Git's
lockfile rename preserved content while replacing inode/mode with 0644. That invalidated
artifact is not repaired. New candidate indexes are atomically published 0400, sealed
`UF_IMMUTABLE`, and stressed across three concurrent Git attempts before review.

The candidate also binds the sole schema-v25 self-test's sorted current-property inventory
of directly executed behavioral acceptances/counterexamples; source-literal checks have no authority. A separate exact
schema-v4 78-label `legacy-test-case-map.json` is a retired non-authoritative historical
inventory only; it makes no equivalence or acceptance claim. Current properties alone gate
capture, and no retired self-test body remains callable.

Receipt, preparation, and registry parents are acquired through descriptor-relative no-follow
directory walks. Publication and fsync stay anchored to the verified parent descriptor, so a
preplanted symlink directory cannot redirect a receipt or registry write. New-name directory
publication uses `renameatx_np(RENAME_EXCL)` and refuses a target that appears at the syscall.
Existing-authority replacement uses `RENAME_SWAP`; the displaced exact old inode is sealed
mode `0400` in a deterministic content-addressed `.shay-retained-authority` slot and is never
unlinked. Recovery accepts only the exact installed/replacement plus retained/prior tuple.
Concurrent target divergence is atomically swapped back without deleting or rewriting either
the foreign entry or the verified prior authority. Selection transaction `temporary_path` fields
remain schema-bound legacy-reserved values: the current tool never creates, selects, rewrites, or
deletes them, and any such pathname fails closed.

The exact structural CLI is
`review_phase0_candidate.py --repo /Users/famtastic-fritz/Development/FAMtastic/shay-shay --base cf6bb95e3dc12e0d4b8eadef2c33be2b39ad21b6 --pointer /Users/famtastic-fritz/.local/state/shay-agent-enhancement-2026-09-13-v3/evidence/candidate-bindings/SHAY-AGENT-R0/active-candidate.json --run-root <fresh-absolute-external-root> verify-pointer --output <fresh-absolute-result-path>` inside the contracted scrubbed `/usr/bin/env -i` envelope. A typed review replaces the final verb with `review --review-type verification|anti_pattern|quality --reviewer <identity> --dispatch-id <orchestrator-task-id> --decision passed|failed --findings-json <closed-findings-json> --output <fresh-result-path>`; `--dry-structural` performs no review record.
The dispatch ID grammar accepts either slash-path orchestrator IDs or their safe encoded
forms such as `root-r0-final-verification-round10`, with one closed 255-character limit;
the ledger recorder enforces global non-reuse across batches and supersessions.
Every run root begins as one empty mode-0700 owned directory and receives a closed ownership
marker binding its exact path/inode/tool before any child is created. Run roots, findings, and
outputs must be disjoint in both containment directions from the repo, v3/v4/live/Obsidian
trees and the complete durable Shay transaction-authority root. Symlink/realpath overlap fails.
Cleanup first validates that marker and preflights the complete tree for ownership, hardlinks,
special files, and immutable flags before deleting an entry. It never chmods a path, requires
Python's descriptor-relative symlink-attack-resistant `rmtree`, and fails closed if the
platform lacks that primitive; an unmarked nonempty directory or partial immutable seal fails
without partial cleanup, while a child/root symlink swap cannot mutate the outside target.
The later recorder replaces the final verb with `record-reviews --recorder <distinct-identity> --result <one-to-three immutable results> --output <fresh-recorder-result.json>`; it accepts no decision or findings arguments. Future phases use `run-phase-tests --output <fresh-result.json>`, `build-phase-select --receipt-id <64-hex-issued-id>`, or `resume-phase-select --candidate <orphan-directory>`. The sole writer also exposes `prepare-commit --actor <identity> --output <fresh-result>`, `record-commit --actor <identity> --staging-receipt-id <64-hex-issued-id> --output <fresh-result>`, R0-only `record-push-bootstrap`, R1-R8 `record-push-ci --actor <identity> --github-token-file <mode-0400-external-path> --output <fresh-result>`, R2-only `record-reconciliation --actor <identity> --report-output <fresh-durable-external-path>`, `record-kanban --actor <identity>`, and R8-only `record-finalize --actor <identity> --github-token-file <mode-0400-external-path> --output <fresh-result>`. `prepare-commit` is after exact staging and returns the only authorized raw commit-tree stdin/env/cwd/argv and CAS `/usr/bin/git -c core.hooksPath=/dev/null update-ref ...` command; a normal `git commit`, hooks, signing, or caller-chosen message is outside the contract. There is no retry-authorization verb: a candidate-wide finalization budget exhaustion requires a separately reviewed future code/config change outside this automation.
Bootstrap and provider-backed push verbs form one closed content-addressed provider observation
inside the ledger event, containing canonical raw query/response bytes, their content hash, one
authoritative timestamp, and the normalized semantic projection. Replay independently derives
the provider/repository/query/workflow/run/branch/head/event/status/conclusion/job/artifact
projection from the raw bytes and requires exact equality with the ledger anchor; inconsistent
facts fail. GitHub HTTPS uses a dedicated stdlib opener whose redirect handler rejects every
301/302/303/307/308 before a Location request can be sent, so Authorization is never forwarded;
a 30x is closed as irrecoverable provider semantic-integrity evidence under its issued query.
raw success/failure data fails. An idempotent push/bootstrap no-op still re-queries and validates
fresh raw bytes, compares only normalized semantic facts, then removes the disposable run root.
A terminal `program_finalized` no-op instead fully replay-validates and returns its already-bound
snapshot with zero provider calls because post-terminal reservation rows are forbidden. The lifecycle ledger `remote_ref` directly binds the original exact
observation; no separate registry, durable caller path, split clock, or orphan receipt can
become authority.

R8 terminal revalidation is a separate freshness-bound operation with the execution
ledger as its only durable transaction and evidence authority. While holding the existing
no-follow ledger lock, `record-finalize` atomically appends
generation 1 `program_finalization_query_issued` before any provider call, or an in-budget contiguous
generation after a bound retry-exhaustion closure. Each schema-v4 issue row binds the accepted
candidate tree/binding/tool, a cryptographic nonce and issue time, the exact completed pre-final
prefix/count/tip/time, nine provider/repository/remote/branch/ref/head targets, generation-unique
derived query IDs, a fixed 30-second absolute wall-clock deadline per request, fixed per-response
and aggregate byte caps, its candidate-global generation,
and the exact preceding exhaustion when applicable.

Immediately before each provider call, the finalizer atomically appends
`program_finalization_query_started`. That row binds the issued query identity, exact
argv/cwd/scrubbed-environment/no-shell descriptor or HTTPS request descriptor, the attempt/call
sequence, and a conservative maximum observable-byte reservation; the first start charges the
attempt before I/O. One matching `program_finalization_query_result` binds completed, failed, or
interrupted evidence. A completed result replaces its reservation with actual observed bytes.
An unmatched started row is recovered as interrupted at the full charge; a matching result with
no later attempt closure is deterministically failed before any new provider call. The finalizer
then streams the issued queries in memory, concurrently capping stdout and stderr for
`git ls-remote` and capping every stdlib-HTTPS response while bytes are read. HTTPS DNS/connect,
headers, and every body read share one absolute monotonic deadline; a slow drip cannot reset it.
A single stream is limited to 8 MiB and the whole nine-query attempt to 64 MiB; overflow or
deadline closes/terminates the producer.
A network, provider, credential, signal, timeout, rate-limit, or bounded-output failure atomically
appends `program_finalization_query_attempt_failed`, not a terminal closure. That row embeds
byte-preserving base64 stdout/stderr/diagnostic data, exact observed/retained counts and hashes,
truncation flags, exit/signal/timeout/provider status, query identity, actual UTC request start/end,
measured monotonic elapsed. A failed row retains no successful response prefix and jointly caps
stdout, stderr, and diagnostic bytes at 64 KiB. Attempts below sixteen reuse the same nonce/query
plan. Each outer attempt increments once at its first provider call and has a closed ordered prefix
of at most 49 independently reserved calls: R0 remote equality, then remote/workflow/runs/run/jobs/
artifacts for each R1-R8. Its call sequence resets to one; a 50th, repeated, skipped, or reordered
provider call fails before I/O. The exact sixteenth transient failure is followed by
`program_finalization_retry_exhausted`, binding all sixteen attempt rows and closing the generation.
Only then may a later invocation issue the next monotonically numbered generation while the
candidate-wide automatic budget remains below three generations, 48 started attempts, and 64 MiB of all
observed or conservatively reserved provider bytes, including the cap-trigger byte rather than only retained/truncated evidence.
Every successful git/HTTP wire body is preserved and byte-recomputable; failure rows distinguish
observed and retained counts under the smaller 64 KiB retention cap. At that boundary
`program_finalization_retry_budget_exhausted` records exact active issuance/attempt and counters,
returns `blocked_needs_owner_action`, closes the pending issuance, and grants no query; no automatic retry authorization
or same-UID JSON override exists. Repeated invocation is a zero-provider-call,
byte-idempotent blocked result. Under the same replay/lock boundary, a later
successful active-generation attempt appends
`program_finalized` with all nine canonical raw responses and independently derived facts.
`program_finalization_abandoned` is reserved for irrecoverable issued-plan or semantic-integrity
failure and embeds its recomputable raw failure evidence. Every terminal binds the issuance and
all intervening attempt rows by event ID, sequence, exact-line hash, and transaction ID.
There is no separate finalizer directory, registry, seal, object namespace, rename, cleanup, or
deletion path, so filesystem residue cannot acquire authority.

A crash before issuance leaves nothing. A crash after issuance resumes only that ledger row,
with the same nonce and query plan; a crash after a started row closes it as interrupted at its
full reservation, and a crash after a result closes the consumed attempt without replay. A crash after the maximum attempt appends its deterministic
exhaustion closure before any successor issue. No second generation is pending concurrently,
candidate-wide counters never reset, and query IDs never repeat across generations. Forged,
parallel, missing, replayed, or over-broad authorization fails. Retryable attempts and exhausted generations remain
nonterminal rather than falsely reporting program completion. A crash after the terminal
atomic append is an idempotent retry. Already-finalized is detected through a pure local replay
of the exact genesis, canonical full lifecycle, global dispatch/idempotency chains, every
started/result reservation pair, immutable selected binding and R8 completion relationship
before issuance, Git, or provider I/O; it returns the existing snapshot with zero subprocess
or provider calls and ledger bytes stay unchanged. Replay rejects missing, duplicated,
replayed, oversized, or
tampered issue/raw/normalized/query evidence and every post-terminal event.

## Protected-custom phase gate

```text
[PC-01] enter phase with exact allowed-path packet
   -> [PC-02] verify SHAY-PROTECTED-CUSTOM-BASELINE-v1 at cf6bb95e
   -> [PC-03] SHA-256 PERSONA.md + SOUL.md + docker/SOUL.md
   -> [PC-03A] capture ignored status + ignored-file manifest outside repo
   -> [PC-04] record primary tip as implementation_base_sha
   -> [PC-05] integrate only listed reviewed commits; record integration_base_sha
   -> [PC-06] first authored write is the exact phase-local evidence JSONL
   -> [PC-07] work only inside packet allowlist; every unlisted path is read-only
   -> [PC-08] validate category-sensitive pre-stage inventory + ignored/live/submodule/v4 state
        + authored integration-base diff + transitive inherited manifest union + hashes
        +-- mismatch -> [PC-10] stop; append blocked evidence
        +-- match ---> [PC-09] disposable build index seeded from HEAD; stage exact paths
                            -> FIRST write candidate tree
                            -> copy build index to authoritative stored mode-0400 + UF_IMMUTABLE index
                            -> THEN derive authored-blob manifest from candidate tree
                            -> complete binding with diff + non-tree state + stored-index metadata
                            -> each reviewer copies stored index to a private disposable file
                            -> Git sees only disposable copies with GIT_OPTIONAL_LOCKS=0;
                               stored artifact stays byte/metadata/flags unchanged under concurrent review
                            -> three standalone immutable review results bind identical hashes/refs
                            -> separate recorder validates artifacts/types/identities/proof timings
                            -> append three result-bound ledger rows under the exclusive lock
                            -> commit agent establishes the exact final authorized staged path/tree state first
                               (no unprovable git-add invocation count)
                            -> tree/diff/blob and stable non-tree state reproduce binding
                               (post-stage inventory category/hash captured as new evidence)
                            -> prepare-commit binds exact review-ledger + board-comment delta
                               and issues raw commit-tree bytes/argv/env + CAS update-ref
                            -> record-commit proves exact C bytes/message/identities/parent/tree
                            -> after push: clean porcelain-v2 + remote SHA equals C
                            -> only then board done + external completion; no Git append
```

The authoritative hashes and protected patterns are in
`docs/architecture/shay-custom-capability-contract.yaml` under
`protected_custom_manifest`; diagrams and trace rows refer to its manifest ID rather
than maintaining a second hash list.

Test execution is externalized. The committed `scripts/run_tests.sh --e2e` accepts
only caller-supplied absolute `SHAY_TEST_PYTHON` and `SHAY_TEST_ENV_PROVENANCE`,
validates Python 3.11 plus strict editable-`.[all,dev]` provenance, and rejects
repository-contained, live-Shay, retired, or fallback environments. This local
orchestration supplies the already finalized immutable v4 paths; CI independently
builds and attests an ephemeral environment below `RUNNER_TEMP`. Venvs, temp files,
caches, coverage, databases, logs, and scratch evidence stay below the caller's
external phase root. Before any Shay/pytest/stress/plugin import, `HOME`, `SHAY_HOME`,
`SHAY_PROMPT_MEMORY_VAULT`, and all Kanban overrides are scrubbed; then fresh HOME,
Shay-home, and prompt-vault descendants are pinned under that profile root. A second
profile proves no cross-profile spillover. Raw ignored-state
and per-file ignored manifests must match at entry, review, and commit. External
before/after sentinels over the live owner profile's path/hash/mtime metadata must be
byte-identical; no test touches `/Users/famtastic-fritz/.shay`. Every Python/pip call
sets `PYTHONDONTWRITEBYTECODE=1` and unique external cache/TMP variables. The complete
v4 lstat manifest covers every file, directory, and symlink with path, type, mode,
uid, gid, size, SHA-256/link target, and nlink; regular files have nlink 1, special
files are forbidden, and every regular file/directory is non-writable. Recompute the
manifest and root digest before/after every review and test; any drift blocks.

The applicable local set is only the current trace/plan command array plus its derived
assertions and, for the two parallel pairs, the tool-issued compatibility receipt.
Paired `run-phase-tests` stops at an immutable `awaiting_pair` packet. The R3 or R5
coordinator invokes the sole `run-pair-tests` verb with the exact pair ID and two
ordered member receipt IDs; the tool derives the accepted parents and composed tree,
runs the fixed command in an immutable sandboxed checkout, and publishes one shared
content-addressed receipt through a transaction-first, fsynced-temp/no-clobber-link,
issued-transaction-registry-first and pair-receipt-registry-last protocol. The first
registry row binds the complete self-addressed canonical prepared bytes before any
prepared pathname is eligible; recovery reopens the pending members and ledger and
rederives both final packets. Only that completed pair transaction emits each member's one
passing terminal evidence, with identical receipt bytes in both closures. R8 reopens
and recomputes both pair authorities and cannot create one. The receipt binds the
actual sandbox profile-byte hash and a failed network-denial probe;
focused/full/E2E/integration/stress labels never add or remove a top-level command.
R1 owns `.github/workflows/tests.yml` branch selection and `test`+`e2e` for the exact
R1-R7 branch names in `branch_ci_gate_map`; R8 alone adds its exact branch and
`shay-upgrade-proof`. A ledger-bound failed-CI successor may append only
`-successor-<64-lowercase-hex-attempt-id>` and inherits the same jobs. Unknown or
mismatched branches/jobs/heads fail.

Phase 0 commit authorization has a separate, non-recursive integration gate. A
first stage emits the complete current verifier suite and documentation result.
The top-level `prepare-commit-integration` command then dependency-injects only
disposable Git, selection, ledger, board, and receipt paths while invoking the
unchanged production build, three typed review, review recorder, board-comment,
exact-stage, and `prepare-commit` functions. Its content-addressed issued receipt
is copied into and bound by the next candidate; `prepare-commit` rejects a
same-tool candidate without that exact proof. Authoritative board DB/JSON reads
are held through no-follow descriptors, copied byte-for-byte to the disposable
run root, and only the copy is opened by SQLite in immutable/query-only mode;
authoritative `-wal` or `-shm` sidecars fail before projection. The integration
authority is serialized by a no-follow lock and appends its exact
content-addressed `prepared` transaction before Stage 2; the later `issued` row
references that preparation and immutable receipt, so an unregistered pathname is
never evidence and a crash retry cannot create a second transaction.

The previously closed cross-tool R0 selection is now history only. Its stored
hash chain, candidate, original producer archive, reconstruction provenance, and
recorded recovery-authorizer identity are reopened exactly; a later verifier does
not rerun that authorizer proof or treat it as fresh selection/commit authority.
Only a new same-tool candidate with its own Stage 1 and issued Stage 2 receipt can
supersede it, through one ordinary locked invalidation/selection transition.

R5's deterministic memory gate uses the reviewed 32-record/16-query fixture at
`tests/fixtures/memory_provenance_benchmark_v1.json`. In the same validated immutable
v4 Python environment and hardware, an offline `MemoryStore` protocol compares the reviewed R4
tip with the R5 candidate: one warmup, then five paired rounds with alternating order
and fresh isolated profiles. It requires provenance precision 1.0, zero required-field
omission, zero stale facts, median token p95 at most baseline*1.10+32, and median
latency p95 at most max(baseline*1.25, baseline+5ms). These technical thresholds are
fixed by the R0 implementation contract; merge approval remains separate.

R8's repository reporter is intentionally fail-closed. It requires an
explicit external execution-ledger path and a fresh external output path. An
incomplete R1-R7 lifecycle produces `launch-blocked`; it cannot derive review,
CI, completion, or `program_finalized` from branch tips or phase-local prose.
