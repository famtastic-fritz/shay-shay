# Shay process intelligence architecture — 2026-06-13

Status: design for docs/control branch
Scope: HyperSwarm mission process intelligence lane
Authority: `docs/shay-full-autonomy-completion-mission-2026-06-13.md`
Lineage defaults:
- plan_id: `plan-full-autonomy-completion-2026-06-13`
- run_id: `run-2026-06-13-full-autonomy-mission-01`
- primary job_id: `job-process-intelligence-architecture-2026-06-13-01`
- primary task_id: `task-process-intelligence-doc-pack-2026-06-13-01`

## Purpose

Give Shay a durable, explainable record of what happened during each meaningful run so HyperSwarm can answer:
- what was attempted
- why it was allowed
- what changed
- what decisions were made
- what evidence exists
- what failed or was deferred
- what should improve next

## Architecture summary

The architecture is redaction-first, ledger-based, and lineage-bound.

Flow:
1. capture run packet at task start
2. append event and tool activity during execution
3. record decisions as they happen, not only at the end
4. record artifacts created or modified
5. normalize outputs into four ledgers
6. validate required lineage and safety metadata
7. run after-action review
8. update gaps, backlog, and improvement recommendation
9. route follow-up through autonomy policy

## Core design principles

1. Redaction before storage
   - no raw secrets
   - no full env dumps
   - no private transcript dumps by default
   - store hashes, summaries, paths, secret-type labels, and protected pointers only

2. Explainability over exhaustiveness
   - enough metadata to reconstruct intent, actions, outcomes, and evidence
   - avoid high-noise low-value telemetry

3. Stable lineage
   - every record must connect plan -> job -> task -> run -> event
   - parent-child relationships are explicit for swarm lanes and subagents

4. Separation of ledgers by concern
   - run ledger for execution envelope
   - decision ledger for approvals, assumptions, and tradeoffs
   - tool-agent ledger for tool calls, worker roles, and failures
   - artifact ledger for files, docs, commits, reports, and evidence objects

5. Safety-state awareness
   - allowed actions, forbidden actions, autonomy zone, and safety events are always captured
   - stop conditions and disaster signals remain first-class metadata

6. Learning loop by default
   - every meaningful run ends with one bounded improvement recommendation
   - each recommendation must map to green, yellow, or red-zone execution handling

## Ledger set

### 1. Run ledger

Tracks one meaningful run or sub-run.

Must answer:
- what mission or job this run belonged to
- who/what executed it
- when it started and ended
- what instructions governed it
- what tools, commands, files, validations, blockers, and outcomes occurred
- what redactions were applied

### 2. Decision ledger

Tracks decisions, assumptions, approvals, reversals, and escalations.

Must answer:
- what decision was made
- what evidence supported it
- what alternatives were rejected
- whether approval was required
- whether the decision changed later

### 3. Tool-agent ledger

Tracks tool calls, subagent roles, execution steps, and runtime failures.

Must answer:
- which worker or role acted
- which tool or command was used
- whether it succeeded
- what files or resources it touched
- whether safety or reliability issues appeared

### 4. Artifact ledger

Tracks created or changed evidence objects.

Must answer:
- what artifact exists
- where it lives
- whether it was created, updated, or inspected
- what run and decision it supports
- whether redaction or review is required

## Canonical lineage model

Required lineage fields:
- plan_id
- job_id
- task_id
- run_id
- event_id

Optional but recommended lineage fields:
- parent_job_id
- parent_task_id
- parent_run_id
- swarm_id
- lane_id
- worker_id
- session_id
- related_decision_id
- related_artifact_id
- related_gap_id
- related_validation_id

Naming guidance:
- plan ids remain stable for the mission
- job ids describe a lane-level objective
- task ids describe a bounded deliverable
- run ids describe one execution attempt
- event ids are append-only timestamps or ordered counters

Example lineage:
- plan_id: `plan-full-autonomy-completion-2026-06-13`
- job_id: `job-process-intelligence-architecture-2026-06-13-01`
- task_id: `task-process-intelligence-doc-pack-2026-06-13-01`
- run_id: `run-2026-06-13-full-autonomy-mission-01`
- event_id: `evt-run-2026-06-13-full-autonomy-mission-01-004`

## Capture stages

### Stage 0 — Intake
Capture:
- mission authority path
- instruction summary
- instruction hash
- lane name
- autonomy zone expectations
- allowed actions
- forbidden actions
- operator/agent identity

### Stage 1 — Execution
Capture:
- tools used
- commands run
- files inspected
- files changed
- decisions made
- blockers encountered
- validations executed
- safety events
- redactions applied

### Stage 2 — Normalization
Convert raw execution notes into ledger records with consistent IDs, timestamps, statuses, and evidence pointers.

### Stage 3 — Review
Perform after-action review with:
- outcome classification
- gap classification
- lessons learned
- single best next improvement

### Stage 4 — Routing
Route the improvement:
- green-zone -> implement in bounded fashion
- yellow-zone -> create approval packet
- red-zone -> stop and request human approval

## Required metadata envelope

Every meaningful run record must include:
- mission authority path
- instruction summary and hash
- autonomy zone at start and end
- allowed actions
- forbidden actions
- tools used
- commands run summary
- files inspected and changed
- validations run
- safety events
- blockers
- outcome
- next actions
- lessons learned
- redactions

## Safety and redaction controls

Redaction-first controls:
- classify sensitive material before persistence
- replace direct values with `[REDACTED:<type>]`
- store file path and evidence hash instead of payload where possible
- keep secret-exposure findings abstract unless explicit red-zone approval exists

Abstract audit finding to preserve:
- an audit discovered secret-exposure risk in a workflow surface
- no secret values were stored in this architecture pack
- follow-up action is to tighten telemetry filtering and approval gates before broader automation

## Data model relationships

- one run ledger record can reference many decision records
- one run can emit many tool-agent records
- one run can create many artifact records
- decisions can reference artifacts and validations
- artifacts can support multiple decisions if evidence is reused

## Validation rules

A record is invalid if:
- any required lineage field is missing
- outcome exists without status
- a changed artifact lacks path or summary
- a safety event lacks severity and disposition
- redaction_applied is true but redaction notes are empty
- forbidden actions list is omitted

## Query goals

The architecture should support fast answers to questions like:
- show every file changed by run_id
- show all yellow-zone decisions awaiting approval
- show repeated blockers across runs
- show artifacts created without validation
- show runs that encountered safety events
- show lessons learned tied to a mission plan

## Storage posture

This docs/control design does not require live automation yet.
Recommended eventual storage layers:
- append-only structured ledgers for runs, decisions, tool-agent activity, and artifacts
- derived summaries for daily/weekly pattern scans
- protected evidence storage for sensitive supporting material

## Non-goals for this lane

This document does not:
- enable watchers automatically
- change live services
- capture raw secrets
- mutate live `.shay`
- define code implementation details beyond the schema and policy shape

## Done criteria for this design

The process intelligence lane is considered complete for docs/control when:
- all required ledgers have schemas
- redaction and after-action policies exist
- a pilot run demonstrates the shape
- query examples prove explainability
- a learning loop defines how improvements are produced and routed
- a lane packet gives future workers a bounded execution contract
