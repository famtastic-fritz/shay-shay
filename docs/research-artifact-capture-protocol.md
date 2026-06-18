# Research artifact capture protocol

Status: active
Date: 2026-06-18

Purpose:
Stop meaningful research from evaporating as terminal output or chat residue. Every meaningful research pass should leave a durable artifact that future Shay can reopen, query, and reuse.

## Core rule

Treat research as data.
That includes research that is not immediately useful today.
Future utility is enough reason to capture it.

This especially applies to:
- GitHub/repo scans
- model capability audits
- provider/runtime comparisons
- architecture comparisons
- jailbreak/limitation research
- market or vendor scans
- any investigation Fritz explicitly wants remembered

## Closed-loop rule

Before meaningful new research starts, run a preflight against prior research.
The minimum preflight checks are:
1. research registry / ledger
2. research note scan
3. session recall surface
4. verdict: `already researched` / `partially researched` / `new topic`

Use:
- `scripts/research_preflight.py`

If the verdict is not `new topic`, review the strongest prior artifact first and only do net-new research on the missing delta.

## Minimum artifact contract

Every durable research artifact must contain:
1. Summary
2. Research question
3. Reuse status
4. Observations
5. Interpretations
6. Capability notes
7. Source ledger
8. Next actions
9. Resume sentence

Minimum reuse-status fields:
- freshness
- verdict
- related topics

## Observation vs interpretation

Observation = direct evidence.
Examples:
- `ollama list` returned `qwen3:14b`, `gemma4:latest`, and `wizardlm-uncensored:latest`.
- `shay -z --provider ollama -m dolphin-mistral:latest` returned empty stdout with exit code 0.
- A repo's last visible commit was dated 2023-11-16.

Interpretation = meaning inferred from those facts.
Examples:
- The model is likely unsafe for protected main-lane use.
- The issue looks like a Shay integration gap, not just weak model quality.
- The repo is stale enough to classify as reference-only unless a unique capability justifies adoption.

Never merge these two sections.

## Default artifact location

Primary notes:
- `~/famtastic/obsidian/Shay-Memory/research/`

Append-only artifact ledger:
- `~/famtastic/obsidian/Shay-Memory/research/_ledger/research-artifacts.jsonl`

Append-only registry / fast lookup index:
- `~/famtastic/obsidian/Shay-Memory/research/_ledger/research-registry.jsonl`

The helpers use those defaults through `$HOME`, but paths can be overridden with:
- `SHAY_RESEARCH_ROOT`
- `SHAY_RESEARCH_LEDGER`
- `SHAY_RESEARCH_REGISTRY`
- `SHAY_STATE_DB`

## Fast helpers

Use:
- `scripts/research_capture.py`
- `scripts/research_preflight.py`

Capture writes:
- one markdown note under the research folder
- one JSONL record in the append-only artifact ledger
- one compact JSONL record in the append-only registry

Preflight reads:
- registry first
- artifact ledger as fallback
- markdown research notes as backup surface
- `state.db` for transcript/session hits when available

## Expected usage pattern

1. Run research preflight.
2. Review strongest prior artifact if one exists.
3. Do only the missing research.
4. Capture the durable artifact before finalizing.
5. In the final response, point to the artifact path and say whether the result extended prior work or created a new topic.
6. If the research changed a stable workflow, patch or create a skill too.

## GitHub research capture requirements

Capture all of the following:
- repo URL
- what the repo concretely does
- maintenance/activity signal
- install/adoption status
- adoption verdict: adopt / evaluate / reference-only / skip
- why it matters to Fritz

## Model and runtime research capture requirements

Capture all of the following:
- installed vs not installed
- live protected lane at time of audit
- exact source of truth used (`ollama list`, config file, harness, direct API check)
- worker/fallback fit
- round-trip gaps between direct model behavior and Shay behavior

## Scope guard

This protocol does not mean every tiny lookup gets a note.
It does mean every meaningful research pass does.

## Why this exists

Fritz's standard is not just "answer the current question."
It is "build a system that learns from every useful pass and can reuse it later."
If research is not captured, Shay cannot compound.
If research is not checked before a new pass, Shay still wastes motion.
