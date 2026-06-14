# Shay Gap Resolution Workflow

Date: 2026-06-13
Scope: global Shay planning/control workflow, seeded from Hermes-removal evidence
Latest evidence incorporated:
- `a644a0a docs: validate Hermes sandbox lock-dir isolation`
- helper/unit-level override proof closes `gateway-lock-dir-default-outside-shay-home` for the override question
- no full platform-runtime invocation proof is claimed

## Purpose

This workflow defines what happens after a gap is logged so the gap becomes managed work instead of dead residue.

## Workflow

### 1. Classify

At record time, classify the gap by:
- capability type
  - missing capability
  - unknown capability
  - environment dependency
  - research question
  - approval-gated action
  - validation gap
  - implementation gap
  - process/control gap
  - accepted-risk candidate
- lane
- severity
- risk
- whether it blocks current work or only future confidence

### 2. Assign Owner Role

Every gap gets:
- owner_role
- checker_role

Default mapping:
- research question -> research_fetcher owns, reviewer checks
- watch item -> watcher owns, checker checks
- sandbox validation -> runner owns, checker verifies preflight, gatekeeper enforces abort rules
- implementation task -> promoter or runner owns, reviewer checks
- approval-gated action -> gatekeeper frames exact question, Fritz owns the decision
- documentation/control gap -> recorder/ledgerer or promoter owns, reviewer checks

### 3. Decide Next Action

Canonical next actions:
- research
- watch
- approval
- sandbox_test
- implementation
- defer
- close
- reject
- duplicate
- accepted_risk
- none

Decision rules:
- if truth is missing -> research
- if truth changes over time -> watch
- if the next useful move has side effects -> approval
- if the claim can be safely proven in containment -> sandbox_test
- if the truth is already sufficient to make a change -> implementation
- if the issue is real but not worth acting on now -> defer or accepted_risk
- if the issue is already resolved or intentionally non-actionable -> close/reject/duplicate/none as appropriate

### 4. Research If Needed

Research stage must answer:
- what exact question are we trying to answer?
- what sources are approved?
- what evidence would count as candidate_found?
- what would force escalation to Fritz?
- does the candidate belong in adoption backlog?

Research outputs:
- no candidate
- candidate_found
- needs_approval
- ready_for_sandbox
- accepted_risk recommended
- deferred recommended

### 5. Create Candidate Fix

If research or analysis finds a plausible answer, write it as a candidate fix:
- what changes
- where it changes
- why it helps
- what proof is still missing
- whether it belongs in:
  - adoption backlog
  - sandbox validation packet
  - implementation packet

### 6. Request Approval If Needed

Approval packets must include:
- exact approval question
- why approval is needed
- exact bounded action to be unlocked
- exact stop/abort rules
- what success would prove

### 7. Run Sandbox Validation

Validation rules:
- smallest honest proof first
- no scope inflation
- helper/unit-level proof is enough if the question is helper/unit-level
- broader runtime claims stay open unless runtime evidence actually exists
- validation results must update both the gap state and the capability matrix if capability truth changed

Validation levels:
- docs/process validation
- helper/unit validation
- sandbox runtime validation
- live runtime validation

### 8. Update Capability Matrix / Gap Log / Adoption Backlog

After every meaningful movement:
- update gap status
- update severity or risk only if truth changed
- update next_action
- update capability matrix if capability truth changed
- update adoption backlog if a candidate or process pattern was found
- record related docs and commits
- record reopen trigger if the result is conditional

### 9. Close / Defer / Reject

Close when:
- the stated question is answered with evidence
- closure scope is explicit
- remaining non-claims are explicit

Defer when:
- the issue is real but lower-priority right now

Reject when:
- a proposed path was intentionally declined

Accepted risk when:
- the issue is real, bounded, and intentionally tolerated with mitigation

None when:
- and only when the gap is already closed, accepted_risk, rejected, duplicate, false positive, or historical-only

### 10. Promote Lessons To Global Matrix Later

Once a Hermes-sandbox rule proves durable, promote it later into a global Shay capability matrix or workflow policy.

Examples of promotable lessons:
- skill presence is not readiness proof
- helper/unit proof can close a helper/unit question without overclaiming runtime
- accepted_risk must still carry mitigation and reopen rules

## Current Hermes Gap Actions

| gap_id | status | severity | next_action | owner_role | checker_role | research/watch needed | Fritz approval needed | adoption backlog | closure criteria |
|---|---|---|---|---|---|---|---|---|---|
| sandbox-no-local-venv | needs_approval | medium | approval | gatekeeper | reviewer | no | yes | yes | sandbox-local runtime exists and sandbox execution no longer depends on shared live-checkout `.venv`, or the shared-coupling decision is explicitly accepted as risk |
| path-missing-python-pytest-pip | accepted_risk | low | none | recorder/ledgerer | checker | no | no | no | exact-command fallback remains sufficient and no current task is blocked by generic PATH assumptions |
| sandbox-home-not-yet-startup-validated | partially_closed | medium | sandbox_test | runner | checker | no | yes, before any new runtime validation | no | remaining runtime edge is either validated with a bounded sandbox test or explicitly accepted as out-of-scope |
| hermes-external-client-usage-unknown | needs_research | high | research | research_fetcher | reviewer | research | no | yes | external `hermes` dependency surfaces are mapped enough to decide safe removal/defer/accepted-risk status |
| provider-health-partial-only | watching | medium | watch | watcher | checker | watch | no | no | passive provider evidence is sufficient for the next provider-dependent decision or the gap is escalated |
| mcp-sandbox-independence-unproven | needs_research | medium | research | research_fetcher | checker | research | no | yes | passive evidence either proves enough for classification or a bounded future sandbox validation packet is defined |
| skill-presence-not-equal-host-readiness | ready_for_implementation | medium | implementation | promoter | reviewer | no | no | yes | host-readiness checks are encoded into policy/checklists/global-capability logic so skills are no longer mistaken for execution readiness |
| gateway-lock-dir-default-outside-shay-home | closed | medium | none | recorder/ledgerer | reviewer | no | no | no | `a644a0a` remains valid evidence that explicit `SHAY_GATEWAY_LOCK_DIR` is honored at helper/unit level and no contradictory evidence appears |

## Lock-Dir Closure Example

`gateway-lock-dir-default-outside-shay-home` is the reference example for narrow honest closure:
- closed question:
  - does helper/unit-level token-scoped lock creation honor explicit `SHAY_GATEWAY_LOCK_DIR`?
- evidence:
  - `a644a0a docs: validate Hermes sandbox lock-dir isolation`
- claim allowed:
  - yes, override-honoring is proven at helper/unit level
- claim forbidden:
  - no, this does not prove full messaging-platform runtime invocation behavior
