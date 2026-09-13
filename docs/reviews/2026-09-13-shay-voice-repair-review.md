---
title: Shay voice repair review and proof
type: post-evaluation
created_at: 2026-09-13T16:55:00Z
status: ready_for_owner_review
branch: codex/shay-voice-repair
baseline: cf6bb95
---

# Shay voice repair review and proof

## Outcome

The feature is ready for owner review on the isolated branch. Shay now has a
private, zero-metered macOS TTS default; Homebrew whisper.cpp support that
reuses an existing local model; a versioned provider-neutral voice profile;
and explicit, fail-closed paid-provider selection. No runtime identity,
credential, production, or private `~/.shay` files were changed.

The final macOS voice is intentionally not approved by this implementation.
Samantha is a provisional technical default, and the generated three-voice
audition retains `owner_audition_required` until Fritz makes the selection.

## Reviewed behavior

- `stt.provider: local` prefers faster-whisper when installed and otherwise
  uses the existing local-command seam with Homebrew `whisper-cli`.
- whisper.cpp model resolution accepts an explicit `stt.local.model_path`,
  checks bounded known cache roots, and never downloads a GGML model.
- An explicit local STT choice never crosses to a cloud provider.
- `tts.provider: macos` invokes `/usr/bin/say` directly, writes WAVE audio,
  and uses ffmpeg only when the requested delivery format needs conversion.
- Unknown TTS providers return a configuration error instead of falling back.
- ElevenLabs requires an explicit provider choice, API key, and voice ID.
  A stale key or voice ID cannot activate the streaming ElevenLabs path while
  another provider is selected.
- `shay-v1` describes delivery only: pace, pauses, pronunciations, and named
  modes. Provider and voice candidates remain outside the profile.
- The profile's feminine presentation is limited to warm, intelligent, and
  confident delivery qualities and explicitly rejects gender-role stereotypes.
- Pronunciation guidance covers Shay-Shay, FAMtastic, and Fritz Medine
  (spoken as Fritz Medenay).

## Privacy, cost, and quality matrix

| Path | Processing | Metering | Quality boundary | Selection behavior |
|------|------------|----------|------------------|--------------------|
| macOS System Voice | Local | Zero metered API cost | Dependable system voice; less natural than premium neural speech | Default on macOS; final voice remains owner-gated |
| whisper.cpp STT | Local | Zero metered API cost | Depends on cached model and source audio | Reuses an existing model; never downloads one |
| faster-whisper STT | Local | Zero metered API cost | Depends on model and hardware | Preserved existing path; named models may download on first use |
| Edge TTS | Cloud | Keyless/unmetered option | Good neural quality; text leaves the device | Explicit alternative; no local fallback selects it |
| ElevenLabs | Cloud | Provider plan may be paid | Premium neural quality | Explicit provider, key, and voice ID required |
| Other cloud speech providers | Cloud | Provider-specific | Provider-specific | Explicit config/credentials required |

## Automated proof

Final focused regression through the repository wrapper:

```text
scripts/run_tests.sh \
  tests/shay_cli/test_voice_profiles.py \
  tests/shay_cli/test_nous_subscription.py \
  tests/shay_cli/test_tools_config.py \
  tests/shay_cli/test_placeholder_usage.py \
  tests/shay_cli/test_tips.py \
  tests/shay_cli/test_setup.py \
  tests/tools/test_tts_macos.py \
  tests/tools/test_transcription_tools.py \
  tests/tools/test_tts_dotenv_fallback.py \
  tests/tools/test_tts_mistral.py \
  tests/tools/test_tts_piper.py \
  tests/tools/test_voice_mode.py \
  tests/tools/test_voice_cli_integration.py \
  tests/tools/test_config_null_guard.py

393 passed, 22 skipped
```

Additional checks:

- `python -m compileall` passed for every changed Python module and script.
- `git diff --check` passed.
- A repository-wide check found no bundled legacy premium-voice label or ID.
- An earlier core-only run passed with 145 tests and 7 skips.

## Local end-to-end proof

The public TTS and STT APIs were exercised with all cloud credentials blank,
a temporary `SHAY_HOME`, `/usr/bin/say`, `/opt/homebrew/bin/whisper-cli`, and
the already-cached model at
`/Users/famtastic-fritz/.cache/hyperframes/whisper/models/ggml-small.en.bin`.
No network provider was invoked.

TTS result:

```text
provider: macos
success: true
voice_profile: shay-v1
voice_mode: conversational
voice_selection_status: owner_audition_required
WAV: RIFF PCM 16-bit mono 22050 Hz
OGG: Opus mono 24000 Hz
WAV SHA-256: e9dc69457b118d9cf2ac11d33156d333a5ac9221dd7dd0d7b30883e7adb023a7
OGG SHA-256: dd49969be58f86e1d367460d931495f2d2ede4b7d1db15093076c3012987a128
```

STT result:

```text
success: true
provider: local_command
backend: whisper_cpp
model_path: /Users/famtastic-fritz/.cache/hyperframes/whisper/models/ggml-small.en.bin
transcript:
  Hello Fritz MetaNay.
  Shae Shae is running locally.
  Fantastic privacy comes first,
  and paid fallback is disabled.
```

The transcript is understandable but imperfect on names and branding. That is
an honest quality limit of this system-voice/cached-model combination, not a
false-positive pass. The implementation reports the real backend and leaves
voice selection and future model-quality upgrades explicit.

## Audition proof

The no-network audition script generated valid PCM WAVE files for Samantha,
Flo (English US), and Shelley (English US), plus a manifest. It did not edit
runtime configuration.

```text
Samantha SHA-256: 3169d2fcaac74a3be3f6dbb9319edf068ed90751db076060d1bd9354dc3c093d
Flo SHA-256:      7171eaa2bb71aeddf6bf3a6d8840bc1a51ed83fac197818d2a2a1281c83098b1
Shelley SHA-256:  c43d201eb0bd4a5de2f1fdcae990531bf873c08ec3a99b97bac2bf7bf4dfadf8
```

## Known validation constraints

- The broader selected regression reached 400 passes and 91 skips, but the
  borrowed project environment lacks FastAPI and Starlette. The 57 failures
  and 11 setup errors were all import-time web-server dependency failures,
  not voice assertions. The changed web-server module still passes compileall.
- The full repository suite cannot collect because the same pre-existing
  environment lacks the `acp` package (`ModuleNotFoundError` in
  `tests/acp/test_entry.py`). No push is being made, so the repository's
  before-push full-suite gate is not being claimed as complete.
- Ruff was not available in the offline cache. It was not installed from the
  network merely to manufacture a lint result.

## Side-effect audit

- No paid or metered speech API call.
- No production, publish, push, or merge action.
- No edit to `~/.shay`, `PERSONA.md`, identity files, credentials, or private
  runtime configuration.
- No model download and no global package installation.
- Generated proof audio is confined to a temporary directory and the Codex
  visualization artifact directory.

## Owner decision remaining

Listen to the three generated candidates and choose the final installed macOS
voice. After that decision, set `tts.macos.voice` explicitly in owner-controlled
runtime configuration. That approval is intentionally outside this commit.
