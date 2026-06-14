# Shay Skills Gap Log

Date: 2026-06-13

## Purpose

Track the delta between a skill being present in the repo and that skill being honestly runnable in a declared lane.

## Current Findings

### skill-presence-not-equal-host-readiness
- status: ready_for_implementation
- why it exists:
  - the repo has a large skill catalog, but host tools, accounts, MCPs, and side-effect boundaries vary by lane
- evidence:
  - `docs/shay-skills-readiness-matrix-2026-06-13.yaml`
- next action: fix now
- recommendation:
  - use the readiness matrix as the default preflight surface before routing to a skill

### stale-duplicate-quarantine-review-needed
- status: recorded
- why it exists:
  - the skill catalog is healthy but not all skills are equally ready; some are candidate-only, blocked by missing deps, or should be quarantined by default
- evidence:
  - `docs/shay-skills-readiness-matrix-2026-06-13.yaml`
- next action: adopt tool
- recommendation:
  - run a later dedicated prune/review wave instead of treating every bundled skill as equally ready
