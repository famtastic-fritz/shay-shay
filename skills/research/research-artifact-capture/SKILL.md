---
name: research-artifact-capture
description: "Turn every meaningful research pass into a durable artifact with source trace, capability notes, and observation vs interpretation separation."
version: 1.0.0
author: Shay-Shay
license: MIT
platforms: [linux, macos, windows]
metadata:
  shay:
    tags: [research, capture, memory, obsidian, learning-loop, github, observations, interpretation]
    related_skills: [shay-shay, autonomous-ai-agents, research-paper-writing]
---

# Research artifact capture

Use this skill whenever a session includes meaningful research: GitHub repo scans, model audits, capability comparisons, market scans, architecture comparisons, jailbreak/limitation research, or any exploration that could matter later even if it is not useful today.

Core doctrine:
- Research is data, not disposable chat residue.
- Every meaningful research run must leave a durable artifact on disk.
- Observation and interpretation must be separated.
- Capability notes belong in the artifact so future Shay can recall what tools/models/lanes were available at the time.

## Required outputs

For each meaningful research pass, capture:
1. Summary
2. Research question
3. Observations
4. Interpretations
5. Capability notes
6. Source ledger
7. Next actions
8. Resume sentence

## Observation vs interpretation rule

Observation = what was directly seen or verified.
- example: "`ollama list` showed `qwen3:14b`, `gemma4:latest`, and `wizardlm-uncensored:latest` installed."
- example: "Repo X has not shipped a commit since 2023-11-16."

Interpretation = what it likely means.
- example: "The repo is probably too stale to adopt without a strong reason."
- example: "This model looks fit for worker-only use, not the protected main brain lane."

Never blur these sections together.

## Default artifact location

Primary notes:
- `~/famtastic/obsidian/Shay-Memory/research/`

Append-only ledger:
- `~/famtastic/obsidian/Shay-Memory/research/_ledger/research-artifacts.jsonl`

## Fast path helper

Use the helper script added in this repo:

```bash
python3 scripts/research_capture.py \
  --title "Local model lane audit" \
  --summary "Compared installed Ollama lanes against the live hosted default." \
  --question "Which installed local models are reliable enough for worker or fallback use?" \
  --observation "`ollama list` showed qwen3:14b, gemma4:latest, phi4-mini-64k:latest, and others installed." \
  --observation "Safe hosted `shay -z` prompts passed on the protected default lane." \
  --interpretation "qwen3/hermes3/phi4-mini are stronger practical worker candidates than older uncensored finetunes." \
  --capability "Live runtime remained openai-codex/gpt-5.4 with service_tier=fast and reasoning_effort=low." \
  --source "ollama list|local shell command|command|live installed model inventory" \
  --source "~/.shay/config.yaml|local file|config|runtime mode and default lane" \
  --next-action "Run focused round-trip evals for top fallback candidates." \
  --resume-sentence "Open the local model lane audit note and continue from the observations and next actions."
```

The helper writes both the markdown artifact and a JSONL ledger entry.
It also stamps retrieval-friendly frontmatter (`permalink`, `tags`, `artifact_type`) so the note is easier to find later through vault search or basic-memory tooling.

## When the work is small

If the research was tiny and truly throwaway, you can skip the artifact.
Do not skip it for:
- GitHub/repo research
- model capability audits
- limitation/jailbreak research
- anything Fritz explicitly wants remembered
- anything that produced a reusable lesson or future option

## For GitHub research specifically

Always capture:
- repo URL
- repo status/activity signal
- exact capability or technique it offers
- why it matters or does not matter to Fritz now
- adoption verdict: adopt / evaluate / reference-only / skip

## For model/capability research specifically

Always capture:
- installed vs not installed
- source of truth used (`ollama list`, config file, live harness, provider docs)
- protected main lane at the time of research
- worker/fallback fit
- gaps between direct model behavior and Shay round-trip behavior

## Completion rule

Research is not complete until the durable artifact exists and the final answer points to it.
