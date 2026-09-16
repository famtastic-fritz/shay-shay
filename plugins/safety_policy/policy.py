"""Deterministic plugin-first typed effect policy.

The policy is conservative and opt-in: reads pass, local writes ask, and
sensitive/external/spend/production effects deny unless an explicit bounded
rule is provided. It never grants a blanket approval.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from .ledger import DecisionLedger

EFFECT_READ = "read"
EFFECT_WRITE = "local_reversible_write"
EFFECT_DESTRUCTIVE = "destructive_local_write"
EFFECT_CREDENTIAL = "credential_account"
EFFECT_EXTERNAL = "external_message_publish"
EFFECT_PAYMENT = "payment_spend"
EFFECT_PRODUCTION = "production"

_READ_TOOLS = {"read_file", "search_files", "session_search", "web_search", "web_extract", "skill_view", "skills_list"}
_WRITE_TOOLS = {"write_file", "patch"}
_DESTRUCTIVE_TOOLS = {"delete_file", "terminal"}
_SENSITIVE_NAMES = {"password", "token", "secret", "api_key", "credential"}


def classify_effect(tool_name: str, args: dict) -> str:
    requested = args.get("effect_class")
    if requested in {EFFECT_READ, EFFECT_WRITE, EFFECT_DESTRUCTIVE, EFFECT_CREDENTIAL, EFFECT_EXTERNAL, EFFECT_PAYMENT, EFFECT_PRODUCTION}:
        return requested
    name = str(tool_name or "")
    if name in _READ_TOOLS:
        return EFFECT_READ
    if name in _WRITE_TOOLS:
        return EFFECT_WRITE
    if name in _DESTRUCTIVE_TOOLS:
        command = str(args.get("command", "")).lower()
        return EFFECT_DESTRUCTIVE if name == "delete_file" or any(x in command for x in ("rm ", "rmdir ", "truncate ", "shred ")) else EFFECT_WRITE
    lowered = " ".join(str(k).lower() for k in args)
    if any(word in name.lower() or word in lowered for word in _SENSITIVE_NAMES):
        return EFFECT_CREDENTIAL
    if any(word in name.lower() for word in ("pay", "purchase", "charge", "spend")):
        return EFFECT_PAYMENT
    if any(word in name.lower() for word in ("send", "publish", "post", "message")):
        return EFFECT_EXTERNAL
    if any(word in name.lower() for word in ("deploy", "production", "release")):
        return EFFECT_PRODUCTION
    return EFFECT_READ


def _effect_id(tool_call_id: str, tool_name: str, args: dict) -> str:
    raw = f"{tool_call_id or ''}|{tool_name}|{repr(sorted(args.items()))}"
    return "effect_" + hashlib.sha256(raw.encode()).hexdigest()[:32]


def _path_allowed(args: dict) -> tuple[bool, str]:
    raw = args.get("path")
    roots = args.get("allowed_roots")
    if not raw or not roots:
        return True, ""
    if not isinstance(raw, str) or not isinstance(roots, (list, tuple)):
        return False, "path_policy_invalid"
    try:
        target = Path(raw).expanduser().resolve(strict=False)
        allowed = [Path(root).expanduser().resolve(strict=False) for root in roots if isinstance(root, str)]
    except (OSError, RuntimeError, ValueError):
        return False, "path_resolution_failed"
    if not any(target == root or root in target.parents for root in allowed):
        return False, "path_outside_allowed_root"
    return True, ""


class SafetyPolicy:
    def __init__(self, ledger: DecisionLedger | None = None):
        self.ledger = ledger or DecisionLedger()

    def pre_tool_call(self, *, tool_name, args=None, task_id="", session_id="", tool_call_id="", client="unknown", **_):
        args = args if isinstance(args, dict) else {}
        # Preserve the host hardline floor at the typed seam. Containerized
        # backends remain explicit isolation exceptions, as in terminal_tool.
        if tool_name == "terminal" and args.get("env_type") not in {"docker", "singularity", "modal", "daytona", "vercel_sandbox"}:
            try:
                from tools.approval import detect_hardline_command
                hardline, description = detect_hardline_command(str(args.get("command", "")))
            except Exception:
                hardline, description = False, None
            if hardline:
                return self._decision("block", "hardline.command", EFFECT_DESTRUCTIVE, _effect_id(tool_call_id, tool_name, args), str(description or "hardline"), task_id, session_id, tool_call_id, client)
        effect_class = classify_effect(tool_name, args)
        effect_id = _effect_id(tool_call_id, tool_name, args)
        rule_id = f"effect.{effect_class}"
        allowed, reason = _path_allowed(args)
        if not allowed:
            return self._decision("block", rule_id, effect_class, effect_id, reason, task_id, session_id, tool_call_id, client)
        if effect_class in {EFFECT_CREDENTIAL, EFFECT_EXTERNAL, EFFECT_PAYMENT, EFFECT_PRODUCTION, EFFECT_DESTRUCTIVE}:
            # A spend-bearing request must carry a provider-enforced maximum;
            # an estimate or absent maximum is never treated as zero cost.
            if effect_class == EFFECT_PAYMENT and not self._has_authoritative_cost_ceiling(args):
                reason = "cost_unknown"
            else:
                reason = "sensitive_or_irreversible"
            return self._decision("block", rule_id, effect_class, effect_id, reason, task_id, session_id, tool_call_id, client)
        if effect_class == EFFECT_WRITE:
            return self._decision("request_approval", rule_id, effect_class, effect_id, "local_write", task_id, session_id, tool_call_id, client)
        return self._decision("allow", rule_id, effect_class, effect_id, "read_only", task_id, session_id, tool_call_id, client)

    @staticmethod
    def _has_authoritative_cost_ceiling(args: dict) -> bool:
        """Accept only an explicit non-negative provider-enforced maximum."""
        value = args.get("provider_max_usd")
        if value is None:
            value = args.get("max_cost_usd")
        try:
            return float(value) >= 0 and bool(args.get("cost_enforced_by_provider", False))
        except (TypeError, ValueError):
            return False

    def _decision(self, action, rule_id, effect_class, effect_id, reason, task_id, session_id, tool_call_id, client):
        outcome = "approval_required" if action == "request_approval" else ("allowed" if action == "allow" else "denied")
        self.ledger.append(rule_id=rule_id, client=client, session_id=session_id, task_id=task_id, tool_call_id=tool_call_id, effect_id=effect_id, effect_class=effect_class, outcome=outcome, reason=reason)
        return {"action": action, "rule_id": rule_id, "effect_class": effect_class, "effect_id": effect_id, "reason": reason, "message": f"{reason}: {effect_class}"}
