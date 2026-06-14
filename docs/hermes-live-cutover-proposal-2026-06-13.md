# Hermes Live Cutover Proposal

Date: 2026-06-13
Status: proposal only — do not execute without Fritz approval

## Purpose

Describe the exact likely live cutover path from Hermes-named external surfaces to Shay-native command identity while preserving safety and rollback.

## Proposed Live Order

1. Preserve live Shay service identity as-is.
2. Introduce or verify a `hermes -> shay` compatibility wrapper.
3. Confirm `shay` is the canonical documented command.
4. Observe whether any scripts/habits still depend on `hermes`.
5. Only after usage mapping, decide whether `~/.shay/hermes-agent` can be retired.
6. Retire `~/.hermes` last, after explicit consumer validation and backup review.

## Proposed Forwarding Behavior

### `hermes`
- preferred live end state: forwards to `shay`
- fallback live end state: prints deprecation guidance and forwards to `shay`
- not allowed in this mission: delete the command outright

## Exact Live Actions That Would Require Fritz Approval

- replacing the live `hermes` shim
- deleting `~/.local/bin/hermes`
- deleting `~/.shay/hermes-agent`
- deleting `~/.hermes`
- editing any live launch agent
- restarting any live service
- copying or reusing live secrets/tokens

## Cutover Questions Still Open

- what still calls `hermes` today?
- does anything still read `~/.hermes` directly?
- can the live Hermes shim be replaced with a forwarder without breaking anything else?

## Current Recommendation

Do not cut over live yet.
Prepare the wrapper-forwarding packet and keep Hermes external surfaces intact until the external-usage map is stronger and Fritz approves the transition.
