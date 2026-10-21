# Telegram Gateway Operational Health — 2026-10-01

## Purpose

Close the false-green Telegram readiness gap: a configured bot must not be reported as operational when the adapter is unavailable, the gateway is stopped, or multiple long-polling processes are active.

## Canonical Runtime Verified

- Repository: `~/Development/FAMtastic/shay-shay`
- Interpreter: canonical project virtual environment, `.venv/bin/python`
- Service manager: macOS `launchd`
- Runtime ownership: exactly one detected Shay gateway process
- Telegram adapter: `python-telegram-bot` importable from the canonical virtual environment

No Telegram token, chat ID, or other credential is recorded here.

## Health Model

Telegram now has four distinct local readiness layers:

1. Configuration — a bot token exists.
2. Dependency — `python-telegram-bot` is importable by the canonical Shay environment.
3. Runtime — the gateway is running and exactly one gateway process owns long polling.
4. Path proof — outbound delivery and a human-originated inbound reply have both been observed.

`shay status` and `shay doctor` report the first three live local layers. They do not infer historical path proof from gateway logs, so `delivery path unverified` means no persisted path-proof indicator is wired into those commands — not that a completed historical round trip does not exist.

## Code Changes

- Added `shay_cli/telegram_health.py` as a redaction-safe readiness assessor shared by status and doctor.
- Updated `shay_cli/status.py` to mark Telegram degraded for:
  - missing `python-telegram-bot`
  - stopped or unavailable gateway state
  - no discoverable gateway process
  - duplicate gateway processes
- Updated `shay_cli/doctor.py` with concrete repair guidance for each degraded condition.
- Added regression coverage in `tests/shay_cli/test_telegram_health.py`, including duplicate-poller detection.

## Verification Evidence

- Focused regression suite: `5 passed`. The host also emitted non-failing pytest cleanup-permission warnings for temporary identity-guard directories; that test-harness gap is logged separately.
- `shay status`: Telegram reported configured, runtime ready, and delivery path unverified; launchd reported one gateway process.
- `shay doctor`: Telegram local delivery prerequisites passed and explicitly reported one active gateway process.
- Controlled outbound Telegram probe: succeeded and returned a Telegram message ID. The ID is intentionally not retained.
- Full round trip: the canonical gateway started at `2026-09-30 19:30:49 EDT`; at `21:26:31 EDT` it processed the Telegram session-reset path and sent its 206-character acknowledgement. Fritz confirms this was the requested `/new` reply. Sixteen seconds later, it received a normal Telegram message and completed a 132.7-second model response. This proves inbound update handling, the gateway acknowledgement path, and normal inbound-to-outbound delivery under the current canonical runtime.

## Acceptance Boundary

Closed. Full inbound/outbound round-trip proof was completed on the canonical gateway. Do not ask Fritz to repeat the `/new` acceptance test solely because `shay status` reports that it does not itself persist historical path-proof state. A new round trip is only required after a material Telegram repair, gateway ownership change, or a newly observed delivery failure.

## Gap Record

Canonical gap ledger: `~/.local/share/famtastic/gaps.jsonl`

A closed local-health record was updated with the completed acceptance result. The ledger record contains no credentials or Telegram identifiers.
