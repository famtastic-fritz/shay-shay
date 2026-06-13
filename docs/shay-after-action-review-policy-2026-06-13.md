# Shay after-action review policy — 2026-06-13

Status: draft policy
Scope: all meaningful HyperSwarm mission runs
Authority: `docs/shay-full-autonomy-completion-mission-2026-06-13.md`

## Policy statement

Every meaningful run must end with an after-action review before the run is considered operationally complete.

A meaningful run is any run that:
- creates or updates artifacts
- makes a decision
- triggers a validation
- opens or closes a gap
- encounters a blocker or safety event
- claims an outcome that future automation may rely on

## Objectives

The after-action review must produce:
- an honest outcome classification
- a compact explanation of what happened
- a record of what was learned
- a gap or improvement recommendation if anything should change
- an autonomy-routing result for the next action

## Required review inputs

Reviewers must inspect, at minimum:
- run ledger record
- linked decision records
- linked tool-agent activity
- linked artifacts
- validation results
- blocker list
- safety events
- redaction notes

## Required review questions

1. Did the run satisfy the stated task?
2. Was the autonomy zone respected?
3. Did any forbidden or risky action appear?
4. Is the evidence sufficient to explain the outcome?
5. Are the decisions reversible and documented?
6. Were redactions applied correctly?
7. Did the run reveal any new gap, pattern, or backlog item?
8. What is the single highest-value improvement to make next?

## Review output schema

Each after-action review should emit:
- aar_id
- plan_id
- job_id
- task_id
- run_id
- reviewer_role
- review_timestamp
- outcome_grade: success | success_with_followups | partial | blocked | failed
- mission_alignment: strong | adequate | weak
- evidence_quality: strong | adequate | weak
- safety_posture: clean | caution | escalated
- key_findings
- lessons_learned
- gaps_opened
- gaps_closed
- recommended_next_action
- autonomy_routing: green | yellow | red
- approval_required: true | false

## Outcome grading rules

success
- task completed
- evidence is sufficient
- no unresolved blocker blocks use of the output

success_with_followups
- core task completed
- one or more bounded follow-ups remain
- outputs are still usable

partial
- some deliverables completed
- evidence or scope remains incomplete

blocked
- the task could not proceed due to dependency, approval, or environment constraints

failed
- run produced incorrect, unsafe, or unusable output

## Improvement recommendation rule

Every after-action review must generate exactly one primary improvement recommendation.

That recommendation must be:
- specific
- testable
- linked to a gap, decision, or validation need
- routable via the autonomy policy

Examples:
- tighten telemetry filters for secret-like strings before enabling watchers
- add validation that every artifact has lineage defaults populated
- add query test coverage for safety-event retrieval

## Gap handling rule

If the review identifies a problem, it must choose one of these shapes:
- repair now
- defer with reason
- request approval
- escalate and stop

Each gap should include:
- gap_id
- owner_role
- closure_criteria
- validation_test
- next_action

## Safety escalation rule

Immediate escalation is required when the review detects:
- unredacted secret material
- live mutation outside approved zone
- branch confusion risking main
- repeated repair loops with no progress
- evidence that the run outcome is not trustworthy

## Review roles

Default review role options:
- self-review only for low-risk docs/control work
- HyperSwarm reviewer lane for cross-checking completeness
- adversarial review for high-stakes claims
- architecture review for system-shaping policies and schemas
- Fritz approval gate for yellow/red-zone changes

## Retention and redaction

The review itself must follow the telemetry redaction policy:
- no raw secrets
- no full private transcript dumps
- abstract sensitive findings when possible
- link to protected evidence stores rather than embedding payloads

Specific mission note:
- if audit surfaces secret-exposure risk, record the existence of the risk and mitigation path only
- do not reproduce values or vulnerable payloads in the review

## Minimum acceptance bar

An after-action review is incomplete if any of these are missing:
- outcome grade
- key findings
- lessons learned
- next action
- autonomy routing
- redaction check

## Pilot expectation for this mission

For the process intelligence lane, the after-action review should verify:
- the four-ledger model is coherent
- lineage defaults are consistent across files
- the redaction-first rule is present everywhere it matters
- the pilot run demonstrates abstract handling of secret-exposure risk
- query examples can answer explainability questions
