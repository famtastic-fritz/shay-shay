"""Pure, redaction-safe readiness assessment for the Telegram gateway path.

Configuration only proves that a bot token exists. A usable Telegram path also
requires the adapter package and exactly one active gateway runtime. This module
keeps those layers explicit for the status and doctor surfaces without
performing network I/O or reading secret values.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util


def telegram_dependency_available() -> bool | None:
    """Inspect the adapter without importing it; a failed probe is not absence."""
    try:
        return importlib.util.find_spec("telegram") is not None
    except (ImportError, ValueError, OSError):
        return None


@dataclass(frozen=True)
class TelegramReadiness:
    """Readiness of the local prerequisites for Telegram delivery.

    ``ready`` means configuration, the adapter dependency, and a local gateway
    process are all present. It intentionally does *not* claim an end-to-end
    delivery test has happened.
    """

    configured: bool
    dependency_available: bool | None
    gateway_running: bool | None
    gateway_process_count: int | None

    @property
    def ready(self) -> bool:
        return (
            self.configured
            and self.dependency_available is True
            and self.gateway_running is True
            and self.gateway_process_count == 1
        )

    @property
    def status_label(self) -> str:
        if not self.configured:
            return "not configured"
        if self.dependency_available is None:
            return "configured — degraded: python-telegram-bot availability unverified"
        if not self.dependency_available:
            return "configured — degraded: python-telegram-bot missing"
        if self.gateway_running is False:
            return "configured — degraded: gateway stopped"
        if self.gateway_running is None:
            return "configured — degraded: gateway status unavailable"
        if self.gateway_process_count is None:
            return "configured — degraded: gateway process count unavailable"
        if self.gateway_process_count == 0:
            return "configured — degraded: gateway process not found"
        if self.gateway_process_count > 1:
            return "configured — degraded: duplicate gateway processes"
        return "configured — runtime ready (delivery path unverified)"

    @property
    def doctor_detail(self) -> str:
        if not self.configured:
            return "not configured"
        if self.dependency_available is None:
            return "python-telegram-bot availability unverified"
        if not self.dependency_available:
            return "python-telegram-bot missing"
        if self.gateway_running is False:
            return "gateway stopped"
        if self.gateway_running is None:
            return "gateway status unavailable"
        if self.gateway_process_count is None:
            return "gateway process count unavailable"
        if self.gateway_process_count == 0:
            return "gateway process not found"
        if self.gateway_process_count > 1:
            return "duplicate gateway processes active; Telegram polling requires one owner"
        return "adapter installed and exactly one gateway process running; delivery path unverified"


def assess_telegram_readiness(
    *,
    configured: bool,
    dependency_available: bool | None,
    gateway_running: bool | None,
    gateway_process_count: int | None = None,
) -> TelegramReadiness:
    """Build a truthful Telegram readiness verdict from local signals only."""

    return TelegramReadiness(
        configured=bool(configured),
        dependency_available=None if dependency_available is None else bool(dependency_available),
        gateway_running=gateway_running,
        gateway_process_count=gateway_process_count,
    )
