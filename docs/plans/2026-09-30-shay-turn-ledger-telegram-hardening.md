# Shay Turn Ledger + Telegram Hardening

## Title
Shay Turn Ledger + Telegram Hardening

## Purpose
Create one clean-room, provider-aware operational spine for Shay turns and repair the highest-confidence Telegram reliability gaps without importing code, binaries, credentials, or runtime authority from the reconstructed external reference.

## Goal
A Shay turn is durably observable, redacted, recoverable, and consistently projected across CLI, TUI, gateway, dashboard, ACP, and cron. Telegram delivery and polling failures are surfaced as structured state and tested through the real gateway contract without changing the approval authority or creating a second runtime.

## Tasks
- [ ] Freeze provenance and behavioral evidence for the external reference; maintain a clean-room audit that rejects copied code, artifact paths, credential harvesting, desktop updater/recovery machinery, and a second agent loop.
- [ ] Map current Shay turn lifecycle, provider usage persistence, tool dispatch hooks, approval path, stream-consumer path, and Telegram polling/send lifecycle to canonical source seams.
- [ ] Add a versioned, redacted `TurnEvent` contract plus a per-turn `TurnReceipt` in the existing `shay_state.SessionDB` store. Preserve existing session aggregates and transcript behavior.
- [ ] Instrument `AIAgent.run_conversation`, central tool dispatch, and typed approvals so events are ordered, correlated, durable, and do not duplicate raw inputs/results.
- [ ] Add one transport-neutral turn projection contract for CLI/TUI/gateway/dashboard/ACP/cron. Telegram must consume the projection rather than own a separate turn state.
- [ ] Diagnose live Shay/Telegram errors and test gaps from gateway status, logs, source, and existing tests. Implement only high-confidence repairs that have a reproducible regression test.
- [ ] Run deterministic, cross-client, Telegram gateway, recovery/no-duplicate-side-effect, and Playwright-facing proof. Perform clean-room and adversarial review before integration.
- [ ] Commit a narrow, human-authored change set from this isolated worktree; leave the dirty main worktree untouched.

## Status
Superseded for bounded source execution by 2026-10-04-shay-source-completion.md. Broader actual client projection/browser/runtime acceptance remains unverified. Original isolated workstream created from clean base `fd663ef3264e7a16e7fdd2e15a3641e77bfc5023`.

## Started
2026-09-30 18:42 local

## Ended

## Execution
Dependency-first multi-swarm orchestration:
- Evidence swarm: source and black-box behavior mapping; produces an allow/reject matrix.
- Telegram reliability swarm: live status/log/test reconnaissance; produces exact reproducible gap packets.
- Ledger implementation swarm: works only in this worktree and only after the contract is frozen; produces a scoped commit.
- Review/proof swarm: attacks source-of-truth drift, migration/recovery, cross-surface projection, credential boundaries, approval invariants, and browser-visible dashboard behavior.

The captain integrates only clean, verified commits. No worker may touch the dirty main worktree, active gateway configuration, provider credentials, or external Studio repos.

## Research
Observation:
- `b-nnett/grok-bot-0.18-reconstructed` provides publicly observable provider/session routing, streamed lifecycle, bounded tool loops, and provider usage patterns.
- Its NOTICE identifies an unofficial reconstruction based on public binaries; it is not an upstream code source.
- Shay already has `AIAgent.run_conversation`, `model_tools`, `tools/approval`, `toolsets`, `gateway/session_context`, `shay_state.SessionDB`, client domain contracts, and Telegram stream/polling seams.

Interpretation:
- The correct adaptation is a clean-room turn/event ledger and projection slice inside Shay's existing state/runtime boundaries.
- Telegram should receive neutral lifecycle projection and contribute operational state; it should not become a parallel control plane.

Research artifact:
- `/Users/famtastic-fritz/famtastic/obsidian/Shay-Memory/research/grok-bot-reconstruction-clean-room-patterns-for-shay-2026-09-30.md`

## Review
Required before merge:
- Clean-room audit: no source/artifact/credential/updater reuse.
- Deterministic event ordering, redaction, idempotence, migration/reconciliation, and receipt aggregation tests.
- Mocked prompt-only, tool, denied approval, provider failure, interruption, and resume tests.
- No-duplicate-side-effect recovery test.
- Cross-client contract proof for CLI, TUI, gateway, ACP/API, cron, and Telegram.
- Playwright dashboard/user-facing proof; no WebSocket-only substitute.
- Independent read-only adversarial review of the final dirty diff, followed by repair/re-review if a material finding appears.

## Skills
- `shay-shay`
- `autonomous-ai-agents`
- `codex`
- `intelligence-control-plane-slice`

## Proof
- Isolated worktree: `/Users/famtastic-fritz/Development/FAMtastic/worktrees/shay-turn-ledger-telegram-hardening`
- Branch: `feat/shay-turn-ledger-telegram-hardening`
- Main-worktree recovery snapshot: `/Users/famtastic-fritz/.shay/private/backups/shay-turn-ledger-telegram-hardening-20260930-184201`
- Initial contract test: `./.venv/bin/python -m pytest -q tests/integration/test_cross_client_contract.py` — passed (1 test); pre-existing macOS temp cleanup warnings were emitted by identity-guard sandbox fixtures.
