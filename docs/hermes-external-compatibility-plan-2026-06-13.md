# Hermes External Compatibility Plan

Date: 2026-06-13
Lane: sandbox planning only

## Purpose

Map the Hermes-named external surfaces that must survive long enough for a safe cutover from Hermes habits/contracts to Shay-native identity.

## External Surfaces

### `~/.local/bin/hermes`
- classification: external_contract_remove_last
- current role: likely user habit/script/automation entrypoint
- current risk: deleting it first could break unknown callers immediately
- current recommendation: keep temporarily; later forward `hermes` to `shay` with deprecation guidance

### `~/.shay/hermes-agent`
- classification: external_contract_remove_last
- current role: backing tree currently targeted by the live `hermes` shim
- current risk: deleting it first breaks the shim and any hidden workflows anchored to that tree
- current recommendation: keep until wrapper forwarding and external usage mapping are complete

### `~/.hermes`
- classification: external_contract_remove_last
- current role: legacy Hermes state/home surface with potential old consumers
- current risk: unknown rollback/session/config/history dependencies
- current recommendation: keep until consumer risk is explicitly mapped and cutover order is approved

### launch agents / service identity
- observed posture: live service naming already appears Shay-native (`ai.shay.gateway`)
- recommendation: keep Shay-native service identity; do not reintroduce Hermes naming here

### shell aliases / human habits / old workflows
- status: partially mapped only
- recommendation: treat as research surface, not cleanup target

## Forwarding Doctrine

Best likely live cutover path:
1. make `shay` the canonical command and docs path
2. keep `hermes` as a temporary compatibility wrapper
3. optionally print deprecation guidance when `hermes` is used
4. remove the wrapper only after actual external usage is mapped and Fritz approves the live cutover

## Remove-Last Doctrine

Remove last, not first:
- `~/.local/bin/hermes`
- `~/.shay/hermes-agent`
- `~/.hermes`

## Open Risks

- external `hermes` callers not fully mapped
- possible old tooling reading `~/.hermes` artifacts directly
- human habit breakage if `hermes` disappears before `shay` forwarding exists

## Promotion Gate

This plan can inform a PR and final cutover packet, but no live action should be taken from this doc alone.
