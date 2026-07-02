# Intelligence Autonomy HyperSwarm Plan — 2026-07-02

## Goal
Move Shay's intelligence layer from proposal-only loop closure to bounded self-improvement with generative reflection, governed pointer/capability promotion, and permissioned ambient context — without allowing unsafe silent mutation of identity, authority, secrets, payments, or destructive runtime state.

## Done condition
The run is complete when all four honest limits are addressed in working code, tests, docs, and proof artifacts:

1. Generative reflection exists behind config and can produce schema-valid L2/L3 candidates from compact evidence packets.
2. Pointer promotion exists with risk classification and can auto-promote low-risk dereferenceable pointers while routing medium/high-risk items to review.
3. Capability reconciliation exists with staged patch/proposal output and governance gates; it does not silently mutate `intelligence_seed.py` unless explicitly configured for a low-risk class.
4. Ambient context has at least read-only local/process/session connectors and a permissioned connector interface for future calendar/message/screen sources.
5. Telemetry is captured for every worker/process lane: lane id, task, model/provider, start/end time, duration, files touched, verification result, and promotion decision.
6. `main` remains shippable: focused tests pass, docs/changelog/state surfaces are updated where required, and the implementation is pushed only after parent verification.

## Branch / worktree
- Repo: `/Users/famtasticfritz/famtastic/shay-shay`
- Base: `origin/main`
- Work branch: `feature/intelligence-autonomy-hyperswarm`
- Do not touch unrelated untracked file: `docs/plans/qa-skill-map.md`

## Truth surfaces
- `agent/intelligence_loop.py`
- `agent/intelligence_prefetch.py`
- `run_agent.py`
- `shay_cli/intelligence_seed.py`
- `tests/agent/test_intelligence_loop.py`
- `tests/agent/test_intelligence_prefetch.py`
- `tests/test_intelligence_layer.py`
- Generated runtime artifacts under `~/.shay/runtime/` and `/Users/famtasticfritz/famtastic/obsidian/Shay-Memory/reflections/`
- Docs: `/Users/famtasticfritz/famtastic/SITE-LEARNINGS.md`, `/Users/famtasticfritz/famtastic/CHANGELOG.md`, `/Users/famtasticfritz/famtastic/FAMTASTIC-STATE.md` if structure changes

## Execution
Mode: HyperSwarm, dependency-gated, cost-effective, multi-process where safe.

Captain policy:
- Shay/captain owns decomposition, final verification, merge/push, and truth claims.
- Workers handle narrow implementation, test, docs, and review lanes.
- Cheap/default lanes handle rote code/test/doc work.
- Premium/captain lane handles final synthesis, adversarial review interpretation, and risky governance decisions.
- Parent verifies all worker claims against files/tests before reporting done.

## Adversarial plan-review loop
Before implementation, run this plan through adversarial review until either:
- no issues above lowest severity remain, or
- 25 iterations are reached.

Severity scale:
- blocker
- high
- medium
- low
- nit

Pass threshold:
- blocker/high/medium/low must be addressed.
- nits may remain if explicitly accepted.

Review must check:
- unsafe self-rewrite risk
- overclaiming generative intelligence
- missing telemetry
- missing tests
- missing rollback/governance
- cost/routing weakness
- dependency mistakes
- ambient privacy risk
- docs/changelog obligations

## Review loop telemetry so far

Iteration 1 external child-review attempt failed quality: two `gemma4:latest` delegate lanes returned `please provide the plan` despite receiving the plan path/content. This is recorded as reviewer-lane negative evidence, not plan approval. Captain re-review identified these addressable issues:
- medium: exact config keys/schema were underdefined.
- medium: rollback and disabling behavior were underdefined.
- medium: exact verification commands were underdefined.
- low: concurrency/budget caps were underdefined.
- low: telemetry storage path was defined, but not the required run manifest schema.

The plan below incorporates those fixes. Remaining nits may be accepted after rerun if no blocker/high/medium/low remain.

## Config schema / runtime gates

New config keys must be additive and disabled-safe:

```yaml
intelligence_loop:
  generative_reflection:
    enabled: false
    provider: null
    model: null
    max_source_chars: 12000
    max_candidates: 25
    timeout_seconds: 60
    allow_paid: false
  pointer_promotion:
    enabled: true
    auto_promote_low_risk: true
    review_queue_path: ~/.shay/runtime/review_queue/intelligence-promotions.jsonl
    min_confidence: 0.85
    min_independent_sources: 2
  capability_reconciliation:
    enabled: true
    auto_mutation_enabled: false
    proposal_path: ~/.shay/runtime/review_queue/capability-proposals.jsonl
  ambient_context:
    enabled: true
    default_ttl_seconds: 3600
    persist_private_sources: false
    connectors:
      local_artifacts: true
      process_snapshot: true
      session_recent: true
      calendar: false
      messages: false
      screen: false
  swarm_telemetry:
    enabled: true
    base_dir: ~/.shay/runtime/swarm-runs
    capture_tokens_if_available: true
```

Rollback behavior:
- Setting `generative_reflection.enabled=false` must return to deterministic reflection with no exception.
- Setting `pointer_promotion.auto_promote_low_risk=false` must route all candidates to review queue only.
- Setting `capability_reconciliation.auto_mutation_enabled=false` must be the default and must prevent direct writes to `intelligence_seed.py`.
- Setting `ambient_context.enabled=false` must disable all ambient connectors.

## Telemetry manifest schema

Each run writes:
- `~/.shay/runtime/swarm-runs/<run_id>/run.json`
- `~/.shay/runtime/swarm-runs/<run_id>/lanes.jsonl`
- `~/.shay/runtime/swarm-runs/<run_id>/review.jsonl`
- `~/.shay/runtime/swarm-runs/<run_id>/summary.md`

Lane row schema:
```json
{
  "run_id": "string",
  "lane_id": "string",
  "role": "captain|worker|reviewer|verifier|docs",
  "task": "string",
  "intended_model": "string|null",
  "actual_model": "string|null",
  "provider": "string|null",
  "budget_class": "free|cheap|shared_subscription|premium_explicit|not_logged",
  "toolsets": ["string"],
  "start_time": "iso8601",
  "end_time": "iso8601",
  "duration_seconds": 0.0,
  "status": "completed|blocked|failed|quality_failed|skipped",
  "files_changed": ["string"],
  "verification_command": "string|null",
  "verification_result": "string|null",
  "artifact_paths": ["string"],
  "tokens": {"input": "number|null", "output": "number|null"},
  "notes": "string"
}
```

Concurrency / budget policy:
- Default live child/process cap: 4 concurrent implementation lanes unless the local runtime exposes a higher safe cap.
- Paid model use is forbidden for worker fan-out unless `allow_paid=true` is explicitly configured.
- Premium/captain lanes are reserved for review/synthesis, not broad labor.
- If actual model/provider cannot be proven, record `actual_model=null` and note `not independently logged`.

Exact verification commands before merge:
```bash
python -m pytest tests/agent/test_intelligence_loop.py tests/agent/test_intelligence_prefetch.py tests/test_intelligence_layer.py -q
python -m pytest tests/agent/test_memory_provider.py tests/run_agent/test_memory_sync_interrupted.py -q
python -m compileall agent shay_cli run_agent.py
```

Live artifact proof command must be added or reused during implementation and recorded in telemetry.

## Swarm lanes after review passes

### Lane A — Generative reflection implementation
Task: Add config-gated generative reflection substrate.
Deliverables:
- `agent/generative_reflection.py` or equivalent integrated module
- schema-bound candidate output
- deterministic fallback when provider unavailable
- tests for enabled, disabled, malformed output, unavailable provider

### Lane B — Pointer promotion governance
Task: Add risk-classified pointer promotion.
Deliverables:
- promotion policy loader
- low-risk auto-promote path for dereferenceable operational pointers
- medium/high-risk review queue JSONL
- tests for auto/review/reject cases

### Lane C — Capability reconciliation governance
Task: Add staged capability proposal/patch generation.
Deliverables:
- proposal queue or staged patch artifact
- no silent mutation of `intelligence_seed.py` by default
- tests for proposal generation and forbidden silent mutation

### Lane D — Ambient context interface
Task: Add read-only ambient context connector interface and safe local connectors.
Deliverables:
- connector protocol/base class
- local process/session/artifact connectors
- TTL/source/confidence metadata
- tests for disabled connector, TTL expiry, no-persist behavior

### Lane E — Telemetry and run ledger
Task: Add swarm/run telemetry capture for this implementation pass.
Deliverables:
- ledger artifact path under `~/.shay/runtime/swarm-runs/`
- per-lane timing/model/provider/task/result rows
- summary reducer
- tests or proof script

### Lane F — Integration and CLI/runtime wiring
Task: Wire new pieces into existing intelligence loop/prefetch surfaces.
Deliverables:
- config keys documented
- generated artifacts consumed by prefetch where appropriate
- no startup breakage
- focused tests pass

### Lane G — Docs, changelog, and state surfaces
Task: Update required documentation after code truth is verified.
Deliverables:
- `SITE-LEARNINGS.md` update
- `CHANGELOG.md` entry
- regenerate `FAMTASTIC-STATE.md` if structure/data flow changed

### Lane H — Adversarial implementation review
Task: Separate review of final diff and proof.
Deliverables:
- review report with severity labels
- all blocker/high/medium/low addressed or explicit accepted-risk note

## Parallelism
Dependency gates:
1. Plan review must pass before code fan-out.
2. Lanes A/B/C/D/E can run in parallel after review.
3. Lane F waits on A/B/C/D/E outputs.
4. Lane G waits on final code truth.
5. Lane H runs after integration/proof, then captain patches any remaining issues.

Parallel process strategy:
- Use separate subprocess lanes where implementation can be isolated by file/domain.
- Use parent/captain for final reconciliation to avoid branch collisions.
- If child-lane quality is weak, mark telemetry honestly and recover captain-direct only for bounded patches.

## Telemetry requirements
For every lane/process:
- run_id
- lane_id
- role
- task
- intended_model
- actual_model if available
- provider if available
- budget_class
- toolsets
- start_time
- end_time
- duration_seconds
- status
- files_changed
- verification_command
- verification_result
- artifact_paths
- notes

If token/cost data is unavailable, record `not_logged`, not estimates.

## Proof
Required proof before merge/push:
- focused pytest suite passes
- intelligence loop live run produces artifacts
- telemetry ledger exists and contains lane rows
- git diff inspected by captain
- docs updated if behavior changed
- `origin/main` matches final pushed HEAD after push

## Blockers / intervention thresholds
Stop only for:
- missing credentials/API keys for configured generative lane
- destructive action request
- permission boundary for private ambient sources
- paid spend outside configured budget
- merge conflict needing owner decision
- repeated review loop failure after 25 iterations

## Initial status
Status: plan drafted, pending adversarial review loop.
Started: 2026-07-02T11:44:38-0400
Ended: null
