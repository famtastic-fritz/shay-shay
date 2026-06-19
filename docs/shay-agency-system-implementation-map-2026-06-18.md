# Shay Agency System Implementation Map

Date: 2026-06-18
Status: derived from live code audit

## Purpose

Translate the seeded intelligence layer into the next concrete system shape:
- not captain + generic worker
- but orchestrator + capability intelligence + dynamic agency + telemetry-backed routing

## Current truth surfaces

### Existing code surfaces
- `shay_cli/capabilities_cmd.py`
- `shay_cli/intelligence_cmd.py`
- `shay_cli/intelligence_seed.py`
- `tests/test_capabilities_cmd.py`
- `tests/test_intelligence_layer.py`

### Existing concepts already present
- capability matrix
- agent registry
- truth registry
- mission graph
- research classifier
- worker schema
- swarm dry-run
- briefs
- cadence records
- R&D seeds

## The key architectural problem

The current registry and worker system are too static.
They encode named roles, but they do not yet create evidence-backed task-fit agency.

Right now the system mostly answers:
- what agents are called
- what seeded capabilities exist

It does not answer well enough:
- which model/provider/tool route is best for this exact task type
- what objective evidence supports the choice
- what ecosystem access surface a given CLI or platform unlocks
- what the observed performance history of a role-template/model combination is

## Required new layers

### 1. Provider and model intelligence registry

Add a first-class registry for:
- provider id
- model id
- release tier
- test-only vs production-ready
- context length
- reasoning/tool/web/code/browser support
- auth surface
- ecosystem unlocks
- pricing / cost class
- latency class
- reliability notes
- recommended task families
- disallowed task families
- source URLs / docs pointers
- last verified timestamp

This should become routable truth, not scattered memory.

### 2. Capability expansion beyond internal tools

Current capability entries focus heavily on Shay-side functions.
Expand into:
- provider capabilities
- model capabilities
- CLI ecosystem ingress
- platform orchestration surfaces
- research targets and prior-art systems

A capability should be able to represent:
- internal tool
- external CLI
- provider lane
- model lane
- integration surface
- ecosystem access path
- prior-art system

### 3. Agent templates instead of fixed generic workers

Split “agent registry” into:
- registry of templates
- instantiated workers

Template fields should include:
- template id
- role name
- task families served
- required capabilities
- preferred providers/models
- allowed tools
- forbidden tools
- budget profile
- latency profile
- verification path
- output contract shape
- redaction rules
- escalation rules

Examples:
- provider-intel-researcher
- model-capability-cartographer
- ecosystem-ingress-mapper
- route-evaluator
- implementation-worker
- browser-operator
- verifier
- review-judge
- memory-curator
- delivery-router

### 4. Telemetry schema

Add durable telemetry records for every routed task.

Suggested schema:
- run_id
- task_id
- task_family
- task_subtype
- requested_outcome
- template_id
- instantiated_agent_id
- provider
- model
- toolsets
- start_time
- end_time
- latency_ms
- token_in
- token_out
- estimated_cost
- success
- review_outcome
- verification_outcome
- user_acceptance
- correction_required
- retries
- failure_mode
- route_confidence_before
- route_confidence_after
- notes

This should support aggregation.

### 5. Routing scorecards

Each route should accumulate evidence:
- success rate
- correction rate
- verification pass rate
- median latency
- median cost
- user acceptance rate
- best task families
- worst task families
- last seen good run
- last seen bad run

Then route selection can move from static rules toward weighted evidence.

## Where to evolve current files

### `shay_cli/intelligence_seed.py`
Keep as seed layer for:
- baseline capabilities
- baseline templates
- baseline mission/brief/cadence definitions

But stop treating it as the main truth surface once observed telemetry exists.

### `shay_cli/intelligence_cmd.py`
Evolve into command surface for:
- provider registry views
- model registry views
- template registry views
- telemetry summaries
- route scorecards
- comparative R&D studies
- evidence-backed route explanation

New likely commands:
- `shay intelligence providers`
- `shay intelligence models`
- `shay intelligence templates`
- `shay intelligence telemetry`
- `shay intelligence scorecards`
- `shay intelligence compare <system-or-model>`
- `shay intelligence explain-route <task>`

### `shay_cli/capabilities_cmd.py`
Evolve from static gatekeeper to evidence-aware router.

It should answer:
- what route is available
- what route is safe
- what route is recommended
- what proof supports the recommendation
- what alternatives were rejected and why

## R&D seeds that need dedicated comparative study packets

### OpenJarvis
Study dimensions:
- personal AI OS structure
- memory surfaces
- workspace design
- tool routing
- agent coordination
- UI concept
- planning system

### Odysseus
Study dimensions:
- self-hosted workspace UX
- multi-surface workbench design
- notes/tasks/docs integration
- mobile/PWA implications
- deep research flow
- Today Hub analogs

### Others already seeded
- TurboVec
- vLLM local serving
- agent swarms / OpenSwarm / agency-swarm / HyperSwarm doctrine

Each R&D item should get:
- source pointers
- comparative rubric
- adoption risk
- absorb/reject notes
- follow-up tasks

## Concrete next code targets

1. Add provider/model registry module.
2. Add telemetry schema + storage module.
3. Refactor agent registry into template registry + worker instances.
4. Add route explanation command backed by evidence, not only policy.
5. Add comparative-study artifact format for OpenJarvis and Odysseus.
6. Add ecosystem-ingress tracking for CLIs/platforms/auth unlocks.

## Success condition

The system is no longer done when it can spawn a worker.
It is done when Shay can justify, with evidence:
- why this route
- why this model
- why this template
- why this provider
- why this cost
- why this review path
- what was learned from the outcome

## One-line implementation principle

Every agent, model, tool, CLI, and provider should become a measured instrument in Shay’s agency system, not an unexamined option on a shelf.
