---
title: Shay voice repair implementation discovery
type: note
created_at: 2026-09-13T16:35:00Z
freshness: 2026-09-13 live worktree and host probes
verdict: extend the existing local command seam and add a fail-closed local macOS TTS default
related_topics: [Shay voice mode, whisper.cpp, voice profiles, ElevenLabs]
tags: [research, shay, stt, tts, voice, whisper-cpp, macos]
artifact_type: research-capture
---

# Shay voice repair implementation discovery

## Summary

Shay already has the right extension points. The smallest safe repair is to teach the existing local-command STT path how to invoke Homebrew `whisper-cli` with a local GGML model, add a native macOS `say` TTS provider as the zero-metered default, require an explicit ElevenLabs voice ID, and resolve delivery guidance through a versioned voice profile outside `PERSONA.md`.

## Research question

How can the current Mac's installed speech capabilities become Shay's supported default without editing private identity/runtime files, making paid calls, or introducing a new framework?

## Reuse status

- freshness: same-day repository and host probes
- verdict: partially researched; this note captures the implementation-specific delta
- related topics: the existing vault note `shay-open-voice-stack-persona-2026-09-13.md`

## Observations

- The isolated lane is `/Users/famtastic-fritz/Development/FAMtastic/worktrees/shay-voice-repair` on `codex/shay-voice-repair` at baseline `cf6bb95`, matching `origin/main`.
- `/opt/homebrew/bin/whisper-cli` is installed from whisper.cpp 1.9.2.
- `/Users/famtastic-fritz/.cache/hyperframes/whisper/models/ggml-small.en.bin` is already cached locally.
- `faster_whisper`, Piper, and KittenTTS are not importable in the active Python environment; `edge_tts` is importable.
- `tools/transcription_tools.py` already supports a `local_command` provider and `SHAY_LOCAL_STT_COMMAND`, but automatic discovery only searches for a binary named `whisper` and emits Python Whisper CLI flags.
- `tools/tts_tool.py` and `shay_cli/config.py` carry a bundled Adam voice ID as an ElevenLabs default.
- The tracked TTS default is Edge TTS. Edge is zero-key but cloud-based, so text leaves the machine.
- `/usr/bin/say` is installed and can synthesize files locally. Installed English feminine-presenting candidates include Samantha, Flo (English US), Shelley (English US), Karen, Moira, and Tessa.
- The repository has no versioned provider-neutral voice-profile loader. Delivery controls live only in provider-specific configuration.
- Existing voice playback code assumes an MP3 output path even though command/local providers may produce WAV.

## Interpretations

- The local STT gap is syntax and model-path resolution, not missing inference capability.
- Extending `local_command` preserves the provider boundary and avoids adding another STT provider or Python dependency.
- The safest no-metered-cost TTS default on this Mac is `/usr/bin/say`: it is local, installed, deterministic, and requires no download. Its quality is lower than premium neural services, which must remain an explicit tradeoff.
- A voice profile should express delivery intent and normalized controls, not personality or gendered behavior. Provider adapters may map the same profile to their supported controls.
- A specific system voice is subjective. Samantha can be a provisional technical candidate, but the profile and documentation must keep final selection owner-gated and provide a repeatable local audition.
- Paid providers must never be chosen as fallback. Selecting ElevenLabs should require both an explicit provider choice and an explicit voice ID.

## Capability notes

- STT adoption: Homebrew whisper.cpp through the existing local-command seam, with explicit model-path support and bounded local cache discovery.
- TTS adoption: native macOS `say`; zero metered cost and local privacy, with system-voice quality limits.
- Voice profile: versioned YAML bundled with the package and overridable from profile-aware `SHAY_HOME`, resolved to pace, pauses, pronunciation, and named operating modes.
- Premium lane: ElevenLabs remains available only when explicitly selected and configured; no bundled voice identity.
- Proof lane: temporary `SHAY_HOME`, generated local fixtures, no production config mutation, no API keys, and no network provider calls.

## Sources

- Shay STT implementation [local source] — `tools/transcription_tools.py`
- Shay TTS implementation [local source] — `tools/tts_tool.py`
- Tracked defaults and migration behavior [local source] — `shay_cli/config.py`
- Voice setup surfaces [local source] — `shay_cli/setup.py` and `shay_cli/tools_config.py`
- Existing STT tests [local source] — `tests/tools/test_transcription_tools.py`
- whisper.cpp CLI contract [local executable] — `/opt/homebrew/bin/whisper-cli --help` and `--version`
- Cached GGML model [local artifact] — `/Users/famtastic-fritz/.cache/hyperframes/whisper/models/ggml-small.en.bin`
- macOS speech contract [local manual] — `man say`
- Prior research [read-only vault note] — `/Users/famtastic-fritz/Development/FAMtastic/obsidian/Shay-Memory/research/shay-open-voice-stack-persona-2026-09-13.md`

## Next actions

- Implement and test whisper.cpp binary/model resolution without changing the legacy command-template contract.
- Add the bundled voice profile and local macOS TTS provider, then update setup/docs.
- Generate a three-voice local audition set and run local STT/TTS smoke proofs in temporary state.
- Review the scoped diff and commit it without pushing or merging.

## Resume prompt

Resume in the isolated `codex/shay-voice-repair` worktree, implement the recorded local STT/TTS and voice-profile seams, then complete the proof and review packet without touching runtime identity or credential files.
