"""Bundled, opt-in typed safety policy plugin."""

from .policy import SafetyPolicy


def register(ctx):
    policy = SafetyPolicy()
    ctx.register_hook("pre_tool_call", policy.pre_tool_call)
