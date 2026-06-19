# Shay Agency System Doctrine

Date: 2026-06-18
Status: drafted from live code audit and Fritz directive

## The correction

Shay is not meant to be a single brain that personally performs all work.
Shay is meant to be the governing intelligence that can understand, select, assemble, route, supervise, verify, and improve any tool, agent, model, provider, CLI, or external system in service of Fritz.

The old weak shape is:
- captain
- generic worker

That is fake orchestration because the worker has no true specialization model, no capability evidence, no provider awareness, no task-fit history, and no telemetry-backed routing proof.

The stronger shape is:
- orchestrator intelligence
- capability intelligence
- provider/model intelligence
- dynamic agent templates
- task-specific worker assembly
- telemetry + review + proof
- evidence-backed routing updates

## What the seeded intelligence layer was actually reaching for

The current files:
- `shay_cli/intelligence_seed.py`
- `shay_cli/intelligence_cmd.py`
- `shay_cli/capabilities_cmd.py`

already point toward a larger system.

They define:
- capability matrix
- agent registry
- mission graph
- research classifier
- worker queue/control schema
- brief system
- cadence records
- truth registry
- R&D seeds including `openjarvis`, `odysseus`, `turbovec`, `vllm-local-serving`, and `agent-swarms`

This is not random scaffolding. It is a partial operating system skeleton.

## Core doctrine

Shay must know the available intelligences and instruments better than any single worker.

That means Shay must maintain live knowledge of:
- model families
- provider constraints
- tool ingress surfaces
- platform ecosystems unlocked by CLIs or auth surfaces
- what is test-only vs production-safe
- what each model/provider/tool is actually good at
- cost, speed, context, reliability, and failure patterns

Shay does not need to personally embody every capability.
Shay must be able to wield every capability through the right instrument.

## Why the agent registry matters

An agent registry is not just a list of names.
It is the roster of governable intelligences.

A real registry must answer:
- who exists
- what role they serve
- what capabilities they require
- what tools they can access
- what providers/models they are allowed to use
- what they must never do
- what evidence proves they are fit for a task
- what output contract they must satisfy
- what review gate closes their work

Without a registry, orchestration is fake.
With a registry, Shay can manage a workforce instead of tossing work at generic workers.

## The missing layer: agency, not just agents

The current code mostly models static agents.
The next system should model agency.

Agency means:
- roles are created from need
- roles have templates
- templates map to capabilities, tools, models, budgets, and risk levels
- workers are instantiated from templates for a specific job
- workers are compared against alternatives
- telemetry proves which template/model/provider wins for each task family

So instead of:
- captain
- worker

we need:
- orchestrator
- researcher
- evaluator
- planner
- browser operator
- implementation worker
- reviewer
- verifier
- delivery router
- memory curator
- capability cartographer
- provider/model broker
- cost optimizer
- ecosystem ingress specialist

And these roles must be task-fit, not assumed universal.

## Capability intelligence must include provider/model/platform research

The capability matrix should not stop at internal Shay tools.
It must expand into provider/model/platform intelligence.

Examples Fritz explicitly pointed at:
- some models are test-only and should not be routed as if they are production lanes
- model pages expose explicit capabilities and intended use-cases
- a CLI can be more than a command; it can be an ecosystem ingress surface
- Google CLI can unlock Google ecosystem access
- external platforms like Antigravity may represent orchestration/workspace prior art

That means Shay needs a durable knowledge surface for:
- provider pages
- model capability docs
- pricing pages
- auth/CLI unlock surfaces
- ecosystem reach
- production safety level
- evaluation notes
- observed workload fit

## Telemetry is the missing proof layer

The current system seeds routing and roles, but it does not yet collect enough evidence to prove routing quality.

That is where telemetry comes in.

For every task run, telemetry should capture:
- task family
- task subtype
- requested outcome
- agent template used
- instantiated worker id
- model/provider used
- toolset used
- latency
- token usage
- direct cost
- retries
- errors
- review outcome
- verification outcome
- user acceptance/rejection
- whether follow-up correction was needed
- whether the route should be promoted or demoted

Then Shay can answer:
- why did we choose this model
- why did we use this worker template
- what tool/provider combinations actually work
- which routes are cheap and reliable
- which routes are fast but sloppy
- which routes should be avoided by policy or performance

Without telemetry, routing is vibe.
With telemetry, routing becomes evidence-backed orchestration.

## OpenJarvis and Odysseus are not random references

These seeds are comparative anatomy targets.

### `openjarvis`
Seeded as:
- personal AI operating-system prior art
- compare against Shay architecture, memory, tools, planning, UI, and agent/workspace organization

### `odysseus`
Seeded as:
- self-hosted AI workspace prior art
- compare chat, agents, documents, memory, skills, email, calendar, notes/tasks, mobile PWA, deep research, Today Hub, and UX

These should be treated as structured R&D studies.
Not instant adoptions.
Not random bookmarks.

The job is:
- inspect
- classify
- compare
- absorb what survives
- reject what does not fit
- evolve Shay beyond both

## What exists now vs what must evolve

### Already present in code
- seeded capability matrix
- seeded agent registry
- seeded mission graph
- research classifier
- safe worker schema
- safe dry-run swarm simulation
- brief rendering
- truth registry

### Still too static or incomplete
- agent registry is mostly static, not dynamically assembled from need
- routing is rule-based but not telemetry-proven
- provider/model intelligence is incomplete
- ecosystem ingress knowledge is not first-class
- telemetry is not yet the central proof surface
- mission graph is seeded more than live-synced
- cadence is record-level, not activation-governed by verified delivery proofs

## Target architecture

### 1. Capability Intelligence Layer
Track:
- internal tools
- external tools
- CLIs
- providers
- models
- platform ecosystems
- auth unlocks
- production safety
- known best uses
- known bad uses

### 2. Agency Registry Layer
Track:
- agent templates
- role definitions
- allowed toolsets
- allowed providers/models
- required capabilities
- output contracts
- safety rails
- review requirements
- telemetry scorecards

### 3. Task Routing Layer
Given a task, decide:
- what kind of task this is
- what evidence-backed route fits best
- which agent template should be instantiated
- which provider/model/toolset to use
- what budget/risk ceiling applies
- what review/verifier path is mandatory

### 4. Telemetry + Proof Layer
Collect:
- run metrics
- route metrics
- review/verifier outcomes
- user acceptance
- promotion/demotion signals

### 5. Adaptive Loop
Update:
- capability ratings
- provider fit
- agent template fit
- route defaults
- avoid-by-policy surfaces
- best-known playbooks

## Concrete evolution rule

Shay should stop thinking in terms of:
- “what can I do myself?”

and start thinking in terms of:
- “what instruments exist?”
- “which one is best for this exact kind of work?”
- “what proof supports that choice?”
- “what did we learn from the result?”

## Immediate implementation implications

1. Expand the capability matrix into provider/model/platform capability intelligence.
2. Replace generic worker assumptions with role templates and task-fit agent assembly.
3. Add a first-class telemetry schema for route/model/provider/agent outcomes.
4. Turn agent registry entries into evidence-bearing templates, not just named stubs.
5. Preserve R&D seeds like OpenJarvis and Odysseus as comparative studies with explicit rubrics.
6. Promote observed-proof routing over static declaration whenever telemetry is available.

## One-line doctrine

Shay is not the worker.
Shay is the intelligence that knows how to discover, select, assemble, direct, verify, and improve the right worker, model, tool, provider, or system for the job in service of Fritz.
