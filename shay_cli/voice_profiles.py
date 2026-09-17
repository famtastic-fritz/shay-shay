"""Provider-neutral, versioned voice-profile loading for Shay speech output.

Voice profiles describe delivery intent (pace, pauses, pronunciation, and
mode-specific changes). They deliberately do not replace ``PERSONA.md`` and do
not assign personality or behaviour based on gender presentation.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping, Optional

import yaml

from shay_constants import get_shay_home


SUPPORTED_VOICE_PROFILE_SCHEMA_VERSION = 1
DEFAULT_VOICE_PROFILE = "shay-v1"
_PROFILE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class VoiceProfileError(ValueError):
    """Raised when a requested voice profile is missing or invalid."""


def _profile_paths(name: str, shay_home: Optional[Path] = None) -> tuple[Path, Path]:
    if not _PROFILE_NAME_RE.fullmatch(name):
        raise VoiceProfileError(
            "Voice profile names may contain only lowercase letters, digits, dots, dashes, and underscores"
        )

    user_root = Path(shay_home) if shay_home is not None else get_shay_home()
    user_path = user_root / "voice_profiles" / f"{name}.yaml"
    bundled_path = Path(__file__).resolve().parent / "voice_profiles" / f"{name}.yaml"
    return user_path, bundled_path


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise VoiceProfileError(f"Voice profile field '{field}' must be a mapping")
    return value


def _positive_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise VoiceProfileError(f"Voice profile field '{field}' must be a positive number")
    return float(value)


def load_voice_profile(
    name: str = DEFAULT_VOICE_PROFILE,
    *,
    shay_home: Optional[Path] = None,
) -> dict[str, Any]:
    """Load a user override or bundled voice profile and validate its contract.

    User profiles live under the profile-aware ``SHAY_HOME/voice_profiles``
    directory. A user profile with the same name intentionally overrides the
    bundled profile without modifying repository or identity files.
    """

    user_path, bundled_path = _profile_paths(name, shay_home)
    source = user_path if user_path.is_file() else bundled_path
    if not source.is_file():
        raise VoiceProfileError(
            f"Voice profile '{name}' was not found in {user_path.parent} or the bundled profiles"
        )

    try:
        raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise VoiceProfileError(f"Could not read voice profile '{name}': {exc}") from exc

    profile = dict(_mapping(raw, "root"))
    version = profile.get("schema_version")
    if version != SUPPORTED_VOICE_PROFILE_SCHEMA_VERSION:
        raise VoiceProfileError(
            f"Voice profile '{name}' uses schema_version {version!r}; "
            f"supported version is {SUPPORTED_VOICE_PROFILE_SCHEMA_VERSION}"
        )
    if profile.get("id") != name:
        raise VoiceProfileError(
            f"Voice profile id {profile.get('id')!r} does not match requested name '{name}'"
        )
    profile_version = profile.get("profile_version")
    if not isinstance(profile_version, str) or not profile_version.strip():
        raise VoiceProfileError("Voice profile field 'profile_version' must be a non-empty string")

    _mapping(profile.get("presentation"), "presentation")
    delivery = _mapping(profile.get("delivery"), "delivery")
    pace = _mapping(delivery.get("pace"), "delivery.pace")
    pauses = _mapping(delivery.get("pauses"), "delivery.pauses")
    _positive_number(pace.get("speed_multiplier"), "delivery.pace.speed_multiplier")
    _positive_number(pace.get("words_per_minute"), "delivery.pace.words_per_minute")
    _positive_number(pauses.get("sentence_ms"), "delivery.pauses.sentence_ms")
    _positive_number(pauses.get("paragraph_ms"), "delivery.pauses.paragraph_ms")

    modes = _mapping(profile.get("modes"), "modes")
    default_mode = profile.get("default_mode")
    if not isinstance(default_mode, str) or default_mode not in modes:
        raise VoiceProfileError("Voice profile default_mode must name an entry in modes")

    pronunciations = profile.get("pronunciations", [])
    if not isinstance(pronunciations, list):
        raise VoiceProfileError("Voice profile field 'pronunciations' must be a list")
    for index, entry in enumerate(pronunciations):
        item = _mapping(entry, f"pronunciations[{index}]")
        if not str(item.get("written") or "").strip() or not str(item.get("spoken") or "").strip():
            raise VoiceProfileError(
                f"Voice profile pronunciation {index} requires non-empty written and spoken values"
            )

    profile["_source_path"] = str(source)
    return profile


def resolve_voice_profile(
    name: str = DEFAULT_VOICE_PROFILE,
    *,
    mode: Optional[str] = None,
    shay_home: Optional[Path] = None,
) -> dict[str, Any]:
    """Resolve a profile and mode into provider-neutral delivery values."""

    profile = load_voice_profile(name, shay_home=shay_home)
    selected_mode = (mode or profile["default_mode"]).strip().lower()
    modes = _mapping(profile["modes"], "modes")
    if selected_mode not in modes:
        available = ", ".join(sorted(str(key) for key in modes))
        raise VoiceProfileError(
            f"Voice profile '{name}' has no mode '{selected_mode}'. Available modes: {available}"
        )

    delivery = _mapping(profile["delivery"], "delivery")
    pace = _mapping(delivery["pace"], "delivery.pace")
    pauses = _mapping(delivery["pauses"], "delivery.pauses")
    mode_config = _mapping(modes[selected_mode], f"modes.{selected_mode}")
    pace_multiplier = _positive_number(
        mode_config.get("pace_multiplier", 1.0),
        f"modes.{selected_mode}.pace_multiplier",
    )
    pause_multiplier = _positive_number(
        mode_config.get("pause_multiplier", 1.0),
        f"modes.{selected_mode}.pause_multiplier",
    )

    return {
        "schema_version": profile["schema_version"],
        "id": profile["id"],
        "profile_version": profile["profile_version"],
        "mode": selected_mode,
        "presentation": dict(_mapping(profile["presentation"], "presentation")),
        "selection": dict(profile.get("selection") or {}),
        "speed_multiplier": round(
            _positive_number(pace["speed_multiplier"], "delivery.pace.speed_multiplier")
            * pace_multiplier,
            4,
        ),
        "words_per_minute": round(
            _positive_number(pace["words_per_minute"], "delivery.pace.words_per_minute")
            * pace_multiplier
        ),
        "sentence_pause_ms": round(
            _positive_number(pauses["sentence_ms"], "delivery.pauses.sentence_ms")
            * pause_multiplier
        ),
        "paragraph_pause_ms": round(
            _positive_number(pauses["paragraph_ms"], "delivery.pauses.paragraph_ms")
            * pause_multiplier
        ),
        "pronunciations": [dict(item) for item in profile.get("pronunciations", [])],
        "source_path": profile["_source_path"],
    }


def apply_pronunciations(text: str, resolved_profile: Optional[Mapping[str, Any]]) -> str:
    """Apply literal, provider-neutral pronunciation substitutions."""

    if not resolved_profile:
        return text
    pronunciations = resolved_profile.get("pronunciations", [])
    if not isinstance(pronunciations, list):
        return text

    result = text
    entries = sorted(
        (item for item in pronunciations if isinstance(item, Mapping)),
        key=lambda item: len(str(item.get("written") or "")),
        reverse=True,
    )
    for item in entries:
        written = str(item.get("written") or "")
        spoken = str(item.get("spoken") or "")
        if written and spoken:
            result = result.replace(written, spoken)
    return result
