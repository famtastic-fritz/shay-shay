# Shay-Shay private memory policy

Status: canonical policy
Last updated: 2026-06-12
Scope: `~/.shay/private/`

## Purpose

This policy defines what the private memory vault is for, what it is not for, and how it relates to the rest of Shay's memory stack.

## Current role

Private memory lives under:
- `~/.shay/private/`

Current intended content classes:
- thinking logs
- private observations
- strategy notes
- dreams / interpretation notes
- other material intentionally kept outside the shared vault path

## Current access model

The private vault is:
- not part of default prompt injection
- not part of the shared Obsidian vault
- not indexed by shared `basic-memory` project search
- not surfaced by `vault-search`

That isolation is intentional.

## Canonical policy

1. The private vault is private-by-default.
2. The private vault is not canonical prompt memory.
3. The private vault is not canonical shared knowledge.
4. Any retrieval path into private memory must be explicit and opt-in.
5. Private memory must not silently leak into shared retrieval surfaces.

## Allowed use cases

Good uses:
- sensitive internal notes
- reasoning traces the user wants preserved but not broadly exposed
- observations that are meaningful but not yet fit for prompt memory
- long-form internal reflections
- strategy exploration that should not be auto-injected

Bad uses:
- runtime code configuration
- canonical repo policy
- durable shared architecture docs
- default prompt memory facts that should live in `MEMORY.md` or `USER.md`
- general project documentation that belongs in the shared vault or repo docs

## Retrieval rule

If private memory is ever surfaced in runtime, it must follow all of these:
- explicit operator intent
- clear boundary that private content is being consulted
- no automatic inclusion in every session
- no background promotion into shared/public stores without an intentional copy step

## Promotion rule

Material may move from private memory into another layer only by deliberate promotion.

Valid promotion targets:
- `MEMORY.md` or `USER.md` when the content has become a short durable prompt fact
- shared vault when the content becomes useful shared knowledge
- repo docs when the content becomes system policy or implementation guidance
- skills when the content becomes a repeatable workflow

## Non-goal

This policy does not require private memory to become searchable by default. It preserves privacy first and leaves future retrieval integration as an explicit design choice, not an accidental one.

## Related docs

- `docs/shay-memory-hierarchy.md`
- `docs/shay-memory-compaction-policy.md`
- `docs/shay-memory-architecture-review-2026-06-12.md`
