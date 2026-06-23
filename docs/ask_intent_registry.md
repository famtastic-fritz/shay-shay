# Ask Intent Registry

Canonical ask-to-fire map for the Shay intelligence layer.

Purpose
- Normalize fuzzy asks into a named intent.
- Show which command chain fires first.
- Keep capability preflight, intelligence routing, control-plane explain, and proof surfaces aligned.

Rules
1. The user's natural-language ask is not always the route task. Some asks are rewritten into an internal lane task so the route reflects the actual execution path.
2. Capability preflight happens before a live lane claim.
3. Control-plane explain is the evidence layer for why a route/template/provider was chosen.
4. Closeout is part of the chain, not optional ceremony.
5. Swarm status/readiness are included only when the mapped chain touches HyperSwarm lanes.

## Registry

| Intent | User ask patterns | Internal route task shape | Command chain | Proof surfaces |
| --- | --- | --- | --- | --- |
| `build_app` | `build this app`, `build app`, `ship this app`, `create this app` | `launch HyperSwarm build lane for: {ask}` | `shay capabilities preflight "{route_task}"` → `shay intelligence route "{route_task}"` → `shay intelligence control-plane explain "{explain_task}"` → `shay intelligence swarm status` → `shay intelligence swarm readiness` → `shay intelligence swarm dry-run` → `shay capabilities closeout "{route_task}"` | preflight gate report, route decision, control-plane evidence, swarm ledgers, closeout proof |
| `show_attention` | `what needs my attention`, `needs my attention`, `show blockers`, `what's blocked` | `review attention blockers for: {ask}` | `shay intelligence brief today` → `shay intelligence missions` → `shay intelligence workers review` → `shay intelligence critical` → `shay intelligence truth` | today brief, mission graph, worker review summary, critical output, truth snapshot |
| `github_to_obsidian_ingest` | `github to obsidian`, `ingest github into obsidian`, `sync github to obsidian` | `ingest GitHub to Obsidian for: {ask}` | `shay capabilities preflight "{route_task}"` → `shay intelligence route "{route_task}"` → `shay intelligence control-plane explain "{explain_task}"` → `shay capabilities closeout "{route_task}"` | preflight gate report, route decision with repo/vault lane, explain evidence, closeout proof |
| `context_compression_gap` | `context compression`, `memory continuity`, `compression continuity` | `fix context compression memory continuity for: {ask}` | `shay capabilities preflight "{route_task}"` → `shay intelligence route "{route_task}"` → `shay intelligence brief compression` → `shay capabilities closeout "{route_task}"` | preflight gate report, gap-tracking route decision, compression health brief, closeout proof |
| `run_reviewer_pass` | `run reviewer pass`, `reviewer pass only`, `review this lane`, `review only` | `launch HyperSwarm reviewer lane for: {ask}` | `shay capabilities preflight "{route_task}"` → `shay intelligence route "{route_task}"` → `shay intelligence workers review` → `shay intelligence control-plane explain "{explain_task}"` → `shay capabilities closeout "{route_task}"` | reviewer preflight, reviewer route, worker review summary, explain evidence, closeout proof |
| `resume_lane` | `resume the lane`, `resume last run`, `continue this plan`, `resume this run` | `resume HyperSwarm lane for: {ask}` | `shay intelligence workers queue` → `shay intelligence route "{route_task}"` → `shay intelligence control-plane explain "{explain_task}"` → `shay intelligence brief workers` → `shay capabilities closeout "{route_task}"` | worker queue, resume route, explain evidence, worker brief, closeout proof |
| `generic_orchestration_ask` | fallback when no explicit rule matches | `{ask}` | `shay capabilities preflight "{route_task}"` → `shay intelligence route "{route_task}"` → `shay intelligence control-plane explain "{explain_task}"` → `shay capabilities closeout "{route_task}"` | preflight gate report, route decision, explain evidence, closeout proof |

## Worked examples

### Example: `build this app`
- Intent: `build_app`
- Route task: `launch HyperSwarm build lane for: build this app`
- Explain task: `implement app build lane for: build this app`
- Expected route decision: `route_live`
- Expected swarm state: `working`

### Example: `show me what needs my attention`
- Intent: `show_attention`
- Route task: `review attention blockers for: show me what needs my attention`
- Explain task: `rank blocked work and attention surfaces for: show me what needs my attention`
- Expected first command: `shay intelligence brief today`
- Expected swarm state: not included

### Example: `ingest GitHub into Obsidian for repo history`
- Intent: `github_to_obsidian_ingest`
- Route task: `ingest GitHub to Obsidian for: ingest GitHub into Obsidian for repo history`
- Explain task: `plan GitHub to Obsidian ingest route for: ingest GitHub into Obsidian for repo history`
- Expected first command: `shay capabilities preflight "{route_task}"`
- Expected swarm state: not included

### Example: `fix context compression memory continuity`
- Intent: `context_compression_gap`
- Route task: `fix context compression memory continuity for: fix context compression memory continuity`
- Explain task: `explain context compression continuity gap for: fix context compression memory continuity`
- Expected route decision: `track_gap`
- Expected brief surface: `shay intelligence brief compression`

## Notes
- This registry is implemented in `shay_cli/intelligence_cmd.py` via `ASK_TRACE_RULES` and surfaced through `shay intelligence trace <ask>`.
- The trace command is the CLI proof view. It does not execute the chain; it shows what would fire and why.
- If the command chain changes, update both this file and the rule registry in code in the same change.