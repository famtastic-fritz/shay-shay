import json
import queue
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from tools import tts_tool
from tools.tts_tool import (
    BUILTIN_TTS_PROVIDERS,
    DEFAULT_ELEVENLABS_VOICE_ID,
    DEFAULT_PROVIDER,
    _configured_elevenlabs_voice_id,
    _generate_macos_tts,
    text_to_speech_tool,
)


def test_macos_is_the_fail_closed_local_default():
    expected = "macos" if sys.platform == "darwin" else "edge"
    assert DEFAULT_PROVIDER == expected
    assert "macos" in BUILTIN_TTS_PROVIDERS
    assert DEFAULT_ELEVENLABS_VOICE_ID == ""


def test_elevenlabs_voice_must_be_explicit():
    with pytest.raises(ValueError, match="explicit tts.elevenlabs.voice_id"):
        _configured_elevenlabs_voice_id({"elevenlabs": {"voice_id": ""}})


def test_elevenlabs_key_without_voice_does_not_satisfy_requirements(monkeypatch):
    monkeypatch.setattr(tts_tool, "_has_any_command_tts_provider", lambda: False)
    monkeypatch.setattr(tts_tool, "_find_macos_say_binary", lambda: None)
    monkeypatch.setattr(
        tts_tool,
        "_import_edge_tts",
        lambda: (_ for _ in ()).throw(ImportError()),
    )
    monkeypatch.setattr(tts_tool, "_import_elevenlabs", lambda: object())
    monkeypatch.setattr(
        tts_tool,
        "_import_openai_client",
        lambda: (_ for _ in ()).throw(ImportError()),
    )
    monkeypatch.setattr(
        tts_tool,
        "_import_mistral_client",
        lambda: (_ for _ in ()).throw(ImportError()),
    )
    monkeypatch.setattr(tts_tool, "_check_neutts_available", lambda: False)
    monkeypatch.setattr(tts_tool, "_check_kittentts_available", lambda: False)
    monkeypatch.setattr(tts_tool, "_check_piper_available", lambda: False)
    monkeypatch.setattr(tts_tool, "_has_openai_audio_backend", lambda: False)
    monkeypatch.setattr(tts_tool, "_load_tts_config", lambda: {"elevenlabs": {"voice_id": ""}})
    monkeypatch.setattr(
        tts_tool,
        "get_env_value",
        lambda name, default=None: "configured-key" if name == "ELEVENLABS_API_KEY" else default,
    )

    assert tts_tool.check_tts_requirements() is False


def test_generate_macos_tts_uses_voice_rate_and_wav(monkeypatch, tmp_path):
    output = tmp_path / "shay.wav"
    seen = []
    monkeypatch.setattr(tts_tool, "_find_macos_say_binary", lambda: "/usr/bin/say")

    def fake_run(command, **kwargs):
        seen.append(command)
        target = Path(command[command.index("--output-file") + 1])
        target.write_bytes(b"RIFF" + b"\0" * 64)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(tts_tool.subprocess, "run", fake_run)

    result = _generate_macos_tts(
        "Hello.",
        str(output),
        {
            "macos": {"voice": "Samantha"},
            "_resolved_voice_profile": {
                "words_per_minute": 171,
                "sentence_pause_ms": 160,
                "paragraph_pause_ms": 400,
            },
        },
    )

    assert result == str(output)
    assert output.read_bytes().startswith(b"RIFF")
    assert seen[0][seen[0].index("--voice") + 1] == "Samantha"
    assert seen[0][seen[0].index("--rate") + 1] == "171"
    assert "--file-format" in seen[0]
    assert "WAVE" in seen[0]


def test_text_to_speech_applies_profile_and_reports_owner_gate(monkeypatch, tmp_path):
    output = tmp_path / "shay.wav"
    captured = {}

    monkeypatch.setattr(
        tts_tool,
        "_load_tts_config",
        lambda: {
            "provider": "macos",
            "voice_profile": "shay-v1",
            "voice_mode": "focused",
            "macos": {"voice": "Samantha"},
        },
    )

    def fake_generate(text, output_path, config):
        captured["text"] = text
        captured["profile"] = config["_resolved_voice_profile"]
        Path(output_path).write_bytes(b"RIFF" + b"\0" * 64)
        return output_path

    monkeypatch.setattr(tts_tool, "_generate_macos_tts", fake_generate)
    monkeypatch.setattr(tts_tool, "_convert_to_opus", lambda path: None)

    result = json.loads(
        text_to_speech_tool(
            "Shay-Shay builds FAMtastic systems.",
            output_path=str(output),
        )
    )

    assert result["success"] is True
    assert result["provider"] == "macos"
    assert result["voice_profile"] == "shay-v1"
    assert result["voice_mode"] == "focused"
    assert result["voice_selection_status"] == "owner_audition_required"
    assert captured["text"] == "Shay Shay builds Fam-tastic systems."
    assert captured["profile"]["words_per_minute"] > 178


def test_unknown_provider_does_not_fall_back_to_cloud(monkeypatch, tmp_path):
    monkeypatch.setattr(
        tts_tool,
        "_load_tts_config",
        lambda: {"provider": "not-configured", "voice_profile": "off"},
    )
    monkeypatch.setattr(
        tts_tool,
        "_generate_edge_tts",
        lambda *args, **kwargs: pytest.fail("cloud fallback must not run"),
    )

    result = json.loads(
        text_to_speech_tool("Hello", output_path=str(tmp_path / "out.wav"))
    )

    assert result["success"] is False
    assert "Unknown TTS provider" in result["error"]


def test_streaming_never_initializes_elevenlabs_unless_explicitly_selected(monkeypatch):
    text_queue = queue.Queue()
    text_queue.put(None)
    stop_event = threading.Event()
    done_event = threading.Event()

    monkeypatch.setattr(
        tts_tool,
        "_load_tts_config",
        lambda: {
            "provider": "macos",
            "elevenlabs": {"voice_id": "explicit-but-inactive"},
        },
    )
    monkeypatch.setattr(
        tts_tool,
        "get_env_value",
        lambda name, default=None: (
            "present-but-inactive" if name == "ELEVENLABS_API_KEY" else default
        ),
    )
    monkeypatch.setattr(
        tts_tool,
        "_import_elevenlabs",
        lambda: pytest.fail("inactive paid provider must not initialize"),
    )

    tts_tool.stream_tts_to_speaker(text_queue, stop_event, done_event)

    assert done_event.is_set()
