# Shay pattern scanner design — 2026-06-13

Status: design-only
Authority: `docs/shay-full-autonomy-completion-mission-2026-06-13.md`
Lineage:
- plan_id: `plan-full-autonomy-completion-2026-06-13`
- job_id: `job-pattern-scanner-design-2026-06-13-01`
- task_id: `task-pattern-scanner-design-2026-06-13-01`
- run_id: `run-2026-06-13-full-autonomy-mission-01`
- event_id: `event-pattern-scanner-design-2026-06-13-01`

## Why this exists

The policy doc exists.
The actual scanner design did not.
That was a real gap.

This document closes the design gap without pretending the scanner is live.

## Mission-fit

The scanner exists to answer questions like:
- what patterns are repeating across runs?
- what is noisy vs actually actionable?
- where is process breaking down?
- what should be automated next?
- what should be pruned next?

It is not allowed to:
- mutate live schedulers
- create asks automatically
- restart services
- enable cron jobs
- capture raw secrets
- escalate without dedupe/cooldown

## Inputs

Required input families:
1. run ledger records
2. decision ledger records
3. tool-agent ledger records
4. artifact ledger records
5. scheduler/watcher observations
6. command-surface health observations
7. gap lifecycle records
8. adoption backlog records

## Output classes

The scanner produces only append-only review artifacts:
1. pattern packets
2. anomaly packets
3. stale-gap packets
4. backlog-priority packets
5. prune candidates
6. review-needed packets

No direct action packets go to live mutation surfaces.
All outputs stay review-gated.

## Minimum viable scanner

Phase 1 scanner must detect:
1. repeated failed validations
2. repeated stale or contradictory docs
3. repeated ask/event storms
4. repeated scheduler unhealthy states
5. repeated missing-proof patterns
6. repeated overclaim patterns (`designed` being spoken about like `live_wired`)
7. repeated lane packet metadata omissions
8. repeated duplicate/superseded docs

If Phase 1 cannot do those eight things, it is too weak.

## Detection units

### 1) Validation failure pattern
- key: `validation_failure`
- source: artifact + review + command-surface + scheduler evidence
- threshold: same failure class seen 2+ times in 7 days
- output: review packet only

### 2) Overclaim pattern
- key: `state_overclaim`
- source: tracker state vs prose state mismatch
- threshold: 1 confirmed mismatch
- output: immediate downgrade packet

### 3) Ask storm pattern
- key: `ask_storm`
- source: events log / ask directory observation
- threshold: duplicate ask family over configured window
- output: review packet with suppression recommendation

### 4) Stale gap pattern
- key: `stale_gap`
- source: gap lifecycle tracker
- threshold: no state movement after defined review window
- output: backlog packet or prune packet

### 5) Metadata omission pattern
- key: `missing_lineage`
- source: lane packets / ledgers
- threshold: missing required lineage in any packet
- output: review packet and checklist hardening recommendation

### 6) Documentation sprawl pattern
- key: `doc_sprawl`
- source: artifact ledger + prune recommendations
- threshold: 3+ overlapping docs for one control truth surface
- output: prune packet

## Record shape

Each scanner output should include:
- scanner_run_id
- source_run_ids
- pattern_id
- pattern_class
- severity
- confidence
- first_seen_at
- last_seen_at
- occurrence_count
- affected_roles
- affected_artifacts
- evidence_pointers
- recommended_next_action
- approval_required
- redaction_status

## Severity model

- info: notable but no immediate operator value
- low: worth logging, not urgent
- medium: repeated inefficiency or trust erosion
- high: recurring process failure or misleading reporting
- critical: safety, secret, or runaway-autonomy risk

## Confidence model

- low: weak evidence, keep observational
- medium: probable pattern, review needed
- high: repeated and well-supported

## State boundaries

The scanner may classify evidence into:
- designed
- sandbox_proven
- pr_ready
- pr_open
- merged_to_main
- live_wired
- validated_live
- blocked
- deferred

The scanner must never infer a stronger state than the evidence supports.
If in doubt, downgrade.

## Required gates before enablement

Do not enable the scanner until all are true:
1. append-only ledgers exist
2. redaction pre-persistence filters exist
3. deterministic fingerprints exist
4. cooldown/suppression exists
5. review artifact destination exists
6. tracker is the state authority
7. human-review boundary is explicit

## Relationship to watcher design

Watchers observe local surfaces.
The scanner compares observations across time and across runs.

Watcher = sensor.
Scanner = pattern judge.
Tracker = truth table.
Reviewer = final downgrade authority.

## First implementation recommendation

Build the smallest real path first:
1. machine-write run ledger rows
2. machine-write artifact ledger rows
3. machine-write validation outcomes
4. scan only for overclaim + stale-gap + ask-storm + metadata-omission
5. emit markdown review packets
6. verify usefulness before adding more classes

## Known non-goals

Not in scope for first implementation:
- autonomous remediation
- auto-pruning files
- auto-enabling jobs
- auto-creating phone asks
- auto-modifying memory
- cross-repo mutation

## Captain verdict

This closes the missing design-doc gap.
It does not make pattern scanning live.
Correct state: `designed`.
