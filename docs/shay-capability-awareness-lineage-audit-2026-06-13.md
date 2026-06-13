# Shay capability-awareness lineage audit — 2026-06-13

Status: captain audit
Purpose: trace where the missing awareness docs most likely went, determine whether they were truly lost versus intentionally deferred/superseded, and answer whether Shay currently has real global capability awareness.

## Executive verdict

The missing awareness docs do not look like a simple random loss.
They look like a combination of:
1. intentionally deferred sandbox awareness artifacts,
2. renamed or broadened predecessor docs,
3. later Life OS synthesis docs that absorbed the interview-driven architecture direction,
4. tracker/final-report references that overstate what was actually copied into the main-sync branch.

Blunt answer:
- Shay does NOT yet have a clean, machine-backed, canon-complete global capability-awareness system.
- Shay DOES have meaningful precursor material, including a draft global capability matrix, adoption backlog, worker-role matrix, skills gap log, and gap-lifecycle policy in the sandbox lane.
- The Life OS interview and implementation plan are the later, broader synthesis layer built on top of that precursor material.

## Key proof

### 1. The interview clearly drives the Life OS plan

The Shay Life OS interview capture explicitly asks Shay to turn the interview into a better Life OS architecture and phased implementation plan.

Source:
- `docs/shay-life-os-interview-2026-06-13.md`

Direct evidence:
- interview lines 106-129 define the task list for turning the interview into architecture + implementation recommendations
- interview lines 133-142 name the immediate architectural implications
- the Life OS implementation plan later restates those same concepts in Phase 5

Examples of direct carry-through:
- interview: `global life-domain registry`
- plan: `global life-domain registry`
- interview: `portfolio/business registry`
- plan: `portfolio/business registry`
- interview: `Fritz model`
- plan: `Fritz model inputs`
- interview: `attention router`
- plan: `attention-router inputs`
- interview: `HyperSwarm is one orchestration method, not the whole swarm architecture`
- plan repeats the same correction almost verbatim

Conclusion:
The Life OS plan was not generated in a vacuum. It is a later synthesis built directly from the interview artifact.

### 2. The missing awareness layer exists mostly in the sandbox lane, not in the promoted main-sync branch

Sandbox-only awareness/control docs with matching date and cluster:
- `docs/shay-global-capability-matrix-draft-2026-06-13.md`
- `docs/shay-global-capability-matrix-draft-2026-06-13.yaml`
- `docs/shay-adoption-backlog-2026-06-13.md`
- `docs/shay-worker-role-matrix-2026-06-13.md`
- `docs/shay-skills-gap-log-2026-06-13.md`
- `docs/shay-gap-lifecycle-policy-2026-06-13.md`
- `docs/shay-gap-resolution-workflow-2026-06-13.md`
- `docs/shay-capability-research-cron-design-2026-06-13.md`
- `docs/shay-add-audit-prune-rule-2026-06-13.md`

These files are timestamp-clustered in the sandbox lane and read like the real precursor awareness pack.

Main-sync branch contains later synthesis docs instead:
- `docs/shay-life-os-interview-2026-06-13.md`
- `docs/shay-life-os-completion-implementation-plan-2026-06-13.md`
- `docs/shay-full-autonomy-completion-mission-2026-06-13.md`
- `docs/shay-hyperswarm-final-mission-report-2026-06-13.md`
- `docs/shay-master-open-items-and-completion-tracker-2026-06-13.md`

Conclusion:
The branch with the Life OS plan contains the later architecture/synthesis layer, while the sandbox lane contains the rawer capability-awareness prototypes.

### 3. The repo itself says many awareness docs were intentionally deferred

`docs/shay-docs-promotion-manifest-2026-06-13.md` says these were "Defer later":
- `docs/shay-adoption-backlog-2026-06-13.md`
- `docs/shay-awareness-completion-assessment-2026-06-13.md`
- `docs/shay-gap-lifecycle-status-2026-06-13.md`
- `docs/shay-hermes-lane-packet-2026-06-13.md`
- `docs/shay-pattern-scanner-autonomy-policy-2026-06-13.md`
- `docs/shay-process-intelligence-watcher-design-2026-06-13.md`
- `docs/shay-process-learning-loop-2026-06-13.md`
- `docs/shay-process-query-examples-2026-06-13.md`

It also classifies `docs/shay-awareness-lane-packet-2026-06-13.md` as scratch/duplicate/lane residue.

Conclusion:
At least part of what looks "missing" was intentionally excluded from the first clean promoted surface.

### 4. The clean transplant manifest says the awareness pack should stay deferred to a later awareness PR

`docs/hermes-removal-clean-pr-transplant-manifest-2026-06-13.md` explicitly defers:
- `docs/shay-global-capability-matrix-draft-2026-06-13.*`
- `docs/shay-adoption-backlog*`
- `docs/shay-skills-gap-log-2026-06-13.md`
- `docs/shay-skills-readiness-matrix-2026-06-13.yaml`
- `docs/shay-worker-role-matrix-2026-06-13.md`
- `docs/shay-gap-log-schema-2026-06-13.yaml`
- `docs/shay-gap-resolution-workflow-2026-06-13.md`
- `docs/shay-gap-lifecycle-policy-2026-06-13.md`
- `docs/shay-capability-research-cron-design-2026-06-13.md`
- `docs/shay-add-audit-prune-rule-2026-06-13.md`

Conclusion:
The sandbox awareness cluster was not supposed to be fully promoted in the first clean PR shape.

## Best-fit mapping: likely predecessors / substitutes for the "missing" docs

### `shay-awareness-completion-assessment-2026-06-13.md`
No exact file found.
Most likely conceptual predecessors/substitutes:
- `docs/shay-global-capability-matrix-draft-2026-06-13.md`
- `docs/shay-skills-gap-log-2026-06-13.md`
- `docs/shay-worker-role-matrix-2026-06-13.md`
- `docs/hermes-removal-brutal-qa-report-2026-06-13.md`

Interpretation:
This looks more like an intended synthesis artifact than a currently surviving file. The real content seems distributed across the draft matrix, gap log, role matrix, and brutal QA review.

### `shay-adoption-backlog-2026-06-13.md`
Exact file found in sandbox:
- `docs/shay-adoption-backlog-2026-06-13.md`

Interpretation:
This one is real and recoverable. It was likely deferred intentionally, not lost conceptually.

### `shay-gap-lifecycle-status-2026-06-13.md`
No exact file found.
Closest surviving equivalents:
- `docs/shay-gap-lifecycle-policy-2026-06-13.md`
- `docs/shay-gap-resolution-workflow-2026-06-13.md`
- `docs/hermes-removal-gap-log-2026-06-13.md`

Interpretation:
The named `status` doc may have been planned as a summary artifact, but the surviving reality is policy + workflow + actual gap log rather than a single status snapshot.

### `shay-awareness-lane-packet-2026-06-13.md`
No exact file found.
Closest surviving equivalents:
- the entire sandbox awareness cluster listed above
- later synthesis in `docs/shay-life-os-completion-implementation-plan-2026-06-13.md`

Interpretation:
This looks like lane residue that may never have been preserved as a standalone file, even though later docs refer to it.

### `shay-process-query-examples-2026-06-13.md`
No exact file found.
Interpretation:
This appears to be a referenced-but-missing artifact. The intent survives conceptually in the process-intelligence architecture and the tracker's query-answering expectations, but the named file itself is absent.

### `shay-process-intelligence-watcher-design-2026-06-13.md`
No exact file found.
Closest surviving substitute:
- the watcher phase/spec sections inside `docs/shay-life-os-completion-implementation-plan-2026-06-13.md`
- the scheduler audit in `docs/shay-current-intelligence-schedule-audit-2026-06-13.md`

### `shay-pattern-scanner-autonomy-policy-2026-06-13.md`
No exact file found.
Closest surviving substitute:
- `docs/shay-pattern-scanner-design-2026-06-13.md`

## Timeline read

The timestamps suggest this sequence:
1. Early sandbox capability-awareness prototypes were created first.
2. Those prototypes included the matrix/backlog/gap/role cluster.
3. Later in the day, the Life OS interview happened.
4. After the interview, the mission/plan/tracker/report synthesis layer was created in main-sync.
5. During that later synthesis, some deferred/missing awareness artifacts were still referenced as if they existed cleanly in the promoted branch.

This means the Life OS plan is probably the newer strategic synthesis, while the missing awareness files belong to an earlier but still important prototype layer.

## Answer to Fritz's return question

If Fritz asks:
"Are you aware of your capabilities globally?"

Best honest answer right now:

Partially.
I have meaningful scaffolding and precursor artifacts for global capability awareness, including a draft capability matrix and related gap/backlog/role docs in the sandbox lane, and I have a later Life OS architecture plan that broadens that into a real system. But I do not yet have a clean, fully preserved, machine-backed, canon-complete global capability-awareness layer that I can claim as finished truth.

## Recommended next move

1. Treat the sandbox awareness cluster as source material, not noise.
2. Build one clean promoted awareness canon later from:
   - global capability matrix
   - adoption backlog
   - gap lifecycle policy/workflow
   - worker-role matrix
   - skills readiness/gap truth
3. Remove or downgrade references to artifacts that never actually landed.
4. Keep the Life OS interview + implementation plan as the higher-order synthesis layer built from that source material.

## Pride test

The real move is not to pretend the missing docs are random casualties.
The real move is to recognize that the capability-awareness prototype lane existed, then got partially deferred while a later interview-driven Life OS synthesis doc set became the new top layer. The branch is carrying both stories at once, and the inconsistency comes from mixing deferred prototype artifacts with promoted synthesis truth.
