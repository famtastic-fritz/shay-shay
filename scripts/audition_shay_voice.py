#!/usr/bin/env python3
"""Generate a no-network macOS audition set for Shay's voice profile."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shay_cli.voice_profiles import apply_pronunciations, resolve_voice_profile
from tools.tts_tool import _find_macos_say_binary, _generate_macos_tts


DEFAULT_CANDIDATES = (
    "Samantha",
    "Flo (English (US))",
    "Shelley (English (US))",
)
DEFAULT_SCRIPT = (
    "Hello. I'm Shay-Shay. I can keep the pace warm, clear, and confident. "
    "FAMtastic systems are ready for the next step. The final voice choice is yours."
)


def _safe_filename(voice: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", voice.lower()).strip("-")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate local macOS voice candidates without API calls or runtime-config changes."
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(tempfile.gettempdir()) / "shay-voice-auditions"),
    )
    parser.add_argument("--profile", default="shay-v1")
    parser.add_argument("--mode", default="conversational")
    parser.add_argument("--text", default=DEFAULT_SCRIPT)
    parser.add_argument("--voice", action="append", dest="voices")
    args = parser.parse_args()

    if not _find_macos_say_binary():
        parser.error("macOS /usr/bin/say is not available on this host")

    resolved = resolve_voice_profile(args.profile, mode=args.mode)
    text = apply_pronunciations(args.text, resolved)
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    generated = []

    for voice in args.voices or DEFAULT_CANDIDATES:
        output = output_dir / f"{_safe_filename(voice)}.wav"
        config = {
            "macos": {"voice": voice},
            "_resolved_voice_profile": resolved,
        }
        try:
            _generate_macos_tts(text, str(output), config)
        except Exception as exc:
            print(f"SKIP {voice}: {exc}")
            continue
        generated.append({"voice": voice, "path": str(output)})
        print(f"WROTE {voice}: {output}")

    manifest = {
        "voice_profile": resolved["id"],
        "voice_mode": resolved["mode"],
        "selection_status": resolved.get("selection", {}).get("status"),
        "generated": generated,
        "next_step": "Fritz auditions these files, then explicitly sets tts.macos.voice.",
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"MANIFEST {manifest_path}")
    return 0 if generated else 1


if __name__ == "__main__":
    raise SystemExit(main())
