# Routing Benchmark Artifact Wiring

Date: 2026-06-24
Status: implementation wiring note

## Purpose

Tie the new routing artifacts together so the next code wave can expose them through runnable command surfaces instead of leaving them as isolated docs.

## New artifacts

1. Agent-template registry draft
- `docs/agent-template-routing-matrix-2026-06-24.md`

2. Benchmark packet seed set
- `docs/benchmark-packets-wave-1-2026-06-24.yaml`

3. NL ask coverage corpus seed set
- `docs/nl-ask-coverage-corpus-wave-1-2026-06-24.yaml`

4. Route scorecard schema
- `docs/route-scorecard-schema-2026-06-24.yaml`

5. Benchmark program plan
- `docs/route-benchmark-harness-plan-2026-06-24.md`

## Intended future runner commands

These commands do not exist yet. They are the next useful code targets.

### 1. Packet runner
Suggested shape:
- `shay intelligence benchmark run --packets docs/benchmark-packets-wave-1-2026-06-24.yaml`

Expected behavior:
- load packet file
- validate packet schema
- route each packet through candidate lanes
- save run records and raw outcomes
- emit a batch summary

### 2. NL coverage runner
Suggested shape:
- `shay intelligence benchmark coverage --corpus docs/nl-ask-coverage-corpus-wave-1-2026-06-24.yaml`

Expected behavior:
- run `trace` and `route` for each ask
- compare actual vs expected template/intent
- mark verdict as correct / acceptable / generic_fallback / wrong
- save coverage report artifact

### 3. Scorecard reducer
Suggested shape:
- `shay intelligence benchmark scorecards --runs <path-or-run-group>`

Expected behavior:
- aggregate packet run outcomes into the scorecard schema
- keep separate views by template, task family, provider/model, and route class
- emit promotion candidates and escalation warnings

### 4. Live lane audit
Suggested shape:
- `shay intelligence benchmark lane-audit --lane build`

Expected behavior:
- inspect whether a live lane follows controller-path requirements
- confirm packet metadata, ledger-first ordering, reviewer separation, and report artifacts

## File-role mapping

| Artifact | Role now | Role later |
|---|---|---|
| agent-template-routing-matrix | human-readable route doctrine | source to seed template registry |
| benchmark-packets-wave-1 | seed packet definitions | runnable benchmark input |
| nl-ask-coverage-corpus-wave-1 | seed ask corpus | runnable route/trace coverage input |
| route-scorecard-schema | aggregation contract | output/report schema |
| route-benchmark-harness-plan | program design | rollout checklist |

## Minimal implementation sequence

1. Add YAML loaders + validators for packet corpus and scorecard schema.
2. Add a benchmark runner under `shay_cli/intelligence_cmd.py` or adjacent helper module.
3. Save raw run outputs under a generated benchmark artifact directory.
4. Add a reducer that emits scorecards matching `docs/route-scorecard-schema-2026-06-24.yaml`.
5. Add a coverage command for the NL ask corpus.

## Proof standard for the next wave

The next wave counts as real only if it can:
- read the seeded packet file
- read the seeded NL corpus file
- produce at least one scorecard artifact
- produce at least one coverage report artifact
- explain why a route was chosen
