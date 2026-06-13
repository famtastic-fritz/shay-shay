# Shay workstream control map — 2026-06-12

Status: planning only
Owner: Fritz + Shay-Shay orchestration
Execution rule: current live Shay on `main` is the source-of-truth product. `shay-platform-build` is preserved as a draft rewrite sandbox. Memory architecture is already merged into `main`.

## Executive control rule

Do not mix these concerns into one lane:
1. live product stabilization
2. Hermes removal
3. capability-awareness / routing honesty
4. rewrite sandbox evolution
5. promotion rules
6. swarm/ledger architecture

Each lane has its own purpose, allowed workers, evidence standard, and done criteria.

## Current reality snapshot

- Source-of-truth product lane: `main`
- Rewrite sandbox lane: `shay-platform-build`
- Live repo status: dirty on `main`; not safe to treat as a clean execution surface without classification
- Memory architecture: already merged into `main`
- Hermes: not the active runtime, but still present on disk and via callable wrapper / compatibility residue
- Capability surface: partially honest, not fully classified; some skills overstate runtime readiness
- Swarm doctrine: desired state is atomic parallelism with durable ledgers, but the ledger policy is not yet final

---

## Lane 1 — Live-main stabilization lane

Purpose:
- stabilize the current live Shay product on `main`
- finish `/model` switchboard stabilization
- classify dirty live repo files
- protect current product reality
- prevent accidental cross-contamination from Hermes removal or rewrite experiments

Current status:
- active source-of-truth lane
- dirty working tree exists
- model-selection/provider-resolution stabilization is not yet fully closed
- some dirty files appear product-relevant; some appear planning/artifact-related; they are not yet classified

Safe next action:
- perform a read-only classification of all dirty tracked and untracked files on `main`
- split them into:
  - live product change
  - planning artifact
  - persona/runtime file drift
  - scratch/junk
  - rewrite-only candidate
- then define what belongs in live stabilization versus what must be quarantined

Blocked by:
- nothing for read-only classification
- any actual cleanup/editing is blocked until Fritz approves lane-specific execution

Agents/workers allowed now:
- read-only repo auditor
- dirty-tree classifier
- model-switchboard behavior mapper
- runtime-truth verifier
- issue triage summarizer

Agents/workers not allowed yet:
- file editors
- cleanup agents
- merge agents
- service restart agents
- branch rewrite agents

Files/areas in scope:
- `main` branch working tree as read-only
- tracked dirty product files:
  - `shay_cli/commands.py`
  - `shay_cli/models.py`
  - `shay_constants.py`
  - `tools/registry.py`
- planning docs under `docs/` as read-only evidence
- git status / diff surfaces
- runtime behavior docs relevant to `/model`

Files/areas out of scope:
- `MEMORY.md`
- `USER.md`
- `SOUL.md`
- `PERSONA.md`
- `shay-platform-build` edits
- live services/process control

Risks:
- accidental stabilization work on top of unclassified dirty files
- product bugfixes getting entangled with planning artifacts
- persona/runtime files muddying product-lane decisions
- “fixing” rewrite issues on main

Done criteria:
- every dirty file on `main` is classified
- `/model` switchboard remaining issues are listed and bounded
- a protection rule exists for what may and may not change on live main
- live-main execution packet is specific enough to delegate safely

Exact first prompt to run:
“Read the current `main` working tree only. Do not edit anything. Classify every dirty tracked and untracked file into: live product change, planning artifact, persona/runtime drift, scratch/junk, or rewrite-only candidate. Then assess the remaining `/model` switchboard stabilization surface and return a live-main protection packet with risks, ownership, and the minimum safe next execution step.”

---

## Lane 2 — Hermes removal sandbox lane

Purpose:
- remove Hermes branding/code/runtime dependencies safely
- create backup-of-now sandbox before destructive work
- audit all Hermes references and compatibility surfaces
- validate Shay still works without Hermes dependency pressure

Current status:
- planning exists
- live Hermes footprint is known at a high level
- no destructive removal has started
- external compatibility gate is not yet fully defined

Safe next action:
- produce a read-only touchpoint/dependency inventory for Hermes references and external compatibility surfaces
- define the exact shape of the backup-of-now sandbox
- define cutover gates, not deletion commands

Blocked by:
- blocked from execution until backup-of-now design and compatibility gate are approved
- blocked from deletion until external-client/contract validation plan exists

Agents/workers allowed now:
- Hermes touchpoint mapper
- compatibility-shim classifier
- sandbox-shape planner
- external-consumer inventory planner
- deletion-gate drafter

Agents/workers not allowed yet:
- deletion/removal agents
- launchd/service modifiers
- env/path changers
- shell cleanup agents
- branch-wide refactor agents

Files/areas in scope:
- live Hermes/Shay identity and runtime audit docs
- Hermes compatibility references in repo, tests, env naming, wrappers, launch references
- disk/runtime footprints as read-only evidence:
  - `~/.hermes`
  - `~/.shay/hermes-agent`
  - `~/.local/bin/hermes`
- branch/lane mapping docs

Files/areas out of scope:
- destructive changes to live machine
- service restarts
- deleting Hermes paths
- rewrite branch implementation
- memory/persona files

Risks:
- hidden compatibility surfaces break after removal
- auth/session/token regressions in external clients
- deleting lineage artifacts before proving Shay-only behavior in sandbox
- mistaking dormant install residue for safe-to-delete runtime dependency

Done criteria:
- backup-of-now sandbox design is explicit
- Hermes references are classified:
  - hard dependency
  - compatibility shim
  - historical leftover
  - remove-early
  - remove-last
- external compatibility gate is defined
- validation checklist exists for sandbox and for live cutover
- rollback handles are specified

Exact first prompt to run:
“Read the Shay/Hermes runtime identity audit, Hermes decommission plan, and current repo references to Hermes. Do not edit anything and do not delete anything. Build a Hermes removal control packet that defines: backup-of-now sandbox shape, compatibility-surface inventory, external-client validation gate, deletion-order prerequisites, and rollback handles.”

---

## Lane 3 — Capability awareness lane

Purpose:
- create honest capability awareness for Shay
- audit skills, tools, MCPs, providers, messaging, agent CLIs, and model routes
- maintain adoption backlog
- define model-routing policy
- define ‘before saying I can’t’ logic

Current status:
- partial audit already exists
- routing policy/adoption backlog already exists
- runtime truth is still not fully enforced
- capability claims still exceed live host reality in some areas

Safe next action:
- consolidate the capability status model into a control map:
  - healthy
  - warning
  - capped
  - broken
  - missing
  - unknown
- define the no-side-effect smoke-test rule as the required gate before claiming capability
- define fallback order per task family

Blocked by:
- not blocked for read-only planning
- implementation blocked until Fritz approves runtime policy changes or connector adoption work

Agents/workers allowed now:
- provider inventory agent
- MCP inventory agent
- skills-vs-host-readiness checker
- model-routing policy drafter
- fallback-logic designer
- adoption backlog classifier

Agents/workers not allowed yet:
- installer agents
- connector setup agents
- auth mutation agents
- config writers
- provider-switching execution agents

Files/areas in scope:
- runtime surface audit
- routing policy / adoption backlog
- runtime truth-table artifacts as read-only
- `shay status` / provider / MCP / skill inventory evidence
- model routing logic as planning target

Files/areas out of scope:
- live provider config edits
- installing missing dependencies
- enabling dormant connectors
- changing default provider/model behavior
- service restarts

Risks:
- Shay claims ability that is not proven live
- expensive models get used for grunt work
- capped/broken lanes get promised as if healthy
- skill presence gets mistaken for capability readiness

Done criteria:
- capability classes are defined and accepted
- “before saying I can’t” rule is explicit:
  - check auth
  - check dependency
  - run no-side-effect smoke test
  - route to approved fallback
  - only then declare unavailable
- routing policy by task family is explicit
- adoption backlog is split into:
  - adopt now
  - review
  - hold
  - skip

Exact first prompt to run:
“Read the runtime surface audit, routing policy, adoption backlog, and runtime truth-table artifacts. Do not edit anything. Build a capability-awareness control packet that defines capability statuses, smoke-test gates, fallback routing, model-cost policy, and a ‘before saying I can’t’ decision flow.”

---

## Lane 4 — Rewrite sandbox lane

Purpose:
- preserve `shay-platform-build` as draft rewrite sandbox
- quarantine conflicting memory runtime assumptions
- identify salvage candidates
- prevent forced merge pressure
- allow comparison against live-main reality without redefining truth

Current status:
- branch exists and is preserved
- memory-architecture-related work appears documented there historically, but memory architecture is already merged into `main`
- lane must now be treated as sandbox, not authority

Safe next action:
- perform a read-only divergence map between `main` and `shay-platform-build`
- classify rewrite contents into:
  - already merged/live
  - salvage candidate
  - conflicting runtime assumption
  - obsolete duplicate
  - still useful research artifact

Blocked by:
- blocked from merge/promotion decisions until promotion rules are defined
- blocked from active rewrite implementation until live-main and Hermes-removal control maps are stabilized

Agents/workers allowed now:
- branch divergence mapper
- salvage-candidate classifier
- memory-runtime conflict auditor
- parity-gap summarizer
- rewrite-risk reviewer

Agents/workers not allowed yet:
- merge agents
- cherry-pick agents
- forced reconciliation agents
- rewrite implementation agents
- service wiring agents

Files/areas in scope:
- `shay-platform-build` as read-only
- branch diff against `main`
- docs and runtime assumptions inside rewrite lane
- memory/runtime surfaces only for conflict analysis

Files/areas out of scope:
- edits to `shay-platform-build`
- forced parity work
- live main behavior changes
- cutover planning as if rewrite is imminent

Risks:
- treating rewrite as more current than live main
- duplicate work on features already merged
- reintroducing memory/runtime contradictions already solved in main
- forcing merge pressure before live functionality and promotion gates are clear

Done criteria:
- divergence map exists
- salvage candidates are identified
- conflicting runtime assumptions are quarantined
- rewrite lane has explicit “no forced merge” status
- parity unknowns are listed for future transfer rules

Exact first prompt to run:
“Read `main` and `shay-platform-build` as separate lanes only. Do not edit either branch. Produce a rewrite sandbox divergence map showing what is already live in main, what is salvageable, what conflicts with current runtime truth, and what should remain quarantined until later.”

---

## Lane 5 — Promotion rules lane

Purpose:
- define how live Shay functionality transfers into rewrite later
- preserve clean-room logic transfer
- create validation gates before any future promotion
- stop ad hoc porting

Current status:
- concept exists in prior planning
- not yet formalized into a transfer contract
- no final parity or promotion gate is currently authoritative

Safe next action:
- define a transfer contract:
  - live lesson identified
  - rewrite relevance decided
  - logic transferred clean-room
  - parity tested
  - benchmark/behavior checked
  - promotion logged

Blocked by:
- blocked by incomplete divergence map from rewrite lane
- blocked by incomplete stabilization picture from live-main lane
- blocked by undefined final ledger schema from swarm/ledger lane

Agents/workers allowed now:
- promotion-policy drafter
- parity-gate designer
- clean-room transfer-method analyst
- drift-tracking schema designer
- validation checklist author

Agents/workers not allowed yet:
- branch merge agents
- code port agents
- automatic parity-claim agents
- rewrite adoption agents

Files/areas in scope:
- lane-mapping docs
- main vs rewrite planning docs
- validation-rule planning artifacts
- parity/drift concepts

Files/areas out of scope:
- actual code transfer
- merge/cherry-pick work
- branch mutation
- live runtime changes

Risks:
- untracked drift between main and rewrite
- copying implementation details blindly instead of transferring validated logic
- “looks similar” being mistaken for proven parity
- rewrite inheriting stale assumptions instead of live truth

Done criteria:
- promotion decision table exists
- clean-room transfer rule is explicit
- parity/benchmark gates are explicit
- drift-tracking requirements are explicit
- future promotion can be delegated without branch confusion

Exact first prompt to run:
“Using the live-main lane assumptions and rewrite sandbox assumptions as separate truths, define a promotion-rules packet for future transfer only. Do not edit code. Specify how a live-main lesson becomes a rewrite change, what validation must pass, what counts as parity, and what evidence must be logged before any future promotion.”

---

## Lane 6 — Swarm / ledger lane

Purpose:
- define worker types
- define context injection rules
- define assignment ledger
- define artifact ledger
- define validation ledger
- define model-cost routing
- make cheap/free lanes the default labor force
- reserve premium lanes for reviewer/breaker roles only

Current status:
- doctrine exists in planning docs
- adversarial review already exposed at least one telemetry-policy gap:
  raw/exact context capture without mandatory redaction controls is unsafe
- ledger model is not yet execution-safe

Safe next action:
- define ledger schema and policy only
- explicitly add secret-handling, retention, ACL, and redaction rules
- define worker-role taxonomy and routing policy by task class

Blocked by:
- blocked from execution swarm launch until ledger/redaction policy is explicit
- blocked from high-scale automation until assignment/artifact/validation ledgers are defined

Agents/workers allowed now:
- worker-taxonomy designer
- context-injection policy drafter
- ledger-schema planner
- model-cost router
- telemetry risk reviewer
- secret-handling policy designer

Agents/workers not allowed yet:
- implementation swarms
- high-scale autonomous execution lanes
- telemetry persistence writers
- production orchestration agents that assume ledger safety already exists

Files/areas in scope:
- hyperparallel swarm plan
- ledger/dispatch plan
- review findings about telemetry and cutover gates
- routing/cost policy docs
- worker-role and prompt-shape planning

Files/areas out of scope:
- actual swarm runs
- durable telemetry writes in production
- secret-bearing prompt logs
- implementation agents touching live repos

Risks:
- storing raw secrets or tenant-sensitive context in ledgers
- no durable traceability for assignments/artifacts/validation
- premium models being wasted on grunt work
- role confusion between worker, reviewer, and captain

Done criteria:
- worker taxonomy exists
- context injection rules exist
- assignment ledger schema exists
- artifact ledger schema exists
- validation ledger schema exists
- redaction/ACL/retention policy exists
- cost-routing rule is explicit:
  cheap/free workers by default, premium reviewer lanes only

Exact first prompt to run:
“Read the hyperparallel swarm and ledger planning docs plus the latest adversarial review findings. Do not start any workers and do not edit implementation files. Produce a swarm-control packet defining worker types, context-injection policy, assignment/artifact/validation ledgers, redaction/retention/access rules, and model-cost routing with cheap/default worker lanes and premium reviewer lanes only.”

---

## What can run in parallel now

These can run now as read-only planning tracks in parallel:
1. live-main dirty-tree classification lane
2. Hermes touchpoint + sandbox-shape planning lane
3. capability-awareness control lane
4. rewrite divergence-map lane
5. swarm/ledger policy lane

Reason:
- all five can operate read-only
- none require edits, merges, restarts, or service mutation
- each has a distinct evidence surface

## What must be serial

These must be serial or at least phase-gated:
1. promotion rules lane after:
   - live-main stabilization map exists
   - rewrite divergence map exists
2. any Hermes removal execution after:
   - sandbox plan exists
   - compatibility gate exists
   - Fritz approves
3. any live-main cleanup/editing after:
   - dirty-tree classification is complete
4. any rewrite adoption/merge work after:
   - promotion rules are approved
   - live-main product truth is stabilized
5. any swarm execution after:
   - ledger/redaction policy is approved

## What should be read-only only right now

Read-only only:
- `main` dirty-tree classification
- `shay-platform-build` divergence mapping
- Hermes touchpoint/dependency mapping
- capability awareness / truth-table planning
- promotion-rules drafting
- swarm/ledger schema drafting

## What requires Fritz approval

Requires explicit Fritz approval before execution:
- writing/cleaning files on `main`
- creating backup-of-now sandbox
- editing `shay-platform-build`
- deleting any Hermes artifact
- changing provider/model routing defaults
- installing missing dependencies/connectors
- starting implementation agents
- merging or cherry-picking between lanes
- introducing durable ledger persistence
- restarting any service

## What should be committed

When execution is later approved, these should become committed artifacts:
- finalized lane map / control map
- finalized Hermes decommission playbook
- finalized capability truth policy
- finalized promotion rules
- finalized swarm/ledger schema docs
- any approved product fixes on `main`
- any approved rewrite-sandbox docs inside rewrite lane

## What should stay uncommitted

Should stay uncommitted until explicitly approved:
- scratch comparison notes
- temporary review outputs
- raw prompt dumps
- raw context-injection examples containing sensitive material
- branch-local exploratory notes not yet promoted to canonical docs
- any accidental persona/runtime file drift unrelated to the approved workstream

## Recommended order

1. Live-main stabilization lane
2. Capability awareness lane
3. Hermes removal sandbox lane
4. Rewrite sandbox lane
5. Promotion rules lane
6. Swarm/ledger lane finalization

Reason:
- protect live truth first
- make capability claims honest second
- define safe Hermes removal third
- map rewrite divergence fourth
- then define transfer rules
- then finalize swarm/ledger execution architecture on top of cleaned lane boundaries

## What can run right now

Run now as planning-only, read-only:
- Lane 1 first prompt
- Lane 2 first prompt
- Lane 3 first prompt
- Lane 4 first prompt
- Lane 6 first prompt

## What must wait

Must wait:
- any file edits
- any sandbox creation
- any Hermes deletion
- any branch merge or cherry-pick
- any service restart
- any implementation swarm
- lane 5 execution beyond drafting until lane 1 + lane 4 outputs exist

## Highest-risk lane

Highest-risk lane:
- Hermes removal sandbox lane

Why:
- destructive potential
- hidden compatibility surfaces
- auth/session/token regression risk
- easy to confuse dormant lineage with safe-to-delete runtime dependency

Close second:
- swarm/ledger lane, because unsafe telemetry policy can create long-lived secret leakage

## First implementation prompt

When Fritz approves actual execution later, the first implementation prompt should be:

“Work only on the live-main stabilization lane. Start with the current `main` branch. Classify every dirty file, isolate which tracked changes are real product work versus planning/persona/scratch drift, and produce the minimum safe execution plan to finish `/model` switchboard stabilization without touching Hermes removal, rewrite sandbox, MEMORY.md, USER.md, SOUL.md, or PERSONA.md. Do not merge, do not restart services, and do not touch `shay-platform-build`."