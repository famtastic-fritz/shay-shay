"""Tests for the Nous-Shay-Shay-3/4 non-agentic warning detector.

Prior to this check, the warning fired on any model whose name contained
``"shay"`` anywhere (case-insensitive). That false-positived on unrelated
local Modelfiles such as ``shay-brain:qwen3-14b-ctx16k`` — a tool-capable
Qwen3 wrapper that happens to live under the "shay" tag namespace.

``is_nous_shay_non_agentic`` should only match the actual Nous Research
Shay-Shay-3 / Shay-Shay-4 chat family.
"""

from __future__ import annotations

import pytest

from shay_cli.model_switch import (
    _SHAY_MODEL_WARNING,
    _check_shay_model_warning,
    is_nous_shay_non_agentic,
)


@pytest.mark.parametrize(
    "model_name",
    [
        "NousResearch/Shay-Shay-3-Llama-3.1-70B",
        "NousResearch/Shay-Shay-3-Llama-3.1-405B",
        "shay-3",
        "Shay-Shay-3",
        "shay-4",
        "shay-4-405b",
        "shay_4_70b",
        "openrouter/shay3:70b",
        "openrouter/nousresearch/shay-4-405b",
        "NousResearch/Shay3",
        "shay-3.1",
    ],
)
def test_matches_real_nous_shay_chat_models(model_name: str) -> None:
    assert is_nous_shay_non_agentic(model_name), (
        f"expected {model_name!r} to be flagged as Nous Shay-Shay 3/4"
    )
    assert _check_shay_model_warning(model_name) == _SHAY_MODEL_WARNING


@pytest.mark.parametrize(
    "model_name",
    [
        # Kyle's local Modelfile — qwen3:14b under a custom tag
        "shay-brain:qwen3-14b-ctx16k",
        "shay-brain:qwen3-14b-ctx32k",
        "shay-honcho:qwen3-8b-ctx8k",
        # Plain unrelated models
        "qwen3:14b",
        "qwen3-coder:30b",
        "qwen2.5:14b",
        "claude-opus-4-6",
        "anthropic/claude-sonnet-4.5",
        "gpt-5",
        "openai/gpt-4o",
        "google/gemini-2.5-flash",
        "deepseek-chat",
        # Non-chat Shay-Shay models we don't warn about
        "shay-llm-2",
        "shay2-pro",
        "nous-shay-2-mistral",
        # Edge cases
        "",
        "shay",  # bare "shay" isn't the 3/4 family
        "shay-brain",
        "brain-shay-3-impostor",  # "3" not preceded by /: boundary
    ],
)
def test_does_not_match_unrelated_models(model_name: str) -> None:
    assert not is_nous_shay_non_agentic(model_name), (
        f"expected {model_name!r} NOT to be flagged as Nous Shay-Shay 3/4"
    )
    assert _check_shay_model_warning(model_name) == ""


def test_none_like_inputs_are_safe() -> None:
    assert is_nous_shay_non_agentic("") is False
    # Defensive: the helper shouldn't crash on None-ish falsy input either.
    assert _check_shay_model_warning("") == ""
