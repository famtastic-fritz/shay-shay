# Agent Template Routing Matrix

Date: 2026-06-24
Status: first operational draft
Authority class: recommendation + benchmark target, not yet telemetry-proven truth

## Purpose

Create the first concrete registry artifact for agent-class routing so Shay can stop treating model assignment as loose doctrine only.

This matrix defines:
- agent template
- task families served
- success standard
- default lane
- escalation lane
- forbidden downgrade cases
- verification path
- benchmark packet family

## Routing principles

1. Default to the cheapest sufficient lane.
2. Do not downgrade grounded review below the level needed to cite artifacts.
3. Prefer capability-fit over raw intelligence prestige.
4. Escalate on contradiction, ambiguity collapse, or repeated failed verification.
5. Browser/UI work is capability-first, not prestige-model-first.

## Lane vocabulary

- cheap: orchestration / retrieval / monitoring / low-risk summarization
- mid: implementation / debugging / structured reasoning / synthesis
- premium: adversarial review / high-stakes judgment / ambiguity collapse / irreversible-risk decisions
- capability-first: route by surface/tool modality first, then choose the cheapest sufficient model inside that surface

## Template registry

### 1. Scout
- template_id: scout
- role_name: Scout
- task_families:
  - research
  - recall
  - gap-finding
  - monitoring
  - triage
- required_capabilities:
  - search
  - retrieval
  - summarization
  - contradiction spotting
- default_lane:
  - tier: cheap
  - route_intent: retrieval-first then summarization
- escalation_lane:
  - tier: mid
  - trigger: conflicting sources remain after retrieval, or synthesis requires reasoning across multiple contradictory surfaces
- forbidden_downgrade_cases:
  - do not pretend artifact-grounded review is scout work
- verification_path:
  - source list present
  - contradiction note present when applicable
  - retrieval outputs attributable to concrete surfaces
- benchmark_packet_family:
  - prior-session recall
  - repo state scan
  - market scan
  - contradiction summary

### 2. Builder
- template_id: builder
- role_name: Builder
- task_families:
  - implementation
  - bug-fixing
  - CLI wiring
  - tests
  - refactors
- required_capabilities:
  - code reading
  - code editing
  - test execution
  - failure interpretation
- default_lane:
  - tier: mid
  - route_intent: code-capable lane with strong tool use
- escalation_lane:
  - tier: premium
  - trigger: ambiguity collapse, architecture-crossing root cause, or repeated failed implementation attempts
- forbidden_downgrade_cases:
  - do not push non-trivial code surgery into cheap-only routing
- verification_path:
  - patch diff exists
  - compile/test proof exists
  - changed behavior is described with evidence
- benchmark_packet_family:
  - bug fix
  - feature patch
  - CLI command wiring
  - targeted test repair

### 3. Critic
- template_id: critic
- role_name: Critic
- task_families:
  - defect finding
  - tradeoff review
  - implementation criticism
  - plan pressure testing
- required_capabilities:
  - comparative reasoning
  - failure-mode analysis
  - architecture reading
- default_lane:
  - tier: mid
  - route_intent: review-capable reasoning lane
- escalation_lane:
  - tier: premium
  - trigger: high-stakes architecture, revenue risk, deployment risk, or disagreement between builder and critic
- forbidden_downgrade_cases:
  - do not use cheap review when defect cost is high
- verification_path:
  - objections are concrete
  - each major objection ties to code/artifact evidence
  - recommendations include tradeoffs
- benchmark_packet_family:
  - plan review
  - diff critique
  - architecture pressure test

### 4. Reviewer
- template_id: reviewer
- role_name: Reviewer
- task_families:
  - adversarial review
  - grounding checks
  - acceptance gate
  - reconciliation judgment
- required_capabilities:
  - grounded artifact reading
  - schema compliance checks
  - citation-ready objections
- default_lane:
  - tier: premium
  - route_intent: grounded review lane with enough reasoning to verify claims against artifacts
- escalation_lane:
  - tier: premium
  - trigger: multiple artifacts, financial/security risk, or contradictory producer outputs
- forbidden_downgrade_cases:
  - never route artifact-grounded review to cheap-only models
  - never let a worker review itself
- verification_path:
  - cites artifact rows/lines/files
  - reproduces the claim against the source
  - returns approve/revise with explicit reasons
- benchmark_packet_family:
  - adversarial artifact review
  - ledger acceptance gate
  - diff acceptance gate

### 5. Clerk
- template_id: clerk
- role_name: Clerk
- task_families:
  - attention board
  - queue summary
  - cron/process monitoring
  - status collection
  - recap generation
- required_capabilities:
  - listing
  - ranking
  - summarization
  - exception detection
- default_lane:
  - tier: cheap
  - route_intent: command-truth-first, summarize exceptions only
- escalation_lane:
  - tier: mid
  - trigger: priority conflicts or contradictory signals need adjudication
- forbidden_downgrade_cases:
  - none beyond basic truth-surface grounding
- verification_path:
  - every surfaced item maps to a concrete process/todo/cron/session signal
  - report is exception-oriented, not dump-oriented
- benchmark_packet_family:
  - what needs my attention
  - stuck-work board
  - running-now summary

### 6. Watcher
- template_id: watcher
- role_name: Watcher
- task_families:
  - ongoing health watch
  - anomaly detection
  - spend watch
  - long-run supervision
- required_capabilities:
  - thresholding
  - change detection
  - alert suppression
- default_lane:
  - tier: cheap
  - route_intent: low-cost continuous monitoring with minimal narrative
- escalation_lane:
  - tier: mid
  - trigger: anomalous pattern needs diagnosis rather than alerting
- forbidden_downgrade_cases:
  - do not use premium for routine status watching
- verification_path:
  - alerts tied to explicit threshold/signal
  - silence when nothing actionable changed
- benchmark_packet_family:
  - budget watch
  - queue drift watch
  - stuck mission detection

### 7. Browser Operator
- template_id: browser-operator
- role_name: Browser Operator
- task_families:
  - Playwright/browser testing
  - UI verification
  - form traversal
  - screenshot/state comparison
- required_capabilities:
  - browser automation
  - DOM/state inspection
  - deterministic step execution
- default_lane:
  - tier: capability-first
  - route_intent: browser surface first, then cheapest sufficient model for orchestration around it
- escalation_lane:
  - tier: mid
  - trigger: ambiguous UI state, multi-step dynamic flows, or visual mismatch requiring stronger reasoning
- forbidden_downgrade_cases:
  - do not replace browser truth with guessed text-only reasoning
- verification_path:
  - user-visible flow executed
  - DOM/screenshot evidence captured
  - result tied to actual UI state
- benchmark_packet_family:
  - loginless flow test
  - checkout/contact flow test
  - regression verification

### 8. Captain / Router
- template_id: captain-router
- role_name: Captain / Router
- task_families:
  - swarm planning
  - lane selection
  - packet generation
  - reconciliation
- required_capabilities:
  - decomposition
  - dependency planning
  - routing discipline
  - ledger awareness
- default_lane:
  - tier: cheap
  - route_intent: cheap orchestration by default
- escalation_lane:
  - tier: mid
  - trigger: packet design ambiguity, cross-lane conflicts, or repeated reconciliation failure
- forbidden_downgrade_cases:
  - do not use premium by default just because the swarm is large
- verification_path:
  - plan exists
  - worker/reviewer separation exists
  - packet metadata complete
  - ledger-first path observable
- benchmark_packet_family:
  - safe dry-run
  - live lane plan
  - multi-wave route packet set

## Initial route rules by template

| Template | Default | Escalate | Never do |
|---|---|---|---|
| Scout | cheap | mid | pretend grounded review is cheap research |
| Builder | mid | premium | force serious code work into cheap-only lane |
| Critic | mid | premium | cheap-only review on high-cost defects |
| Reviewer | premium | premium | downgrade artifact-grounded review |
| Clerk | cheap | mid | replace truth surfaces with narrative guesses |
| Watcher | cheap | mid | spend premium on routine monitoring |
| Browser Operator | capability-first | mid | skip browser execution and guess from prose |
| Captain / Router | cheap | mid | set premium as swarm default |

## What this is not yet

This is not a telemetry-proven registry yet.

It is a production-shaped recommendation artifact to drive:
- benchmark design
- route scorecard collection
- future live lane assignment
- future registry commands

## Required next step

Use this matrix to create benchmark packets and scorecards so routing can move from doctrine to measured evidence.
