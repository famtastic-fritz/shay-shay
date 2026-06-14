# Shay Capability Gap Lifecycle Policy

Date: 2026-06-13
Scope: global Shay capability-gap policy, seeded from Hermes-removal sandbox evidence.
Status: planning and control policy only
Latest evidence incorporated:
- `a644a0a docs: validate Hermes sandbox lock-dir isolation`
- token-scoped lock-dir override is proven at helper/unit level
- `gateway-lock-dir-default-outside-shay-home` is closed for override behavior
- no full platform-runtime invocation proof is claimed

## Purpose

Capability gaps are not allowed to die as vague notes, residue, or "next action: none."

Every real gap must move into an explicit lifecycle state and must point to one of these next-motion buckets:
- watch item
- research task
- approval request
- sandbox validation
- adoption backlog candidate
- implementation task
- deferred risk
- closed finding

If Shay cannot name the next state, the gap has not been processed enough.

## Core Rules

1. Observation and interpretation stay separate.
2. A gap must be recorded before it can be solved.
3. Every recorded gap must have:
   - status
   - severity
   - risk
   - owner_role
   - checker_role
   - next_action
   - closure_criteria
4. "Next action: none" is forbidden unless the gap is explicitly:
   - false positive
   - duplicate
   - historical-only
   - accepted_risk
   - rejected
   - already closed
5. A gap may be closed narrowly. Helper/unit-level proof can close a helper/unit-level question without claiming runtime proof.
6. Closure must always say what was proven, what was not proven, and what would reopen the gap.
7. Research and watching are not implementations. They are evidence-gathering states.
8. Accepted risk is not silence. It is an explicit decision with mitigation and reopen conditions.

## Status Vocabulary

### observed
The issue has been seen but not normalized into a durable gap record yet.

Required evidence:
- at least one concrete observation or proof surface

Allowed transitions:
- `observed -> recorded`
- `observed -> duplicate`
- `observed -> rejected`

### recorded
The gap has a durable record with lane, evidence, fallback, and risk.

Required evidence:
- durable record exists
- blocked action or degraded capability is named

Allowed transitions:
- `recorded -> needs_research`
- `recorded -> watching`
- `recorded -> candidate_found`
- `recorded -> needs_approval`
- `recorded -> ready_for_sandbox`
- `recorded -> ready_for_implementation`
- `recorded -> partially_closed`
- `recorded -> deferred`
- `recorded -> rejected`
- `recorded -> duplicate`
- `recorded -> accepted_risk`
- `recorded -> closed`

### needs_research
The next honest move is evidence discovery, not execution.

Required evidence:
- the missing truth question is explicit
- approved source types are named

Allowed transitions:
- `needs_research -> candidate_found`
- `needs_research -> watching`
- `needs_research -> needs_approval`
- `needs_research -> ready_for_sandbox`
- `needs_research -> accepted_risk`
- `needs_research -> deferred`
- `needs_research -> rejected`

### watching
The gap is real, but the best move is cadence-based rechecking because the answer may change over time.

Required evidence:
- watch cadence is named
- approved sources are named
- stop condition is named

Allowed transitions:
- `watching -> candidate_found`
- `watching -> needs_approval`
- `watching -> ready_for_sandbox`
- `watching -> ready_for_implementation`
- `watching -> accepted_risk`
- `watching -> closed`
- `watching -> deferred`

### candidate_found
A plausible fix, workflow, upstream capability, or adoption path exists but is not yet approved or validated.

Required evidence:
- at least one source-backed candidate
- candidate scope and value stated

Allowed transitions:
- `candidate_found -> needs_approval`
- `candidate_found -> ready_for_sandbox`
- `candidate_found -> ready_for_implementation`
- `candidate_found -> rejected`
- `candidate_found -> deferred`

### needs_approval
The next useful step has side effects, cost, policy implications, or scope expansion and requires Fritz.

Required evidence:
- exact approval question is written
- the blocked side effect is named

Allowed transitions:
- `needs_approval -> ready_for_sandbox`
- `needs_approval -> ready_for_implementation`
- `needs_approval -> deferred`
- `needs_approval -> rejected`
- `needs_approval -> accepted_risk`

### ready_for_sandbox
The next safe step is a bounded sandbox-only validation packet.

Required evidence:
- exact safe test is written
- abort conditions are known
- required inputs are known

Allowed transitions:
- `ready_for_sandbox -> validated`
- `ready_for_sandbox -> partially_closed`
- `ready_for_sandbox -> needs_research`
- `ready_for_sandbox -> needs_approval`
- `ready_for_sandbox -> deferred`
- `ready_for_sandbox -> rejected`

### ready_for_implementation
Enough truth exists to create an implementation packet.

Required evidence:
- change target is known
- why it is ready is written
- required approval state is satisfied

Allowed transitions:
- `ready_for_implementation -> validated`
- `ready_for_implementation -> partially_closed`
- `ready_for_implementation -> deferred`
- `ready_for_implementation -> rejected`

### validated
The targeted claim has been proven in the intended scope.

Required evidence:
- validation method named
- scope of proof named
- proof artifacts named

Allowed transitions:
- `validated -> closed`
- `validated -> partially_closed`
- `validated -> accepted_risk`
- `validated -> ready_for_implementation`

### closed
The gap is resolved for its intended scope and no additional action is needed right now.

Required evidence:
- the original question is answered
- closure scope is explicit
- reopen trigger is named if applicable

Allowed transitions:
- `closed -> observed` only if new contradictory evidence appears

### partially_closed
Part of the gap is proven or resolved, but a broader claim remains intentionally open.

Required evidence:
- what is closed
- what remains open
- why the remaining portion is out of scope or deferred

Allowed transitions:
- `partially_closed -> needs_research`
- `partially_closed -> watching`
- `partially_closed -> needs_approval`
- `partially_closed -> ready_for_sandbox`
- `partially_closed -> ready_for_implementation`
- `partially_closed -> accepted_risk`
- `partially_closed -> closed`

### deferred
The gap is real but not worth action now.

Required evidence:
- deferral reason
- re-check trigger or date

Allowed transitions:
- `deferred -> needs_research`
- `deferred -> watching`
- `deferred -> needs_approval`
- `deferred -> ready_for_sandbox`
- `deferred -> ready_for_implementation`
- `deferred -> accepted_risk`
- `deferred -> closed`

### rejected
A proposed path was intentionally not adopted.

Required evidence:
- what was rejected
- why it was rejected

Allowed transitions:
- `rejected -> observed` only if a materially different path appears later

### duplicate
The gap is already represented elsewhere.

Required evidence:
- canonical gap_id reference

Allowed transitions:
- `duplicate -> observed` only if the canonical mapping was wrong

### accepted_risk
The gap is real, bounded, and intentionally tolerated with mitigation.

Required evidence:
- mitigation is explicit
- reason it is not worth immediate action is explicit
- reopen trigger is named

Allowed transitions:
- `accepted_risk -> needs_research`
- `accepted_risk -> watching`
- `accepted_risk -> needs_approval`
- `accepted_risk -> ready_for_sandbox`
- `accepted_risk -> ready_for_implementation`
- `accepted_risk -> closed`

## Allowed Next Actions

Canonical next_action vocabulary:
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

Rule:
- `none` is allowed only when the gap is false positive, duplicate, historical-only, accepted_risk, rejected, or already closed.

## Evidence Standards Per Motion Type

### To move into research
Need:
- exact missing question
- approved sources
- stop rule

### To move into watch
Need:
- cadence
- source type
- what would trigger escalation

### To move into approval
Need:
- exact approval question
- exact blocked side effect

### To move into sandbox validation
Need:
- exact safe test
- exact scope
- abort conditions

### To move into implementation
Need:
- why the issue is ready
- what artifact/process/code path would change
- what validation will confirm success

### To close
Need:
- exact question answered
- evidence path(s)
- remaining non-claims stated plainly

## Current Hermes Gap State Table

| gap_id | status | severity | next_action | owner_role | checker_role | research/watch needed | Fritz approval needed | adoption backlog | closure criteria |
|---|---|---|---|---|---|---|---|---|---|
| sandbox-no-local-venv | needs_approval | medium | approval | gatekeeper | reviewer | no | yes | yes | either create a sandbox-local `.venv` by approval and validate sandbox-local execution, or explicitly accept shared-venv coupling as long-term risk |
| path-missing-python-pytest-pip | accepted_risk | low | none | recorder/ledgerer | checker | no | no | no | exact-command rule remains documented and no current task requires generic PATH assumptions |
| sandbox-home-not-yet-startup-validated | partially_closed | medium | sandbox_test | runner | checker | no | yes, before any new runtime test | no | remaining unproven runtime edge is either validated in a bounded sandbox test or explicitly accepted as out-of-scope |
| hermes-external-client-usage-unknown | needs_research | high | research | research_fetcher | reviewer | research | no | yes | dependency surfaces for `hermes` are mapped enough to decide removal safety or deferral |
| provider-health-partial-only | watching | medium | watch | watcher | checker | watch | no | no | passive evidence becomes sufficient for the intended provider-dependent decision, or the need is explicitly escalated |
| mcp-sandbox-independence-unproven | needs_research | medium | research | research_fetcher | checker | research | no | yes | either passive evidence is enough to classify independence or a future sandbox proof packet is defined |
| skill-presence-not-equal-host-readiness | ready_for_implementation | medium | implementation | promoter | reviewer | no | no | yes | host-readiness checks are encoded into policy/checklists/global matrix logic so skill presence is no longer treated as readiness proof |
| gateway-lock-dir-default-outside-shay-home | closed | medium | none | recorder/ledgerer | reviewer | no | no | no | override-honoring question remains proven by `a644a0a` and no contradictory runtime-path evidence appears |

## Lock-Dir Result Integration

The latest lock-dir finding changes the lifecycle in one important way:
- `gateway-lock-dir-default-outside-shay-home` is not open anymore for the override-honoring question
- it is closed because `a644a0a` proved helper/unit-level lock creation respects explicit `SHAY_GATEWAY_LOCK_DIR`
- it is not partially_closed because the original narrow question was answered
- full messaging-platform runtime proof remains explicitly outside the closure claim

## “Next Action: None” Policy Applied To Current Hermes Gaps

Literal `next_action: none` is used only for:
- `path-missing-python-pytest-pip`
  - reason: accepted_risk with stable mitigation and no active blocked work
- `gateway-lock-dir-default-outside-shay-home`
  - reason: already closed for the exact override question validated in `a644a0a`

No other current Hermes gap qualifies for `none`.

## Globalization Path

To make this global later:
1. keep the same lifecycle vocabulary across lanes
2. attach gap IDs to local capability matrices
3. let watcher/research roles run read-only across approved source sets
4. route candidate findings into a shared adoption backlog
5. promote proven process rules into a future global Shay capability matrix
