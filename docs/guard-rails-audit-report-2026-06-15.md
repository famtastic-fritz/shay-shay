# Guard-Rails Audit Report

Date: 2026-06-15
Repo assessed: `/Users/famtasticfritz/famtastic/shay-shay`
Audit window: last 4 days of commit activity from mainline plus directly related Shay worktrees/branches used to stage the same feature family

## Executive verdict

Yes — your suspicion is real.

The last 4 days added a large policy-and-control layer that does more than make Shay proactive. It hard-codes a supervisory worldview into the runtime: blocked routes, unsafe statuses, approval requirements, forbidden-action lists, policy-driven provider avoidance, and a gated-only swarm posture.

Short version:
- Good intent was present: capability visibility, routing, ledgers, resumable work, and a proactive command surface.
- The implementation drifted into overcoding: a lot of static policy was baked directly into code and tests before the orchestration layer had a chance to prove itself in the wild.
- The specific `gated` behavior you called out is real and is not just docs talk. It is wired into the CLI/runtime surface right now.

I cannot prove “this came from ChatGPT Web” from git metadata alone. What I can do is rank the commits by style, content, blast radius, and how strongly they match the guardrail-heavy posture you described.

## Scope and method

I assessed:
- canonical live repo: `/Users/famtasticfritz/famtastic/shay-shay`
- related Shay worktrees/sandboxes to trace the same feature lineage

Method:
1. reviewed mainline commits from the last 4 days
2. inspected diffs, file churn, and added policy language
3. searched current runtime code for `gated`, `unsafe`, `blocked`, `approval`, `avoid_by_policy`, `forbidden`, `review gate`, and `stop/resume`
4. verified the current CLI output with the repo venv

Mainline commit totals in the audit window:
- 6 commits on first-parent main
- 7,260 insertions
- 51 deletions

Most of the new behavior is concentrated in 4 commits:
- `78043aa` — 3,500 insertions
- `b30a8f5` — 1,478 insertions
- `fde1f73` — 1,432 insertions
- `bde9b62` — 19 insertions

Those 4 commits alone account for 6,429 insertions.

## The commits most likely tied to the guardrail posture

### Tier 1 — highest-confidence guardrail/overcoding commits

#### 1) `78043aa` — `feat: add intelligence layer command surface`
Date: 2026-06-15 06:58:34 -0400
Confidence: VERY HIGH

Why it stands out:
- massive blast radius: 3,500 inserted lines across 5 files
- introduces the runtime command surface where the current `gated` behavior lives
- hard-codes safety gates, forbidden actions, blocked production routes, and approval requirements
- this is the strongest direct match to the behavior you described

Key evidence:
- `shay_cli/intelligence_cmd.py:80-96`
  - defines `SAFETY_GATES` including:
    - `no live runtime edits`
    - `no production HyperSwarm launch without explicit approval`
    - `no Gmail send`
    - `no Calendar write`
    - `no publish action`
    - `no uncontrolled provider spend`
- `shay_cli/intelligence_cmd.py:881-890`
  - returns:
    - `"hyperswarm": "gated"`
    - `"production_launch_safe": false`
    - `"requires_fritz_approval_for_production": true`
- `shay_cli/intelligence_cmd.py:1053-1067`
  - routes “launch HyperSwarm” to:
    - `decision = blocked_for_production`
    - `unsafe = true`
    - `requires_fritz_approval = true`
    - missing item: `production HyperSwarm remains gated unless Fritz explicitly approves it later`
- `shay_cli/intelligence_seed.py:813-827`
  - defines `COMMON_FORBIDDEN_ACTIONS`:
    - `dirty-main writes`
    - `persona/root-truth edits`
    - `live runtime edits`
    - `production HyperSwarm launch`
    - `external repo execution`
    - `Gmail send`
    - `Calendar write`
    - `publish action`
    - `uncontrolled provider spend`
- `shay_cli/intelligence_seed.py:864-882`
  - the `work-router` is explicitly described as routing through `policy` and able to `block unsafe routes`

Effect on proactivity:
- this commit creates the proactive shell, but then neuters it by defaulting key paths into policy-controlled blocks
- it is the cleanest example of “turned responsive into supervised”

#### 2) `b30a8f5` — `feat: add capability truth layer CLI`
Date: 2026-06-14 22:55:49 -0400
Confidence: VERY HIGH

Why it stands out:
- creates a static capability status matrix with policy labels like `unsafe`, `blocked`, `avoid_by_policy`, and `requires_review`
- turns capability reporting into a normative control surface instead of an observational one
- this is where a lot of the worldview gets fossilized

Key evidence:
- `shay_cli/capabilities_cmd.py:72-76`
  - `HYPERSWARM_BLOCKERS` are hard-coded with language about gating, review gates, redaction, output contracts, and stop/resume fields
- `shay_cli/capabilities_cmd.py:654-674`
  - if HyperSwarm-related skills exist, status is still forced to `unsafe`
  - summary becomes `runtime launch remains intentionally blocked`
- `shay_cli/capabilities_cmd.py:722-724`
  - capability registry override forces:
    - `status = unsafe`
    - `summary = HyperSwarm doctrine is present; production launch remains gated and unsafe without explicit approval`
- `shay_cli/intelligence_seed.py:136-178`
  - `gmail-send` and `calendar-read-write` are pre-labeled `blocked`
  - both are framed as explicitly forbidden in-task, with draft-only or read-only fallback posture
- `shay_cli/intelligence_seed.py:497-517`
  - `hyperswarm-doctrine` is marked `unsafe`
  - `safe_to_use = false`
  - `live = false`
  - next action literally says: `keep production launch gated; use dry-run to prove safety behavior`

Effect on proactivity:
- instead of “what is available and what is the cheapest good lane?”, the layer becomes “what is pre-disallowed by baked policy?”
- that is a different product philosophy

#### 3) `bde9b62` — `fix: surface capability status in routing output`
Date: 2026-06-15 07:05:01 -0400
Confidence: HIGH as follow-up cementing commit

Why it stands out:
- tiny commit, but it strengthens the visibility of the policy labels in route output
- this is not where the guardrails were invented, but it makes them more front-and-center

Effect on proactivity:
- hardens the guardrail posture in the user-facing command results

### Tier 2 — strong supporting commits that enabled or normalized the posture

#### 4) `fde1f73` — `feat: add process intelligence ledger MVP [docs] (#5)`
Date: 2026-06-14 01:07:24 -0400
Confidence: MEDIUM-HIGH

Why it matters:
- this one is not the main blocker, but it adds the machinery that records decisions, assumptions, gaps, validations, safety events, and blockers as first-class run artifacts
- useful in principle, but it can drift from “observe reality” into “encode policy into reality” when paired with the intelligence layer

Key evidence:
- `agent/process_intelligence.py:20-50`
  - required ledger fields include:
    - `decisions_made`
    - `assumptions_made`
    - `gaps_opened`
    - `gaps_closed`
    - `validation_results`
    - `safety_events`
    - `blockers`
- current generated run artifacts under `~/.shay/process-intelligence/` already record the swarm posture as:
  - `unsafe`
  - `production ... remains gated`
  - `review_gate_enforced = true`

Effect on proactivity:
- good as telemetry
- bad if the telemetry is being filled by static policy assumptions rather than live evidence

#### 5) `5c3cbb2` — `docs: add Shay workstream control map`
Date: 2026-06-13 01:56:41 -0400
Confidence: MEDIUM

Why it matters:
- this appears to be the planning/doctrine seed where the control-heavy posture starts becoming explicit
- it reads like a pre-code command packet for highly constrained execution lanes

Effect on proactivity:
- not runtime by itself
- but it likely fed the later code shape

## Non-mainline precursor commits that look like the same authoring wave

These are not the core runtime commits on `main`, but they look like the same policy-heavy wave and likely informed the merged code.

### Strong precursor cluster
- `4740e9f` — `docs: add Shay control packet and implementation map`
- `f79a342` — `docs: add clean Hermes removal control packet (#4)`
- `95eedb6` — `docs: normalize Title 6 truth surfaces`
- `7ea3d9d` — `docs: add capability gap lifecycle and research watcher design`

Why they matter:
- huge doc volume
- repeated language about:
  - approval-gated work
  - forbidden actions
  - redaction policy
  - review gates
  - control packets
  - gap lifecycle policy
  - runtime truth surfaces
- the later runtime code uses the same vocabulary almost verbatim

This is the closest thing to a knowledge base of “likely came from him” that the repo can support: these docs look like the conceptual staging area, and `b30a8f5` + `78043aa` look like the code realization.

## Runtime verification — the behavior is live, not theoretical

Using the repo venv, I verified the current CLI outputs.

### `capabilities show hyperswarm-doctrine`
Current output says:
- `hyperswarm-doctrine [unsafe]`
- `production launch remains gated and unsafe without explicit approval`

### `intelligence swarm`
Current output says:
- `"hyperswarm": "gated"`
- `"production_launch_safe": false`
- `"requires_fritz_approval_for_production": true`
- and prints the full forbidden/safety list

### `intelligence route 'launch HyperSwarm'`
Current output says:
- `decision: blocked_for_production`
- `unsafe: true`
- `requires Fritz approval: true`

### `intelligence route 'use OpenRouter by default'`
Current output says:
- `decision: avoid_by_policy`
- `unsafe: true`
- `requires Fritz approval: true`

That last one is important: this is not just about swarm launch safety. The code also bakes in provider-policy behavior that can suppress autonomy even when the route is technically available.

## What looks overcoded

### 1) Static policy is pretending to be runtime truth
The capability matrix and routing layer do not only report what exists. They pre-judge what is allowed, safe, blocked, or to be avoided.

That means the system is no longer just introspecting reality. It is enforcing a worldview.

### 2) The command surface is too big for the maturity of the underlying system
`78043aa` adds 3,500 lines at once. The result is a large orchestration shell with a lot of concepts:
- missions
- plans
- workers
- gaps
- events
- review gates
- forbidden actions
- safety gates
- dry-runs
- cadence scans
- provider policy

That is a lot of framework before proving a minimal proactive loop.

### 3) Tests now lock the guardrails in place
Examples:
- `tests/test_intelligence_layer.py:151-156`
  - asserts HyperSwarm production launch is blocked and requires approval
- `tests/test_intelligence_layer.py:227-230`
  - asserts specific safety gates exist
- `tests/test_intelligence_layer.py:286-290`
  - asserts Anthropic/OpenRouter default paths are `avoid_by_policy`
- `tests/test_capabilities_cmd.py:182-186`
  - asserts HyperSwarm launch is unsafe and warns not to launch it

Once tests codify the posture, the policy stops being a suggestion and becomes part of the product contract.

### 4) The system is biased toward “report and gate” over “route and execute”
The current layer is very good at:
- classifying
- labeling
- warning
- generating gaps
- drafting safe dry-runs
- requiring review

It is weaker at the thing you actually wanted:
- proactively choosing lanes and driving work forward with minimal friction

## What looks worth keeping

Not all of this should be thrown away.

Keep or salvage:
- process-intelligence ledgers as observational telemetry
- capability inventory as a diagnostic/reporting tool
- provider/tool visibility
- resumable worker metadata
- dry-run simulation capability for swarm experiments

These are useful if downgraded from hard policy engine to support instrumentation.

## What most likely needs pruning or demotion

Highest-priority candidates:
1. `shay_cli/intelligence_cmd.py`
   - especially swarm gating, route blocking, hard safety-gate lists, and approval-required defaults
2. `shay_cli/intelligence_seed.py`
   - especially `COMMON_FORBIDDEN_ACTIONS`, capability records pre-labeled `blocked` / `unsafe` / `avoid_by_policy`, and policy-first agent registry definitions
3. `shay_cli/capabilities_cmd.py`
   - especially HyperSwarm blockers and forced unsafe summaries
4. test cases that enforce policy posture rather than technical correctness

## Recommendation

### Recommended immediate direction
Do not nuke everything.

Do this instead:

1. Split observation from enforcement.
   - capability/status layer should report truth
   - enforcement should be narrow and only cover genuinely destructive or expensive actions

2. Demote `blocked`, `unsafe`, and `avoid_by_policy` from default labels to evidence-backed exceptions.
   - use `observed`, `verified`, `unverified`, `experimental`, `costly`, `destructive`, etc.
   - reserve hard blocks for truly dangerous side effects

3. Remove the baked “requires Fritz approval” posture from non-destructive orchestration paths.
   - especially discovery, routing, research, drafting, cheap test lanes, and safe worker launches

4. Keep dry-run support, but stop making dry-run the only identity of the system.
   - Shay should be able to route and act, not just simulate and warn

5. Audit tests and rewrite them around capability truth, not fear posture.
   - test that the route is explicit and explainable
   - do not test that the answer must be “no” unless the task is truly destructive

## Bottom line

If the goal was “turn Shay from responsive into proactive,” then the last 4 days only half-hit the target.

They successfully built a proactive-looking orchestration shell.
But they also injected a heavy compliance/governance layer that makes Shay hesitate, pre-block, and narrate policy.

My direct take:
- yes, this looks overcoded
- yes, the `gated` behavior is real
- yes, `78043aa` and `b30a8f5` are the biggest commits to scrutinize first
- yes, the doc cluster from June 13 looks like the conceptual source for the same posture

## Ranked commit list for follow-up review

### Highest suspicion
1. `78043aa` — intelligence layer command surface
2. `b30a8f5` — capability truth layer CLI
3. `bde9b62` — surface capability status in routing output

### Supporting/precursor wave
4. `fde1f73` — process intelligence ledger MVP
5. `5c3cbb2` — Shay workstream control map
6. `4740e9f` — Shay control packet and implementation map
7. `f79a342` — clean Hermes removal control packet
8. `95eedb6` — Title 6 truth surfaces normalization
9. `7ea3d9d` — capability gap lifecycle and watcher design

### Probably not the problem
10. `6519ada` — model selection/provider resolution stabilization

## File produced by this audit

This report is the audit artifact.
