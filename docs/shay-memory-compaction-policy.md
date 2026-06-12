# Shay-Shay memory compaction policy

Status: canonical policy
Last updated: 2026-06-12
Scope: bounded prompt memory only

## Purpose

This policy governs compaction of:
- `~/.shay/memories/MEMORY.md`
- `~/.shay/memories/USER.md`

These files are prompt memory, not archives. They must stay compact enough to remain useful as auto-injected context.

## Why compaction exists

Prompt memory is not a vault. It is a small, high-value layer that should carry only durable facts with repeated future value.

Without compaction, prompt memory drifts toward:
- stale status notes
- duplicated preferences
- one-off project details
- procedural instructions that belong in skills or docs
- bulky notes that should live in the shared vault instead

## Core rules

1. Keep only durable facts with ongoing value.
2. Prefer compact declarative statements over verbose explanations.
3. Remove stale or superseded entries instead of stacking near-duplicates.
4. Move long-form detail to docs, vault notes, or skills rather than expanding prompt memory.
5. Store workflows in skills, not prompt memory.
6. Store session outcomes in transcripts or vault notes, not prompt memory.

## What belongs in bounded prompt memory

Good candidates:
- stable user preferences
- enduring communication preferences
- stable environment facts that save repeated rediscovery
- recurring conventions that repeatedly affect execution
- lasting corrections from the user

Bad candidates:
- task progress
- temporary TODOs
- file counts, branches, SHAs, PR numbers, issue numbers
- long architecture summaries
- one-off debugging details
- long quotes from prior conversations
- speculative notes that are better kept in the private vault or shared notes

## Target shape

Each entry should be one of these:
- one durable fact
- one durable preference
- one durable constraint
- one durable convention

If an entry needs paragraphs to make sense, it probably belongs somewhere else.

## Compaction triggers

Compaction should happen when any of the following becomes true:
- a file approaches its configured character cap
- multiple entries say almost the same thing
- an old entry is no longer correct
- a short list has grown into a bulky explanation
- a newer canonical doc or skill now holds the detailed version

## Compaction method

Use this order:
1. Remove stale entries.
2. Merge duplicate or overlapping entries.
3. Rewrite wordy entries into tighter declarative facts.
4. Move long-form detail into a doc, skill, or vault note.
5. Preserve only the high-value compressed statement in prompt memory.

## Preservation rule

Compaction is not deletion by default. When removing detail that may still matter, preserve it in the right home first:
- docs for repo/system policy
- skills for repeatable procedures
- shared vault for structured long-form knowledge
- private vault for sensitive/internal notes
- session history for execution logs and ephemeral work

## Recommended operating thresholds

This policy does not change runtime config, but it defines operator intent:
- under 70 percent of cap: healthy
- 70 to 85 percent: review for duplication
- 85 to 95 percent: compact soon
- over 95 percent: compact before adding much new material

## Decision rule for new memory writes

Before saving to prompt memory, ask:
1. Will this still matter in a week or a month?
2. Will not saving it cause repeated user steering later?
3. Is this short enough to earn always-on prompt space?
4. Does it belong in memory rather than in a skill, transcript, or vault doc?

If the answer to any of those is no, do not put it in bounded prompt memory.

## Related docs

- `docs/shay-memory-hierarchy.md`
- `docs/shay-private-memory-policy.md`
- `docs/shay-memory-architecture-review-2026-06-12.md`
