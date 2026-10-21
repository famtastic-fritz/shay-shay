# Telegram overflow delivery — scoped local-main candidate

Purpose: prevent a small-platform message limit or failed continuation from being reported as a delivered final answer.

Goal: keep only the transport delivery repair from the larger turn-ledger branch, with the existing Shay gateway as the sole runtime and its dirty main worktree preserved.

- [x] Compare `f5d00eb` with Shay `main` and isolate its gateway delivery dependency.
- [x] Keep the polling reconnect rewrite out of this slice after adjacent tests exposed failures.
- [x] Run the canonical hermetic wrapper on delivery, stream, Telegram format/conflict, restart and reconnect tests.
- [ ] Merge the separate turn-ledger/control-plane candidate only after its clean-room and cross-client gates are met.
- [ ] Observe a release-matched owner Telegram flow before calling the behavior accepted.

Status: `changed` source candidate for local main; not deployed or owner accepted.

Started: 2026-10-04.

Ended: 2026-10-04 for source proof; runtime and owner gates remain open.

Execution: isolated branch from `5aaecc3`, four files only: `gateway/platforms/base.py`, `gateway/platforms/telegram.py`, `gateway/stream_consumer.py`, and `tests/gateway/test_stream_consumer.py`. The base result type carries a partial-delivery receipt; Telegram returns delivered and missing portions on a continuation failure; the consumer retains only the missing suffix, bounds its buffer by the adapter's hard limit and avoids a tight retry loop. The branch does not import the reconstructed external bot, turn-ledger persistence, provider credentials, updater machinery, or a second runtime. The original 33 dirty tracked main-worktree paths were not staged or copied.

Research: the original full ledger branch also changed polling generation/recovery task handling. Its focused suite passed, but two existing reconnect tests failed when run with that polling rewrite. Retaining main's polling implementation and only the overflow-delivery change made the targeted delivery/reconnect group pass (240/240). A separate `/new` update-prompt fixture fails on untouched `main` as well; it is not attributed to this slice.

Review: `git diff --check` passed. The full hermetic gateway suite on this slice had **5,329 pass, 17 fail, 10 skip**; the same suite on untouched `5aaecc3` had **5,326 pass, the identical 17 fail, 10 skip**. The three added passing tests therefore introduced no new failing test IDs; the existing failures remain separate work. The local wrapper strips credential environment variables and uses temporary homes; neither run sent a provider message. This slice changes no ledger payload schema or persistent transcript content. It is source-level delivery reliability, not proof that Telegram accepted a real message or that a user saw it. The broader turn-ledger plan still requires clean-room provenance review, cross-client projection/recovery evidence and dashboard proof before that separate candidate reaches main.

Skills: FAMtastic build review and Agency Agents Git Workflow Master, pinned upstream `765be42358100bf89d2faa567668a94c602f9a26`.

Proof and handoff matrix:

| capability_id | Customer job / entry | Saved result and reversal | Evidence | Provider / acceptance / consumption | Next gate |
| --- | --- | --- | --- | --- | --- |
| `shay.telegram.overflow-delivery` | Shay operator receives one complete answer through the Telegram gateway after an oversized or partly failed continuation | In-memory sent/unsent portion and final-delivery receipt; gateway may retry only the missing suffix. No new customer record or rollback action. | `local_tested` on isolated source; 240 focused/adjacent wrapper tests passed and full-suite differential found zero added failures | Provider `connected_unverified` for the existing gateway, with this revision not installed; owner acceptance `pending`; consumption `not_applicable` | Review exact source commit, then release-matched real Telegram delivery and recovery, without duplicate messages. |

No push, gateway restart, Telegram send, scheduler/provider change or hosted release was performed for this candidate.
