from pathlib import Path

import pytest
import yaml

from shay_cli.voice_profiles import (
    DEFAULT_VOICE_PROFILE,
    VoiceProfileError,
    apply_pronunciations,
    load_voice_profile,
    resolve_voice_profile,
)


def test_bundled_shay_profile_is_versioned_and_owner_gated():
    profile = load_voice_profile(DEFAULT_VOICE_PROFILE)

    assert profile["schema_version"] == 1
    assert profile["id"] == "shay-v1"
    assert profile["profile_version"] == "1.0.0"
    assert profile["presentation"]["gender_expression"] == "feminine"
    assert profile["presentation"]["traits"] == ["warm", "intelligent", "confident"]
    assert profile["selection"]["status"] == "owner_audition_required"
    assert "provider" not in profile["selection"]
    assert "voice" not in profile["selection"]
    assert not any(key.startswith("provisional_") for key in profile["selection"])


def test_mode_changes_resolve_pace_and_pauses():
    conversational = resolve_voice_profile("shay-v1", mode="conversational")
    focused = resolve_voice_profile("shay-v1", mode="focused")
    reassuring = resolve_voice_profile("shay-v1", mode="reassuring")

    assert focused["speed_multiplier"] > conversational["speed_multiplier"]
    assert focused["sentence_pause_ms"] < conversational["sentence_pause_ms"]
    assert reassuring["speed_multiplier"] < conversational["speed_multiplier"]
    assert reassuring["paragraph_pause_ms"] > conversational["paragraph_pause_ms"]


def test_pronunciations_are_provider_neutral():
    resolved = resolve_voice_profile("shay-v1")

    assert apply_pronunciations(
        "Shay-Shay builds FAMtastic systems for Fritz Medine.", resolved
    ) == (
        "Shay Shay builds Fam-tastic systems for Fritz Medenay."
    )


def test_profile_aware_user_override_wins(tmp_path):
    profile_dir = tmp_path / "voice_profiles"
    profile_dir.mkdir()
    bundled = load_voice_profile("shay-v1")
    bundled.pop("_source_path")
    bundled["delivery"]["pace"]["words_per_minute"] = 166
    (profile_dir / "shay-v1.yaml").write_text(
        yaml.safe_dump(bundled, sort_keys=False),
        encoding="utf-8",
    )

    resolved = resolve_voice_profile("shay-v1", shay_home=tmp_path)

    assert resolved["words_per_minute"] == 166
    assert Path(resolved["source_path"]) == profile_dir / "shay-v1.yaml"


@pytest.mark.parametrize("name", ["../PERSONA", "MixedCase", "voice/profile"])
def test_profile_name_cannot_escape_profile_directories(name):
    with pytest.raises(VoiceProfileError):
        load_voice_profile(name)


def test_unsupported_schema_fails_closed(tmp_path):
    profile_dir = tmp_path / "voice_profiles"
    profile_dir.mkdir()
    (profile_dir / "future.yaml").write_text(
        "schema_version: 99\nid: future\n",
        encoding="utf-8",
    )

    with pytest.raises(VoiceProfileError, match="schema_version"):
        load_voice_profile("future", shay_home=tmp_path)
