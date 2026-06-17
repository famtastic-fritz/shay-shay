# Shay Runtime Truth Audit

Date: 2026-06-13
Status: read-only runtime audit
Lane: runtime-truth
Method: passive CLI inspection only; no config edits, no paid probes, no live mutation

## Commands run

1. `shay --help`
2. `shay status`
3. `shay doctor`
4. `shay mcp`
5. `shay model`
6. `shay fallback list`
7. `shay run-plan --help`
8. `shay model --help`
9. `shay skills search hyperswarm`
10. `shay skills inspect hyperswarm`
11. `shay skills list`

## Observed runtime truth

### A. CLI surface exists and is broad

`shay --help` proves these relevant command surfaces exist right now:
- `model`
- `fallback`
- `gateway`
- `status`
- `doctor`
- `cron`
- `skills`
- `memory`
- `tools`
- `computer-use`
- `mcp`
- `sessions`
- `dashboard`
- `logs`
- `run-plan`

Truth level: observed

### B. Status command points at the live Shay runtime, not this docs worktree

`shay status` reported:
- project: `/Users/famtasticfritz/famtastic/shay-shay`
- python: `3.13.12`
- model: `gpt-5.4`
- provider: `OpenAI Codex`
- gateway service: running via launchd
- scheduled jobs: `0 active, 10 total`
- active sessions: `1`

Important implication:
The CLI status surface is reporting on the live Shay runtime checkout, not the `shay-shay-main-sync-20260613` docs worktree.
That means runtime-truth evidence and branch-truth evidence must stay separated.

Truth level: observed
Risk if ignored: overclaim / branch-runtime confusion

### C. Provider truth is split across auth, keys, and selected runtime

`shay status` and `shay doctor` together showed:
- selected runtime provider/model: `gpt-5.4` via `OpenAI Codex`
- OpenAI Codex auth: logged in
- Anthropic API: connectivity passed
- Z.AI / GLM: connectivity passed
- OpenRouter API: not configured
- many other provider keys absent

This proves:
- selected runtime provider is not the same thing as raw API-key presence
- provider health can be partially observed without active paid validation
- "configured" and "selected" and "healthy" are different truth states

Truth level: observed / passive
Not yet proven: full routing success across all fallback providers

### D. Routing and fallback surfaces are partially proven

`shay fallback list` reported:
- primary: `gpt-5.4` via `openai-codex`
- fallback 1: `deepseek-r1-64k` via `ollama`
- fallback 2: `phi4-mini-64k` via `ollama`

`shay run-plan --help` proved a routing-advisory surface exists for request-to-executor reasoning.

This proves:
- fallback order is explicitly configured
- a routing-policy inspection surface exists

This does NOT yet prove:
- that fallback providers are currently healthy end-to-end
- that run-plan is aligned with every real task class Fritz cares about

Truth level: observed for surface, configured for chain, unproven for end-to-end fallback execution

### E. `shay model` has a real inspection gap in non-interactive mode

`shay model --help` works.
`shay model` in a non-interactive subprocess fails with:
- `Error: 'shay model' requires an interactive terminal.`

This is important runtime truth:
- the model surface exists
- the current CLI does not expose a read-only non-interactive current-model inspection command via `shay model`
- operator truth for current model therefore comes from `shay status`, not `shay model`

Truth level: observed
Gap implication: command-surface asymmetry

### F. MCP inventory is observed at the inventory layer, not yet proven per-server healthy

`shay mcp` reported these enabled servers:
- `obsidian`
- `basic-memory`
- `vault-search`

This proves:
- MCP inventory is visible from CLI
- at least three servers are enabled in config/runtime

This does NOT yet prove:
- each server answers correctly right now
- each server is safe/healthy across all tools

Truth level: observed inventory
Not yet proven: per-server health

### G. Skill truth has two different surfaces that must not be conflated

`shay skills search hyperswarm` searched the hub and did NOT resolve the local `hyperswarm` skill.
`shay skills inspect hyperswarm` followed the hub-inspect path and also did not resolve the local skill.
`shay skills list` proved local runtime availability and showed:
- `hyperswarm` enabled, local
- `hyperstorm` enabled, local
- `hyperparallel-swarm-orchestration` enabled, local
- `shay-shay` enabled, local
- total enabled skills: `176`

This proves a critical rule:
- hub search is not the same thing as local installed-skill truth
- local skill readiness must be checked via local list/inspect surfaces, not hub-only search

Truth level: observed
Gap implication: false-negative risk if the wrong skill surface is used

### H. Tool availability is broad but not uniform

`shay doctor` reported these tools available:
- browser
- clarify
- code_execution
- computer_use
- cronjob
- terminal
- delegation
- file
- image_gen
- memory
- messaging
- session_search
- skills
- todo
- tts
- vision
- video
- web
- kanban (runtime-gated)

Warnings included:
- `browser-cdp` dependency missing
- discord / discord_admin missing token
- feishu_doc / feishu_drive missing system dependency
- homeassistant missing system dependency
- moa missing OPENROUTER_API_KEY
- rl missing TINKER_API_KEY and WANDB_API_KEY
- shay-yuanbao missing system dependency
- spotify missing system dependency

This proves tool truth must be lane-specific and dependency-specific.

Truth level: observed

### I. Memory truth is split between MCP memory and built-in memory provider setup

`shay doctor` warned:
- `Memory Provider: builtin plugin not found run: shay memory setup`

At the same time, `shay mcp` showed `basic-memory` enabled.

This proves:
- external memory surfaces can exist even while the built-in memory provider setup is warning
- memory capability must not be flattened into a single healthy/unhealthy flag

Truth level: observed
Gap implication: memory-surface ambiguity

## High-value conclusions for the capability matrix

1. Runtime truth and branch truth are different surfaces.
   - live runtime points at `/Users/famtasticfritz/famtastic/shay-shay`
   - docs/control work is happening in `/Users/famtasticfritz/famtastic/shay-shay-main-sync-20260613`

2. `configured` does not mean `selected`.
3. `selected` does not mean `healthy across fallbacks`.
4. `enabled MCP` does not mean `proven MCP server`.
5. `hub skill search miss` does not mean `local skill unavailable`.
6. some command surfaces are interactive-only and therefore not equally auditable from non-interactive automation.
7. execution readiness is now a separate gate surface from raw capability inventory.
   - `shay capabilities preflight "<task>"` is where capability truth becomes executable readiness
   - `shay capabilities closeout "<task>"` is where proof requirements become explicit closeout obligations

## Gaps opened or sharpened by this audit

- `runtime-branch-truth-split` — live CLI surfaces report the live Shay checkout, not the docs worktree
- `noninteractive-model-inspection-gap` — `shay model` is interactive-only for current-state inspection
- `hub-skill-search-false-negative-risk` — wrong skill surface can hide real local availability
- `mcp-inventory-not-health-proof` — enabled server list is not the same thing as per-server health proof
- `memory-surface-ambiguity` — built-in memory warning coexists with enabled external-memory MCP

## Safe next moves

1. update the global capability matrix draft with these observed distinctions
2. keep provider health at passive/partial unless explicit active checks are approved
3. record separate command-surface rows for:
   - local skill list truth
   - hub skill search truth
   - interactive model selection truth
   - passive status truth
4. avoid saying "Shay can’t" before checking local skills list, fallback chain, MCP inventory, and advisory routing surface
