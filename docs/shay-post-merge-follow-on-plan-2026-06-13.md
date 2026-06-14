# Shay Post-Merge Follow-On Plan

Date: 2026-06-13
Status: proposed follow-on task
Trigger: execute after the current Title 6 capability-awareness restore/reconstruction cluster is committed and reviewed
Authority:
- `docs/shay-runtime-truth-audit-2026-06-13.md`
- `docs/shay-truth-surface-rubric-2026-06-13.md`
- `docs/shay-awareness-completion-assessment-2026-06-13.md`
- `docs/shay-master-open-items-and-completion-tracker-2026-06-13.md`

## Why this exists

The current run repaired the docs/control layer and made the branch much more honest.
What it did not do is wire future HyperSwarm work so the next run automatically leaves behind clean machine-backed swarm tracking.
Without that wiring, every future swarm risks recreating the same three problems:
- lane outputs exist but are not tied to durable run identities
- tracker truth drifts away from runtime truth
- working-tree artifacts get mistaken for committed or live truth

## Goal

Build the minimum swarm-tracking wiring so future captain-led runs produce:
- one run identity per swarm
- one lane identity per bounded workstream
- durable mapping from lane -> packet -> evidence -> status
- an operator query surface that can answer what ran, what changed, what is blocked, and what is still only design

## Guardrails

- Do not mutate live scheduler state without explicit approval.
- Do not treat branch code as live-runtime proof.
- Preserve the truth-surface split from `docs/shay-truth-surface-rubric-2026-06-13.md`.
- Prefer extending existing process-intelligence/runtime surfaces over inventing a parallel telemetry stack.
- `docs/shay-hermes-lane-packet-2026-06-13.md` is now restored from deferred stash residue; keep references honest and treat it as branch-local evidence unless a later cleanup explicitly retires it.

## Module breakdown

### Module 1 — Canon truth normalization
Purpose: make branch truth mechanically distinguishable from working-tree truth and live-runtime truth.
Outputs:
- tracked/committed awareness-control cluster
- any remaining dead references removed or replaced
- one canonical wording rule adopted wherever capability claims are made

### Module 2 — Swarm run identity
Purpose: stamp every future HyperSwarm execution with stable IDs.
Minimum fields:
- swarm_run_id
- captain_run_id
- lane_id
- lane_role
- worker_id
- packet_path
- started_at
- ended_at
- current_state
- evidence_paths
- review_state

### Module 3 — Tracker binding
Purpose: connect the captain tracker to machine-backed run evidence.
Minimum behavior:
- tracker item can link to one or more lane IDs
- lane packet can link back to tracker item IDs
- status changes can cite exact evidence paths
- blocked/deferred/validated states stop relying on prose alone

### Module 4 — Query surface
Purpose: answer operator questions without rereading whole sessions.
Minimum questions to support:
- what ran in the last swarm?
- which lanes completed?
- which lanes are blocked and why?
- what artifacts were produced by lane X?
- what is present only in working tree vs committed vs live runtime?
- which capability claims still lack evidence?

### Module 5 — Runtime wiring
Purpose: bind swarm tracking into the existing process-intelligence path.
Minimum targets:
- run start / finish capture
- lane-level artifact registration
- reviewer verdict capture
- truth-surface tag capture
- optional watcher/scanner ingestion after approval

### Module 6 — Hermes residue resolution
Purpose: close the dead-pointer gap around `docs/shay-hermes-lane-packet-2026-06-13.md`.
Current branch decision already taken:
1. restore the file as a real historical packet from the stash-backed original

Remaining future options:
2. replace references with cleaner current canon artifacts
3. explicitly retire it and patch all dependent docs in the same change

## Expected deliverables

- one swarm-tracking wiring design doc
- one schema or field-contract doc for swarm/lane tracking
- tracker-to-ledger mapping update
- one operator query contract for swarm status questions
- one Hermes-residue resolution decision

## Recommended execution order

1. Canon truth normalization
2. Hermes residue resolution
3. Swarm run identity design
4. Tracker binding
5. Query surface definition
6. Runtime wiring proposal
7. Optional scheduler/watcher enablement plan after approval

## Definition of done

This follow-on is done when a future swarm can be reviewed with evidence instead of reconstruction.
That means a captain should be able to answer, from durable artifacts:
- what lanes existed
- what each lane received
- what each lane produced
- what reviewer accepted or rejected
- what is only branch/worktree truth versus live-runtime truth

## Not done in this run

This current Title 6 run does not:
- enable live watchers
- deploy any swarm-tracking runtime mutation
- prove live fallback behavior end-to-end
- prove live watcher/scanner scheduling

That is intentional. This file is the follow-on boundary, not a claim that the wiring already exists.
