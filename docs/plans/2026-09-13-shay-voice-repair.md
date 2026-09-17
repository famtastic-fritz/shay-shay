# Shay Voice Repair

Title: Shay voice repair
Purpose: Make Shay's local speech paths private, zero-metered-cost by default, provider-neutral, and reviewable without changing Fritz's private identity or runtime files.
Goal: Ship a focused feature commit that supports Homebrew whisper-cli STT, removes the Adam voice assumption, adds a versioned feminine voice profile, documents explicit provider tradeoffs, and proves local STT/TTS behavior without paid calls.

Tasks:
- [x] Re-anchor the isolated lane and map current STT, TTS, config, and voice defaults
- [x] Record the source-backed implementation decision and boundaries
- [x] Implement local whisper-cli support and provider-neutral voice profiles
- [x] Replace paid or male voice assumptions with safe explicit defaults
- [x] Add focused tests and user documentation
- [x] Run focused tests plus local STT/TTS smoke proof without metered calls
- [x] Review the diff, record post-evaluation, and create the feature commit

Status: completed
Started: 2026-09-13 12:18 EDT
Ended: 2026-09-13 12:56 EDT
Execution: single — branch `codex/shay-voice-repair`; worktree `/Users/famtastic-fritz/Development/FAMtastic/worktrees/shay-voice-repair`; landing requires owner-reviewed merge to `main`
Research: yes — `docs/research/2026-09-13-shay-voice-repair-discovery.md`
Review: yes — `docs/reviews/2026-09-13-shay-voice-repair-review.md`
Skills: none
Blocked By: none

Proof:
- Focused configuration, STT, TTS, and voice-profile tests: 393 passed, 22 skipped through `scripts/run_tests.sh`
- Local whisper-cli smoke transcribed generated macOS speech through `local_command` / `whisper_cpp` with the existing cached model and no network API
- Local macOS TTS smoke produced valid WAV and Opus artifacts and retained `owner_audition_required`
- Three valid local audition WAVs generated for Samantha, Flo, and Shelley without config mutation
- `python -m compileall`, repository-wide removal check for the bundled Adam identity, and `git diff --check` passed
- Review and limitations recorded in `docs/reviews/2026-09-13-shay-voice-repair-review.md`
- Feature implementation committed locally on `codex/shay-voice-repair`; no push or merge performed
