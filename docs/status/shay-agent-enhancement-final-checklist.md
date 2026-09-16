# Shay enhancement final checklist

This is the R8 pre-review checklist. A checked source/test item is not a
release claim; external lifecycle and owner gates remain authoritative.

## Source and safety

- [x] R8 is based on the reviewed R7 tip and includes the reviewed R5 delta.
- [x] R8 changes are limited to its exact manifest.
- [x] The proof requires explicit external authority and a fresh output path.
- [x] No live `.shay` profile, credentials, persona, voice, STT/TTS, filming,
      or unrelated custom files were touched.
- [x] The negative E2E tests pass locally.

## Not yet proven

- [ ] R1–R7 external reviews, CI, commit, remote, Kanban, and completion chains.
- [ ] Frozen pre-candidate ledger and board snapshots.
- [ ] Six semantic upgrade-proof gates and rollback receipt.
- [ ] Three independent candidate-bound reviews.
- [ ] Provider-backed R8 branch CI (`test`, `e2e`, `shay-upgrade-proof`); the
      current GitHub Actions billing/runner issue remains unresolved.
- [ ] `record-commit`, `record-push-ci`, `record-kanban`, and `record-finalize`.
- [ ] Owner-authorized merge to `main` and any later live enablement.

## Current decision

**launch-blocked** — the external lifecycle authority is incomplete. This
checklist must not be changed to “complete” by editing repository prose; the
bound external recorder must establish the missing facts first.
