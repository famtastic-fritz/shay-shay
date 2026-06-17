#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.delegate_tool import _build_child_agent, _load_config, _resolve_delegation_credentials
from shay_cli.config import load_config


def _normalize_model(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("default") or value.get("model") or value
    return value


def _make_parent(main_cfg: dict) -> Any:
    model = _normalize_model(main_cfg.get("model"))
    provider = str(main_cfg.get("provider") or "").strip() or None
    base_url = str(main_cfg.get("base_url") or "").strip() or None
    api_mode = str(main_cfg.get("api_mode") or "").strip() or None
    parent = SimpleNamespace()
    parent.model = model
    parent.provider = provider
    parent.base_url = base_url
    parent.api_mode = api_mode
    parent.api_key = None
    parent.platform = "cli"
    parent.providers_allowed = None
    parent.providers_ignored = None
    parent.providers_order = None
    parent.provider_sort = None
    parent.openrouter_min_coding_score = None
    parent.max_tokens = main_cfg.get("max_tokens")
    parent.reasoning_config = main_cfg.get("reasoning")
    parent.prefill_messages = main_cfg.get("prefill_messages")
    parent._session_db = None
    parent._delegate_depth = 0
    parent._active_children = []
    parent._active_children_lock = threading.Lock()
    parent._print_fn = None
    parent.tool_progress_callback = None
    parent.thinking_callback = None
    parent.valid_tool_names = []
    parent.enabled_toolsets = list(main_cfg.get("enabled_toolsets") or ["web", "terminal", "file", "browser", "search", "vision", "cronjob", "computer_use", "todo", "skills", "kanban", "homeassistant", "spotify", "tts", "video", "discord", "discord_admin", "feishu_doc", "feishu_drive", "yuanbao", "apple", "session_search", "delegation"])
    parent.session_id = "probe-parent"
    parent._fallback_chain = None
    parent.acp_command = None
    parent.acp_args = []
    return parent


def _child_snapshot(child: Any) -> dict[str, Any]:
    prompt = getattr(child, "ephemeral_system_prompt", None) or getattr(child, "system_prompt", "") or ""
    tools = getattr(child, "tools", None) or []
    return {
        "model": getattr(child, "model", None),
        "provider": getattr(child, "provider", None),
        "base_url": getattr(child, "base_url", None),
        "api_mode": getattr(child, "api_mode", None),
        "skip_context_files": getattr(child, "skip_context_files", None),
        "memory_enabled": getattr(child, "_memory_enabled", None),
        "user_profile_enabled": getattr(child, "_user_profile_enabled", None),
        "memory_manager_present": getattr(child, "_memory_manager", None) is not None,
        "enabled_toolsets": getattr(child, "enabled_toolsets", None),
        "valid_tool_count": len(getattr(child, "valid_tool_names", []) or []),
        "tool_schema_count": len(tools),
        "system_prompt_chars": len(prompt),
        "delegate_role": getattr(child, "_delegate_role", None),
        "delegate_depth": getattr(child, "_delegate_depth", None),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe delegated child routing and context minimization.")
    parser.add_argument("--live", action="store_true", help="Run a single live child turn after construction.")
    parser.add_argument("--toolsets", default="web", help="Comma-separated toolsets to request for the child.")
    args = parser.parse_args()

    full_cfg = load_config() or {}
    delegation_cfg = _load_config() or {}
    parent = _make_parent(full_cfg)
    resolved = _resolve_delegation_credentials(delegation_cfg, parent)
    toolsets = [item.strip() for item in args.toolsets.split(",") if item.strip()]

    child = _build_child_agent(
        task_index=0,
        goal="Probe delegated child routing",
        context="Return the minimum viable truth about child runtime state.",
        toolsets=toolsets,
        model=resolved.get("model"),
        max_iterations=1,
        task_count=1,
        parent_agent=parent,
        override_provider=resolved.get("provider"),
        override_base_url=resolved.get("base_url"),
        override_api_key=resolved.get("api_key"),
        override_api_mode=resolved.get("api_mode"),
        override_acp_command=resolved.get("command"),
        override_acp_args=resolved.get("args"),
        role="leaf",
    )
    try:
        payload: dict[str, Any] = {
            "parent": {
                "model": parent.model,
                "provider": parent.provider,
                "base_url": parent.base_url,
                "api_mode": parent.api_mode,
            },
            "delegation_config": {
                "model": delegation_cfg.get("model"),
                "provider": delegation_cfg.get("provider"),
                "base_url": delegation_cfg.get("base_url"),
                "reasoning_effort": delegation_cfg.get("reasoning_effort"),
                "max_concurrent_children": delegation_cfg.get("max_concurrent_children"),
                "max_spawn_depth": delegation_cfg.get("max_spawn_depth"),
            },
            "resolved_override": {
                "model": resolved.get("model"),
                "provider": resolved.get("provider"),
                "base_url": resolved.get("base_url"),
                "api_mode": resolved.get("api_mode"),
                "has_api_key": bool(resolved.get("api_key")),
                "acp_command": resolved.get("command"),
                "acp_args": resolved.get("args"),
            },
            "child": _child_snapshot(child),
        }
        if args.live:
            result = child.run_conversation("Reply with exactly OK.", task_id="delegate-route-probe")
            payload["live_result"] = {
                "completed": result.get("completed"),
                "interrupted": result.get("interrupted"),
                "api_calls": result.get("api_calls"),
                "final_response": (result.get("final_response") or "")[:200],
                "session_prompt_tokens": getattr(child, "session_prompt_tokens", None),
                "session_completion_tokens": getattr(child, "session_completion_tokens", None),
            }
            payload["child_after_live"] = _child_snapshot(child)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    finally:
        try:
            child.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
