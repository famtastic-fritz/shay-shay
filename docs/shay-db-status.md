# Shay-Shay shay.db status

Status: canonical status note
Last updated: 2026-06-12
Scope: `~/.shay/shay.db`

## Current observed state

Observed during the 2026-06-12 memory architecture review:
- path: `~/.shay/shay.db`
- file exists
- size observed: 0 bytes
- tables observed: none

## Current interpretation

At the time of review, `shay.db` does not appear to be an active canonical runtime store.

It should therefore be treated as:
- non-canonical until proven otherwise
- dormant or placeholder until a documented runtime role exists
- lower priority than `state.db` for any memory or recall investigation

## Canonical rule

For conversation/session recall, use:
- `~/.shay/state.db`

Do not assume `shay.db` is authoritative just because it has a database-like name.

## Documentation rule

Until runtime code or future implementation gives `shay.db` a real role, docs should describe it carefully:
- present on disk
- currently not observed as an active memory source
- not a substitute for `state.db`

## This phase policy boundary

This phase does not:
- delete `shay.db`
- move `shay.db`
- repurpose `shay.db`
- declare it permanently useless

It only documents current status so the surface is not misread.

## Future Phase 2+ questions

Deferred for later investigation:
- Is `shay.db` created by an abandoned path, a placeholder, or another subsystem?
- Should it be removed from operator mental models entirely?
- Should runtime diagnostics explicitly label it dormant when empty?

## Related docs

- `docs/shay-memory-hierarchy.md`
- `docs/shay-session-artifact-policy.md`
- `docs/shay-memory-architecture-review-2026-06-12.md`
