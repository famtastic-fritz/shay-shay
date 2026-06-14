# Shay Process Learning Loop

Date: 2026-06-13
Status: design only
Authority:
- `docs/shay-process-intelligence-architecture-2026-06-13.md`
- `docs/shay-after-action-review-policy-2026-06-13.md`
- `docs/shay-pattern-scanner-design-2026-06-13.md`
- Fritz source architecture packet section 21

## Purpose

Define the closed-loop path that turns one run into one bounded improvement recommendation.
The goal is learning that sharpens the system, not a pile of postmortems with no consequence.

## Loop

1. capture run metadata
2. normalize into ledgers
3. validate lineage and safety completeness
4. update gaps/backlog when new truth appears
5. scan for patterns
6. generate exactly one primary improvement recommendation
7. route the recommendation through the autonomy policy
8. either implement in green-zone or create approval packet in yellow/red-zone
9. measure later whether the recommendation helped

## Inputs

Required inputs:
- run ledger
- decision ledger
- tool-agent ledger
- artifact ledger
- validation results
- gap updates
- after-action review notes

Optional later inputs:
- watcher outputs
- cross-run pattern history
- adoption backlog trends
- prune-review findings

## Output types

The loop may emit one primary recommendation of these types:
- capture improvement
- routing improvement
- skill-readiness improvement
- prune recommendation
- backlog/adoption recommendation
- approval packet
- accepted-risk clarification

Only one should be promoted at a time unless a mission explicitly allows broader work.

## Routing rules

### Green zone
If the recommendation is reversible, metadata-only, sandbox-only, or purely documentary:
- implement it in bounded fashion
- record what changed
- record why it was safe

### Yellow zone
If it expands scope, costs money, enables automation, or changes runtime behavior:
- do not execute it
- create approval packet with bounded action, risk, value, stop rules, and fallback

### Red zone
If it touches live deletion, live service mutation, secrets, or main-branch merge boundaries:
- stop
- escalate to Fritz

## Completion conditions for one loop cycle

A loop cycle is complete only when:
- the run metadata is normalized
- missing-capture defects are explicitly noted if present
- at least one lesson is recorded
- exactly one primary recommendation is selected
- the recommendation is routed through autonomy policy
- the next check or revisit trigger is named

## Failure handling

If the loop is blocked:
1. log the blocker as a gap
2. classify whether it is research, approval, implementation, or accepted-risk
3. do not spin indefinitely
4. after two self-repair attempts on the same blocker, switch to gap-driven next-action packet

## What this loop is not

This loop is not:
- a promise that live automation already exists
- permission to mutate live systems
- a replacement for human review on yellow/red actions
- a reason to keep more raw sensitive data than needed

## Success test

The learning loop is working when a later run can show:
- what was improved
- why it was chosen
- what evidence supported it
- whether the change reduced repeat gaps, rework, or overclaim
