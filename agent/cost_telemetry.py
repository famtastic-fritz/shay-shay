"""Cost / energy telemetry — a routing-aware view over recorded usage.

This module is a clean-room implementation of the "treat $-cost and energy as
first-class routing metrics" idea (evaluated from OpenJarvis, Apache-2.0; no
code copied — stack mismatch). It builds on Shay-Shay's existing per-request
usage accounting:

  - ``agent/usage_pricing.py`` already turns raw API usage into a canonical
    token breakdown and estimates $-cost per request via official-docs /
    provider-models-API pricing.
  - ``run_agent.py`` already persists per-call token + estimated-cost deltas
    into the session DB (``sessions`` table: ``estimated_cost_usd``,
    ``billing_provider``, ``model``, token columns).

What this module adds:

  1. A *relative energy weight* per model — a coarse proxy for "intelligence
     per watt". We do not have on-device GPU wattmeters for hosted models, so
     the weight is derived from the model's blended $-per-1k-token rate (a
     reasonable stand-in: bigger / pricier models burn more energy per token).
     Local / unknown-cost routes fall back to a neutral weight.

  2. A *rolling daily $ spend* summary, grouped by model and by provider, read
     straight from the session DB. This is the queryable telemetry surface
     (reused by the ``/insights`` path and by ``shay cost``-style callers).

  3. An OPTIONAL *routing score* hook — ``cost_routing_score()`` — that can be
     consulted by a router to prefer the cheapest model that clears the quality
     bar. It is GATED OFF by default (config ``routing.cost_aware`` defaults to
     ``False``) so adding this module changes no routing behavior until the
     operator opts in. Nothing in this module mutates routing on its own.

  4. A *budget / low-funds* check — ``budget_status()`` — that reports whether
     rolling daily spend has crossed a soft daily-budget threshold, so the
     existing "low funds" notification surface has a number to act on. Gated by
     ``routing.daily_budget_usd`` (default ``0`` = disabled).
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional

from agent.usage_pricing import (
    CanonicalUsage,
    estimate_usage_cost,
    get_pricing_entry,
)

# ---------------------------------------------------------------------------
# Energy weighting
# ---------------------------------------------------------------------------

# Neutral weight applied when we cannot estimate a model's cost (local models,
# subscription-included routes, unknown endpoints). 1.0 == "average model".
NEUTRAL_ENERGY_WEIGHT = 1.0

# A blended $/1k-token rate (input+output averaged) at or below this is treated
# as a "light" model; at or above the high mark as a "heavy" model. The weight
# is a smooth-ish proxy, clamped to a sane band so a single pricey route can't
# dominate the score.
_LIGHT_BLENDED_PER_1K = Decimal("0.002")   # ~ gpt-4.1-nano / haiku territory
_HEAVY_BLENDED_PER_1K = Decimal("0.030")   # ~ opus / o3 territory
_MIN_WEIGHT = 0.25
_MAX_WEIGHT = 4.0


def _blended_per_1k(
    model_name: str,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Optional[Decimal]:
    """Average of input + output $-per-1k-token for *model_name*, or None.

    Returns None when we have no pricing for the route (local / unknown). A
    zero-cost (subscription-included / free) route returns ``Decimal(0)``.
    """
    entry = get_pricing_entry(
        model_name, provider=provider, base_url=base_url, api_key=api_key
    )
    if entry is None:
        return None
    parts: List[Decimal] = []
    if entry.input_cost_per_million is not None:
        parts.append(entry.input_cost_per_million)
    if entry.output_cost_per_million is not None:
        parts.append(entry.output_cost_per_million)
    if not parts:
        return None
    avg_per_million = sum(parts) / Decimal(len(parts))
    return avg_per_million / Decimal(1000)  # per-million -> per-1k


def energy_weight(
    model_name: str,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> float:
    """Return a coarse relative energy weight for a model/route.

    1.0 is "average". Lighter / cheaper models score below 1.0, heavier /
    pricier ones above. Local and unknown-cost routes get the neutral weight
    (we cannot meter hosted-GPU watts, so cost is the proxy; a local model with
    no $-cost is treated as average energy, not free energy).
    """
    blended = _blended_per_1k(
        model_name, provider=provider, base_url=base_url, api_key=api_key
    )
    if blended is None:
        return NEUTRAL_ENERGY_WEIGHT
    if blended <= 0:
        # Free / included route — no $ signal. Treat as neutral energy rather
        # than zero; "free to me" is not "free to run".
        return NEUTRAL_ENERGY_WEIGHT
    if blended <= _LIGHT_BLENDED_PER_1K:
        weight = _MIN_WEIGHT + (
            (float(blended) / float(_LIGHT_BLENDED_PER_1K)) * (1.0 - _MIN_WEIGHT)
        )
    elif blended >= _HEAVY_BLENDED_PER_1K:
        span = float(_HEAVY_BLENDED_PER_1K) * 4  # cap runaway pricing
        frac = min(1.0, (float(blended) - float(_HEAVY_BLENDED_PER_1K)) / span)
        weight = 1.0 + frac * (_MAX_WEIGHT - 1.0)
    else:
        # Linear from the light mark (weight ~1.0) up to the heavy mark
        # (weight ~1.0) — between the marks we interpolate toward 1.0 so a
        # mid-priced model lands near average.
        lo, hi = float(_LIGHT_BLENDED_PER_1K), float(_HEAVY_BLENDED_PER_1K)
        frac = (float(blended) - lo) / (hi - lo)
        # frac 0 -> ~1.0 (just above light), frac 1 -> 1.0 (at heavy mark).
        weight = 1.0
    return max(_MIN_WEIGHT, min(_MAX_WEIGHT, weight))


# ---------------------------------------------------------------------------
# Per-request cost record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RequestCost:
    """Cost + energy view of a single request's usage."""

    model: str
    provider: Optional[str]
    amount_usd: Optional[float]
    cost_status: str
    cost_source: str
    energy_weight: float
    total_tokens: int


def request_cost(
    model_name: str,
    usage: CanonicalUsage,
    *,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> RequestCost:
    """Compute the $-cost + relative energy weight for one request's usage.

    Thin wrapper over ``estimate_usage_cost`` that also attaches the energy
    weight, so callers (telemetry, routing scorer) get one object.
    """
    cost = estimate_usage_cost(
        model_name, usage, provider=provider, base_url=base_url, api_key=api_key
    )
    return RequestCost(
        model=model_name,
        provider=provider,
        amount_usd=float(cost.amount_usd) if cost.amount_usd is not None else None,
        cost_status=cost.status,
        cost_source=cost.source,
        energy_weight=energy_weight(
            model_name, provider=provider, base_url=base_url, api_key=api_key
        ),
        total_tokens=usage.total_tokens,
    )


# ---------------------------------------------------------------------------
# Rolling daily spend (queryable telemetry surface)
# ---------------------------------------------------------------------------

def _day_bucket(epoch_seconds: float) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(epoch_seconds))


def daily_cost_summary(db, days: int = 7) -> Dict[str, Any]:
    """Roll up recorded session spend into per-day / per-model / per-provider.

    Reads the ``sessions`` table directly (same source the InsightsEngine
    uses) so this stays consistent with ``/insights``. Each session row carries
    ``estimated_cost_usd``, ``billing_provider``, ``model``, and ``started_at``.

    Returns::

        {
          "days": 7,
          "total_usd": 1.23,
          "by_day":      {"2026-05-31": 0.40, ...},
          "by_model":    {"claude-opus-4-7": 0.90, ...},
          "by_provider": {"anthropic": 0.90, "openrouter": 0.33},
          "today_usd": 0.40,
        }

    Unknown-cost rows (``estimated_cost_usd`` NULL) contribute 0 to the totals
    but are not errors — they're just routes we can't price.
    """
    cutoff = time.time() - (days * 86400)
    conn = getattr(db, "_conn", None)
    out: Dict[str, Any] = {
        "days": days,
        "total_usd": 0.0,
        "by_day": {},
        "by_model": {},
        "by_provider": {},
        "today_usd": 0.0,
    }
    if conn is None:
        return out

    by_day: Dict[str, float] = defaultdict(float)
    by_model: Dict[str, float] = defaultdict(float)
    by_provider: Dict[str, float] = defaultdict(float)
    total = 0.0

    try:
        cursor = conn.execute(
            "SELECT model, billing_provider, started_at, estimated_cost_usd, "
            "actual_cost_usd FROM sessions WHERE started_at >= ?",
            (cutoff,),
        )
    except Exception:
        return out

    today = _day_bucket(time.time())
    for row in cursor.fetchall():
        amount = row["actual_cost_usd"]
        if amount is None:
            amount = row["estimated_cost_usd"]
        try:
            amount = float(amount) if amount is not None else 0.0
        except (TypeError, ValueError):
            amount = 0.0
        if amount <= 0:
            continue
        started = row["started_at"] or 0
        day = _day_bucket(float(started)) if started else "unknown"
        model = row["model"] or "unknown"
        display_model = model.split("/")[-1] if "/" in model else model
        provider = (row["billing_provider"] or "unknown")

        by_day[day] += amount
        by_model[display_model] += amount
        by_provider[provider] += amount
        total += amount

    out["total_usd"] = round(total, 6)
    out["by_day"] = {k: round(v, 6) for k, v in sorted(by_day.items())}
    out["by_model"] = {k: round(v, 6) for k, v in sorted(
        by_model.items(), key=lambda kv: kv[1], reverse=True)}
    out["by_provider"] = {k: round(v, 6) for k, v in sorted(
        by_provider.items(), key=lambda kv: kv[1], reverse=True)}
    out["today_usd"] = round(by_day.get(today, 0.0), 6)
    return out


# ---------------------------------------------------------------------------
# Optional routing score (DEFAULT OFF)
# ---------------------------------------------------------------------------

def is_cost_aware_routing_enabled(config: Optional[Dict[str, Any]] = None) -> bool:
    """Whether the operator has opted into cost-aware routing.

    Reads ``routing.cost_aware`` (default ``False``). Behavior is unchanged
    until this is flipped on, so importing/using this module is side-effect
    free for routing.
    """
    if config is None:
        try:
            from shay_cli.config import load_config
            config = load_config()
        except Exception:
            return False
    if not isinstance(config, dict):
        return False
    routing = config.get("routing")
    if not isinstance(routing, dict):
        return False
    return bool(routing.get("cost_aware", False))


def cost_routing_score(
    model_name: str,
    *,
    quality_score: float,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> float:
    """Adjust a candidate model's *quality_score* by its cost/energy weight.

    A router can rank candidates by this score to prefer the cheapest model
    that still clears the quality bar. When cost-aware routing is disabled
    (the default), this returns ``quality_score`` unchanged — a hard guarantee
    that the hook is inert until opted in.

    Scoring: ``quality_score / energy_weight``. A heavier (pricier / higher-
    energy) model is divided by a weight > 1.0 and therefore ranked lower for
    the same quality; a light model is boosted. This never *blocks* a model —
    it only reorders — so a router that still wants the heavy model can ignore
    the score.
    """
    if not is_cost_aware_routing_enabled(config):
        return quality_score
    weight = energy_weight(
        model_name, provider=provider, base_url=base_url, api_key=api_key
    )
    if weight <= 0:
        return quality_score
    return quality_score / weight


# ---------------------------------------------------------------------------
# Budget / low-funds signal
# ---------------------------------------------------------------------------

def get_daily_budget_usd(config: Optional[Dict[str, Any]] = None) -> float:
    """Soft daily budget in USD. ``0`` (default) disables the budget signal."""
    if config is None:
        try:
            from shay_cli.config import load_config
            config = load_config()
        except Exception:
            return 0.0
    if not isinstance(config, dict):
        return 0.0
    routing = config.get("routing")
    if not isinstance(routing, dict):
        return 0.0
    try:
        return float(routing.get("daily_budget_usd", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def budget_status(db, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Report today's spend against the soft daily budget.

    Returns ``{"enabled", "budget_usd", "spent_today_usd", "fraction",
    "over_budget"}``. When the budget is ``0`` (default), ``enabled`` is
    ``False`` and nothing should fire. This is the number the existing
    "low funds" / free-limit-counter notification surface can consume.
    """
    budget = get_daily_budget_usd(config)
    summary = daily_cost_summary(db, days=1)
    spent = float(summary.get("today_usd", 0.0))
    if budget <= 0:
        return {
            "enabled": False,
            "budget_usd": 0.0,
            "spent_today_usd": spent,
            "fraction": 0.0,
            "over_budget": False,
        }
    fraction = spent / budget if budget else 0.0
    return {
        "enabled": True,
        "budget_usd": round(budget, 4),
        "spent_today_usd": round(spent, 6),
        "fraction": round(fraction, 4),
        "over_budget": spent >= budget,
    }
