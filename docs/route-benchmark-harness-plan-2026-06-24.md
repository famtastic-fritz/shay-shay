# Route Benchmark Harness Plan

Date: 2026-06-24
Status: implementation plan
Depends on: docs/agent-template-routing-matrix-2026-06-24.md

## Purpose

Turn routing doctrine into measured evidence.

This plan defines how to test:
1. full broad natural-language swarm coverage
2. cheapest-sufficient routing by agent class
3. controller-path adoption across live lanes
4. fanout scaling ladder
5. live model behavior under bounded production load

## Phase 1 — Agent-class benchmark packets

Create benchmark packet sets for these templates:
- scout
- builder
- critic
- reviewer
- clerk
- watcher
- browser-operator
- captain-router

Each benchmark packet should include:
- packet_id
- template_id
- task_family
- task_subtype
- prompt/input artifact
- required toolsets
- required output contract
- verification method
- cost sensitivity class
- escalation condition

### Packet counts (first wave)
- Scout: 12
- Builder: 12
- Critic: 8
- Reviewer: 8
- Clerk: 8
- Watcher: 6
- Browser Operator: 8
- Captain / Router: 6

Total first-wave packets: 68

## Phase 2 — Candidate route matrix

For each template, test at least three route classes when available:
- cheapest sufficient candidate
- stronger reasoning candidate
- premium escalation candidate

Record for each run:
- provider
- model
- runtime surface
- toolsets
- prompt budget
- latency
- token in/out if available
- estimated cost
- pass/fail
- verification pass/fail
- reviewer verdict if applicable
- correction count
- notes

## Phase 3 — NL ask coverage harness

Build a coverage corpus of natural-language asks.

### Coverage families
- build
- review
- resume
- deploy
- research
- recall
- monitoring
- design
- content
- browser/UI
- admin/attention
- swarm/captain asks

### Corpus size target
- 15 asks per family for first wave
- 12 families x 15 = 180 asks

For each ask, record:
- expected intent
- expected template
- acceptable fallback template
- actual `shay intelligence trace` result
- actual `shay intelligence route` result
- verdict: correct / acceptable / generic fallback / wrong

### First success target
- 85% correct-or-acceptable on top-priority families:
  - build
  - review
  - research
  - monitoring
  - browser/UI

## Phase 4 — Live lane conversion checklist

Convert one lane at a time to the controller path.

### Lane order
1. build lane
2. reviewer lane
3. resume lane
4. research lane
5. browser verification lane

### Required proof for each lane
- packet plan exists before dispatch
- worker packets have role/wave/tier/schema metadata
- ledger entries exist before completion
- reviewer separation enforced when applicable
- final report artifact written
- route explanation recorded

A lane is not counted as converted unless all six proofs exist.

## Phase 5 — Fanout load ladder

Scale gradually.

### Stages
- stage A: 5 workers
- stage B: 20 workers
- stage C: 50 workers
- stage D: 100 workers
- stage E: 300 workers

### At each stage capture
- dispatch success rate
- queue latency
- reconciliation latency
- reviewer bottleneck rate
- provider/runtime failures
- token/cost burn rate
- memory/process pressure
- orphaned worker count

### Advancement rule
Do not advance to the next stage until the current stage is boring:
- stable success rate
- controlled cost
- no reconciliation corruption
- no persistent orphan/stranded worker pattern

## Phase 6 — Live bounded production soak

After lanes and fanout ladders are stable, run bounded live tasks.

### Soak goals
- confirm route quality over repeated runs
- observe model drift or instability
- confirm cost routing remains sane
- catch premium over-routing

### Bounded soak rules
- fixed daily budget
- fixed packet families
- explicit reviewer gates on high-stakes tasks
- automatic logging of provider/model/runtime used

## Scorecard schema

Every benchmark should roll into scorecards with at least:
- template_id
- task_family
- provider
- model
- run_count
- success_rate
- verification_pass_rate
- correction_rate
- median_latency_ms
- median_estimated_cost
- reviewer_approval_rate
- last_good_run
- last_bad_run
- notes

## Completion definitions

### Full broad NL swarm coverage
Complete when:
- coverage corpus exists
- corpus is runnable
- top-priority families hit the success target
- generic fallback rate is visible and shrinking

### Cheapest-sufficient model brokerage
Complete when:
- each template has measured default + escalation lanes
- scorecards justify the assignment
- downgrade bans are enforced for reviewer-grade work

### 300-agent production fanout
Complete when:
- stages A-E are executed in order
- costs and failure rates are recorded
- reviewer/reconciliation integrity survives scale

### Every live lane using controller path
Complete when:
- all target lanes show the six required proofs

### End-to-end live model behavior under production load
Complete when:
- bounded soak runs produce stable scorecards over time
- premium over-routing is visible and controllable
- live failures are classified into route, model, tool, or reconciliation causes

## What still requires Fritz authority

These are not engineering unknowns; they are owner decisions:
- acceptable daily/monthly cost ceilings by lane
- allowed premium-by-default cases
- which providers/models are blessed for production lanes
- what risk threshold justifies reviewer escalation automatically
- when a benchmark result is good enough to become doctrine

## Immediate implementation recommendation

Next code wave should build:
1. benchmark packet file format
2. scorecard record schema
3. NL ask corpus file format
4. command(s) to run packet sets and save results
5. route-explanation outputs tied back to this matrix
