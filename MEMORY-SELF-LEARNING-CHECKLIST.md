---
title: Memory + Self-Learning Rebuild Checklist
status: active
branch: feat/shay-memory-regeneration-fix
worktree: /Users/famtasticfritz/famtastic/.worktrees/shay-memory-regeneration-fix
updated_at: 2026-06-16
owner: Shay-Shay
resume_rule: Start at the first unchecked item in "Current Execution Order", then read the latest entry in "Execution Log" before touching code.
---

# Memory + Self-Learning Rebuild Checklist

Purpose: rebuild Shay's self-learning loop and memory reflection system into a resilient, resumable, adversarially-tested pipeline.

## Current Execution Order
- [x] 1. Baseline the live system and capture exact failure modes.
- [x] 2. Trace all write paths into episodic memory and self-learning artifacts.
- [x] 3. Fix reflection regeneration loop and add retry/health state.
- [x] 4. Separate source classes so daily episodic output stops mixing unlike signals.
- [ ] 5. Diagnose and fix session-memo flood / timestamp integrity issues.
- [ ] 6. Audit self-learning capture coverage: what should be learned, what is currently missed, what should never be promoted.
- [ ] 7. Implement stronger promotion rules from raw/session -> episodic -> semantic -> reflective.
- [x] 8. Add adversarial review harness: break the pipeline on purpose and record failures.
- [x] 9. Harden weak points found in the adversarial pass.
- [ ] 10. Update docs, known gaps, and resumable state.

## Guardrails
- Preserve live main as source of truth; do all changes in this worktree.
- Every meaningful finding gets logged here before or immediately after code changes.
- Prefer append-only diagnostics over silent mutation.
- Keep observation separate from interpretation.
- If interrupted, the next session should be able to resume from this file alone.

## Execution Log
- 2026-06-16: Runtime verification moved to a real repo-ready lane via `uv run --python 3.11`. `pytest` was missing from base deps, so verification now uses the `dev` extra explicitly. Current result: `uv run --python 3.11 --extra dev pytest tests/agent/test_context_compressor.py -q -n 0` => 80 passed.
- 2026-06-16: Adversarial break-tests exposed two real memo-integrity bugs in `agent/context_compressor.py`: (1) compaction-wrapper regex falsely matched the boilerplate phrase "'## Active Task' section" instead of a real markdown heading; fixed by anchoring to `^## Active Task` on its own line. (2) Non-structured compaction residue was still being preserved as `## Compression Handoff Context`; fixed by only persisting handoff bodies that contain real markdown section headers.
- 2026-06-16: Added adversarial regression coverage in `tests/agent/test_context_compressor.py` for compaction wrappers with and without a real active-task section, plus tool-only session-end persistence without an explicit `on_session_start` hook.
- 2026-06-16: Added session lifecycle persistence in `agent/context_compressor.py` so session-end memos are written with `memo_schema: handoff-v2`, `source_class: runtime-session`, redaction enforced, and recent tool activity preserved. Added regression coverage in `tests/agent/test_context_compressor.py` for memo writing + secret redaction.
- 2026-06-16: Hardened `obsidian/Shay-Memory/_system/reflect.py` in the main repo with source-class tagging and runtime health status output at `obsidian/Shay-Memory/_system/runtime/memory-reflect-status.json`. Dry-run reflection now reports real mode instead of always claiming extractive.
- 2026-06-15: Created dedicated worktree and feature branch for self-learning + memory rebuild. Initial scope includes regeneration loop, source separation, memo integrity, health logging, self-learning capture coverage, and adversarial hardening.

## Known Questions To Resolve
- What process is writing or touching the 500+ session memos in one day window?
- Why is nightly reflection staying in extractive fallback instead of generative mode?
- Which artifacts should count as self-learning sources versus operational noise?
- What exact rules should govern promotion into semantic and reflective memory?
