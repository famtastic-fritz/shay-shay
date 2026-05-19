"""Tests for tool error sanitization before exception text enters model context."""
from __future__ import annotations

import json

from model_tools import _TOOL_ERROR_MAX_LEN, _sanitize_tool_error, handle_function_call
from tools.registry import registry


class TestToolErrorSanitization:
    def test_strips_role_like_tags(self):
        out = _sanitize_tool_error("bad <tool_call>injected</tool_call> <system>x</system>")
        assert "<tool_call>" not in out
        assert "</tool_call>" not in out
        assert "<system>" not in out
        assert "</system>" not in out
        assert out.startswith("[TOOL_ERROR] ")

    def test_strips_cdata_and_code_fences(self):
        out = _sanitize_tool_error("```json\n<![CDATA[secret]]>\npayload\n```")
        assert "CDATA" not in out
        assert "```" not in out
        assert "payload" in out

    def test_caps_long_input(self):
        out = _sanitize_tool_error("A" * (_TOOL_ERROR_MAX_LEN * 2))
        body = out[len("[TOOL_ERROR] "):]
        assert len(body) == _TOOL_ERROR_MAX_LEN
        assert body.endswith("...")

    def test_handle_function_call_exception_path_is_sanitized(self):
        def _boom(_args, **_kwargs):
            raise RuntimeError("<tool_call>bad</tool_call>")

        registry.register(
            "sanitize_error_test_tool",
            {"type": "function", "function": {"name": "sanitize_error_test_tool", "parameters": {"type": "object"}}},
            _boom,
            toolset="testing",
        )
        payload = json.loads(handle_function_call("sanitize_error_test_tool", {}))
        assert payload["error"].startswith("[TOOL_ERROR] ")
        assert "<tool_call>" not in payload["error"]
