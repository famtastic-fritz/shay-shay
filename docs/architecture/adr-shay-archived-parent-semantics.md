# ADR: Archived Kanban parents remain unsatisfied

- Status: accepted for R1
- Date: 2026-09-16
- Scope: task creation, dependency recomputation, and claim-time enforcement

## Decision

Only a parent whose status is `done` satisfies a child dependency. An
`archived` parent records removal or abandonment, not successful output, so it
continues to block the child in `todo`. The same rule applies when a child was
incorrectly forced to `ready`: the claim gate demotes it and refuses the claim.

This keeps creation, link demotion, unblocking, `parent_results()`, readiness
recomputation, and claim enforcement on one rule. It also avoids silently
authorizing downstream work when a prerequisite was abandoned.

## Operator remedy

An archived dependency must be explicitly removed or replaced before the
child can proceed. Operators can unlink the archived parent or create and link
a replacement task that produces the required result. Archival alone never
promotes dependents.

## Consequences

Children can intentionally remain waiting indefinitely after a parent is
archived. That state is visible and safe: it requires an explicit operator
decision rather than treating abandonment as success. This R1 decision does
not add migrations or alter historical task rows; durable lifecycle recovery
remains a later phase concern.

## Verification environment note

The program's immutable V4 provenance marker remains an external, read-only
artifact bound to the Phase 0 reviewed tree (`cf6bb95e`). Its recorded
`pip_freeze --all` digest is `a866bb917aad926a610936ea772d377016a85d00ec9bbe45ce6dabb66f4a65c6`,
but the shared V4 environment's editable install now points at the R1 worktree
(`29f5fbef`) and produces the different observed digest
`2e00c655979537f0f56693e905b8c821f2c2a99da0af9bd3d0fd7582c8c91f0e`.
The committed runner therefore rejects that marker rather than accepting a
false provenance claim. R1 local checks use a fresh, mode-0400 portable marker
whose lock and source hashes are computed from this worktree; no V4 marker or
owner environment was rewritten.
