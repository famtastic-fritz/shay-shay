# Shay Adoption Backlog Policy

Date: 2026-06-13

## Purpose

The adoption backlog is where source-backed candidate fixes, workflow upgrades, and capability-system improvements wait until they are ready for approval, sandbox proof, or implementation.

## Rules

- Do not add backlog items without a source gap or concrete candidate.
- Each item must name expected value, risk, cost, proof still needed, and whether Fritz approval is required.
- Backlog presence does not equal approval.
- Backlog items should be pruned, merged, or superseded when stale.
- Add = Audit + Prune: every newly-added external-usage or promotion item must trigger a check for stale, duplicate, superseded, or draft-only Hermes planning docs.
- Secret-bearing evidence stays redacted in backlog-adjacent planning artifacts; record paths and surface names, not values.

## Allowed Statuses

- proposed
- waiting_for_research
- waiting_for_approval
- ready_for_sandbox
- ready_for_implementation
- deferred
- rejected
- adopted
- superseded
