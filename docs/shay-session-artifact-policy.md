# Shay-Shay session artifact policy

Status: canonical policy
Last updated: 2026-06-12
Scope: session JSON artifacts and related bookkeeping files under `~/.shay/sessions/`

## Purpose

This policy defines how session JSON artifacts should be interpreted so operators do not confuse them with the canonical conversation recall layer.

## Canonical rule

The canonical historical conversation store is:
- `~/.shay/state.db`

Session JSON artifacts are not the primary recall source unless runtime documentation and code explicitly state otherwise for a specific compatibility path.

## What lives here today

Under `~/.shay/sessions/` there may be:
- legacy per-session JSON files
- JSONL fragments from older persistence flows
- `sessions.json` and similar index/bookkeeping files used by gateway/session management code

## Classification

Treat these artifacts as one of three things:
1. legacy transcript residue
2. compatibility artifacts
3. bookkeeping/index files

Do not treat them as the authoritative memory system just because they are numerous or easy to browse.

## Operational policy

1. Do not assume session JSON files are canonical recall.
2. Check `state.db` first for historical conversation truth.
3. Preserve JSON artifacts until a deliberate prune/archive plan is approved.
4. If a specific runtime seam still depends on a JSON index file, document that seam explicitly.
5. Avoid writing new docs that imply JSON session artifacts are the main historical memory layer.

## Documentation rule

When session artifacts are mentioned, docs should clearly say one of the following:
- canonical historical recall lives in `state.db`
- JSON artifacts remain for compatibility, bookkeeping, or legacy reasons

## This phase policy boundary

This policy does not authorize deleting, moving, or pruning any session JSON files.
It only defines how they should be classified and described.

## Future Phase 2+ questions

Deferred questions for later phases:
- Which JSON artifacts are still touched by runtime code?
- Which are safe to archive?
- Which should be marked as compatibility-only?
- Should the repo include a maintenance command or audit doc for these artifacts?

## Related docs

- `docs/shay-memory-hierarchy.md`
- `docs/shay-db-status.md`
- `docs/shay-memory-architecture-review-2026-06-12.md`
