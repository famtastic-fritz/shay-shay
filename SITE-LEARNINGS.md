# Shay-Shay SITE-LEARNINGS

## 2026-06-13 — Life OS Phases 2-5 landed for process intelligence, watchers, pattern scanning, and capability routing

The process-intelligence runtime in `process_intelligence.py` now carries Phase 2 ledger authority instead of a run/tool-only skeleton. The SQLite schema includes `run_ledger`, `tool_activity_ledger`, `artifact_ledger`, `validation_ledger`, `decision_ledger`, and `tracker_transition_ledger`, with new write surfaces `record_decision()` and `record_tracker_transition()` plus query helpers `get_related_artifacts()` and `get_item_blockers()`. `ProcessIntelligenceRecorder.finish_run()` now records interruption and guardrail outcomes as machine-written decisions, so decision lineage is durable instead of implied.

Tracker authority now lives in `process_tracker.py`. `ProcessTracker.transition_item()` enforces explicit state transitions, requires evidence for `live_wired` / `validated_live`, writes transition history back into the YAML tracker, and mirrors each transition into `tracker_transition_ledger` when a DB handle is present. This is the current proof boundary between design/sandbox/PR/live claims and durable evidence-backed status.

Phase 3 landed as `life_os_watchers.py`, a read-only watcher control plane that inspects live local state without mutating launchd, cron, tracker data, or asks. The first watcher set covers scheduler inventory (`cron/jobs.json`), daily-brief ask-storm signals (`events.jsonl` + asks directory), reflection freshness (`Shay-Memory/reflections/episodic`), lessons-sync freshness (`Shay-Memory/lessons-mirror`), and external-intelligence freshness. Cooldown/dedupe state lives under `get_shay_home() / "watcher-state"`, and every emitted observation writes a JSON review packet under `watcher-state/review-packets/`.

Phase 4 landed as `life_os_pattern_scanner.py`. The first scanner classes are `state-overclaim`, `stale-gap`, `ask-storm-pattern`, and `missing-lineage`; they consume tracker YAML, watcher review packets, and the process-intelligence SQLite ledger, then emit review packets only under `watcher-state/pattern-packets/`. Scanner rules currently enforced: no direct action, fingerprint+cooldown suppression, and exact evidence-path citation in emitted findings.

Phase 5 landed as `life_os_plane.py`. It introduces open-ended domain registry records (`DomainRecord`), evidence-backed capability claims (`CapabilityClaim`), a capability-matrix query surface, and a Fritz-specific attention router that scores candidates using revenue potential, automation potential, mental-load reduction, urgency, blockers cleared, stream priority, overload, and energy. This is intentionally open-ended: domains are not hard-coded to a frozen list, and capability claims remain evidence-backed instead of asserted by prose.

Verification lives in `tests/test_process_intelligence.py`, `tests/test_life_os_watchers.py`, `tests/test_life_os_pattern_scanner.py`, and `tests/test_life_os_plane.py`. Current green command: `uv run --python 3.11 python -m unittest tests.test_process_intelligence tests.test_life_os_watchers tests.test_life_os_pattern_scanner tests.test_life_os_plane`.

## 2026-06-13 — Title 6 docs/control truth surfaces normalized

The Title 6 branch now has a current-state tracker in `docs/shay-master-open-items-and-completion-tracker-2026-06-13.md` and `docs/shay-master-open-items-and-completion-tracker-2026-06-13.yaml`, with `docs/shay-truth-surface-rubric-2026-06-13.md` defining the required split between working-tree presence, committed-branch truth, and live-runtime proof. `docs/shay-runtime-truth-audit-2026-06-13.md` and `docs/shay-command-surface-map-2026-06-13.md` now anchor passive runtime/CLI observations without upgrading docs-only work into live claims.

The previously referenced awareness/control gaps are now materially more complete in the working tree. Key restored or added artifacts include `docs/shay-awareness-completion-assessment-2026-06-13.md`, `docs/shay-gap-lifecycle-status-2026-06-13.md`, `docs/shay-gap-lifecycle-policy-2026-06-13.md`, `docs/shay-gap-resolution-workflow-2026-06-13.md`, `docs/shay-process-learning-loop-2026-06-13.md`, `docs/shay-process-query-examples-2026-06-13.md`, `docs/shay-process-intelligence-watcher-design-2026-06-13.md`, `docs/shay-pattern-scanner-autonomy-policy-2026-06-13.md`, `docs/shay-worker-role-matrix-2026-06-13.md`, `docs/shay-skills-readiness-matrix-2026-06-13.yaml`, `docs/shay-skills-gap-log-2026-06-13.md`, `docs/shay-adoption-backlog-2026-06-13.md`, and `docs/shay-adoption-backlog-schema-2026-06-13.yaml`.

`docs/shay-hermes-lane-packet-2026-06-13.md` was restored from the stash-backed original as branch-local historical evidence. It was not previously committed to `main`, so canon docs must treat it as restored evidence and provenance, not as merged canon or live-runtime proof. `docs/shay-docs-promotion-manifest-2026-06-13.md`, `docs/shay-capability-awareness-lineage-audit-2026-06-13.md`, `docs/shay-process-intelligence-brutal-qa-report-2026-06-13.md`, `docs/shay-post-merge-follow-on-plan-2026-06-13.md`, and `docs/shay-prune-recommendations-2026-06-13.md` were patched to keep that distinction explicit.

Historical `HyperWAM` naming is now confined to typo/superseded historical notes, quoted source text, or real historical filenames/alias paths such as `docs/hyperwam-effectiveness-assessment-2026-06-13.md` and `skills/orchestration/hyperwam/SKILL.md`. `HyperSwarm` is the canonical name going forward.

## Known gaps

- The watcher and pattern-scanner control planes exist as local modules and tests, but they are not yet wired into a recurring launchd/cron surface.
- `life_os_watchers.py` currently inspects file/state surfaces only; it does not yet read live `launchctl` state or running process tables.
- The pattern scanner emits review packets but does not yet back-write findings into `decision_ledger` or a first-class observation ledger.
- `life_os_plane.py` is a local registry/query surface; it is not yet fed automatically from watcher/scanner outputs or exposed through a CLI/API.
- Redaction validation for watcher/scanner packet content is still trust-by-construction; there is no dedicated secret-leak regression suite yet.
- The Title 6 docs/control cluster is still branch-local and unmerged; many artifacts are present in the working tree but are not yet merged to `main` or wired into the live runtime.
- `docs/shay-hermes-lane-packet-2026-06-13.md` is restored historical evidence, not proof of live wiring or merged canon; any future cleanup that retires it must patch dependent references in the same change.
