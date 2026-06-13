# Shay-Shay SITE-LEARNINGS

## 2026-06-13 — Life OS Phases 2-5 landed for process intelligence, watchers, pattern scanning, and capability routing

The process-intelligence runtime in `process_intelligence.py` now carries Phase 2 ledger authority instead of a run/tool-only skeleton. The SQLite schema includes `run_ledger`, `tool_activity_ledger`, `artifact_ledger`, `validation_ledger`, `decision_ledger`, and `tracker_transition_ledger`, with new write surfaces `record_decision()` and `record_tracker_transition()` plus query helpers `get_related_artifacts()` and `get_item_blockers()`. `ProcessIntelligenceRecorder.finish_run()` now records interruption and guardrail outcomes as machine-written decisions, so decision lineage is durable instead of implied.

Tracker authority now lives in `process_tracker.py`. `ProcessTracker.transition_item()` enforces explicit state transitions, requires evidence for `live_wired` / `validated_live`, writes transition history back into the YAML tracker, and mirrors each transition into `tracker_transition_ledger` when a DB handle is present. This is the current proof boundary between design/sandbox/PR/live claims and durable evidence-backed status.

Phase 3 landed as `life_os_watchers.py`, a read-only watcher control plane that inspects live local state without mutating launchd, cron, tracker data, or asks. The first watcher set covers scheduler inventory (`cron/jobs.json`), daily-brief ask-storm signals (`events.jsonl` + asks directory), reflection freshness (`Shay-Memory/reflections/episodic`), lessons-sync freshness (`Shay-Memory/lessons-mirror`), and external-intelligence freshness. Cooldown/dedupe state lives under `get_shay_home() / "watcher-state"`, and every emitted observation writes a JSON review packet under `watcher-state/review-packets/`.

Phase 4 landed as `life_os_pattern_scanner.py`. The first scanner classes are `state-overclaim`, `stale-gap`, `ask-storm-pattern`, and `missing-lineage`; they consume tracker YAML, watcher review packets, and the process-intelligence SQLite ledger, then emit review packets only under `watcher-state/pattern-packets/`. Scanner rules currently enforced: no direct action, fingerprint+cooldown suppression, and exact evidence-path citation in emitted findings.

Phase 5 landed as `life_os_plane.py`. It introduces open-ended domain registry records (`DomainRecord`), evidence-backed capability claims (`CapabilityClaim`), a capability-matrix query surface, and a Fritz-specific attention router that scores candidates using revenue potential, automation potential, mental-load reduction, urgency, blockers cleared, stream priority, overload, and energy. This is intentionally open-ended: domains are not hard-coded to a frozen list, and capability claims remain evidence-backed instead of asserted by prose.

Verification lives in `tests/test_process_intelligence.py`, `tests/test_life_os_watchers.py`, `tests/test_life_os_pattern_scanner.py`, and `tests/test_life_os_plane.py`. Current green command: `uv run --python 3.11 python -m unittest tests.test_process_intelligence tests.test_life_os_watchers tests.test_life_os_pattern_scanner tests.test_life_os_plane`.

## Known gaps

- The watcher and pattern-scanner control planes exist as local modules and tests, but they are not yet wired into a recurring launchd/cron surface.
- `life_os_watchers.py` currently inspects file/state surfaces only; it does not yet read live `launchctl` state or running process tables.
- The pattern scanner emits review packets but does not yet back-write findings into `decision_ledger` or a first-class observation ledger.
- `life_os_plane.py` is a local registry/query surface; it is not yet fed automatically from watcher/scanner outputs or exposed through a CLI/API.
- Redaction validation for watcher/scanner packet content is still trust-by-construction; there is no dedicated secret-leak regression suite yet.
