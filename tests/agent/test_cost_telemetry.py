"""Tests for agent/cost_telemetry.py — cost/energy routing telemetry.

Covers:
  - energy_weight derivation from pricing (light < average < heavy, neutral
    fallback for unknown/local routes)
  - request_cost wrapper (cost + energy in one object)
  - daily_cost_summary roll-up read from the session DB
  - cost_routing_score gated OFF by default (inert), active when opted in
  - budget_status disabled by default, fires when daily_budget_usd > 0
"""

import time

import pytest

from shay_state import SessionDB
from agent.usage_pricing import CanonicalUsage
from agent import cost_telemetry as ct


@pytest.fixture()
def db(tmp_path):
    session_db = SessionDB(db_path=tmp_path / "test_cost.db")
    yield session_db
    session_db.close()


# --------------------------------------------------------------------------
# energy_weight
# --------------------------------------------------------------------------

def test_energy_weight_unknown_route_is_neutral():
    assert ct.energy_weight("totally-unknown-model", provider="local") == ct.NEUTRAL_ENERGY_WEIGHT


def test_energy_weight_light_model_below_average():
    # gpt-4.1-nano: (0.10 + 0.40)/2 = 0.25/M = 0.00025/1k → well under light mark.
    w = ct.energy_weight("gpt-4.1-nano", provider="openai")
    assert ct.NEUTRAL_ENERGY_WEIGHT > w >= ct._MIN_WEIGHT


def test_energy_weight_heavier_than_light():
    light = ct.energy_weight("gpt-4.1-nano", provider="openai")
    heavy = ct.energy_weight("claude-opus-4-7", provider="anthropic")
    assert heavy > light


def test_energy_weight_clamped_band():
    w = ct.energy_weight("claude-opus-4-7", provider="anthropic")
    assert ct._MIN_WEIGHT <= w <= ct._MAX_WEIGHT


# --------------------------------------------------------------------------
# request_cost
# --------------------------------------------------------------------------

def test_request_cost_known_model_has_amount_and_weight():
    usage = CanonicalUsage(input_tokens=1000, output_tokens=500)
    rc = ct.request_cost("claude-opus-4-7", usage, provider="anthropic")
    assert rc.model == "claude-opus-4-7"
    assert rc.amount_usd is not None and rc.amount_usd > 0
    assert rc.energy_weight > 0
    assert rc.total_tokens == 1500


def test_request_cost_unknown_model_amount_none_weight_neutral():
    usage = CanonicalUsage(input_tokens=1000, output_tokens=500)
    rc = ct.request_cost("mystery-model", usage, provider="local")
    assert rc.amount_usd is None
    assert rc.energy_weight == ct.NEUTRAL_ENERGY_WEIGHT


# --------------------------------------------------------------------------
# daily_cost_summary
# --------------------------------------------------------------------------

def _seed_session(db, sid, model, provider, started_at, cost):
    db.create_session(session_id=sid, source="cli", model=model)
    db._conn.execute(
        "UPDATE sessions SET started_at = ?, billing_provider = ?, "
        "estimated_cost_usd = ? WHERE id = ?",
        (started_at, provider, cost, sid),
    )
    db._conn.commit()


def test_daily_cost_summary_groups_by_model_and_provider(db):
    now = time.time()
    _seed_session(db, "s1", "anthropic/claude-opus-4-7", "anthropic", now, 0.50)
    _seed_session(db, "s2", "anthropic/claude-opus-4-7", "anthropic", now, 0.25)
    _seed_session(db, "s3", "openai/gpt-4.1-nano", "openrouter", now, 0.05)

    summary = ct.daily_cost_summary(db, days=7)
    assert summary["total_usd"] == pytest.approx(0.80)
    assert summary["by_model"]["claude-opus-4-7"] == pytest.approx(0.75)
    assert summary["by_model"]["gpt-4.1-nano"] == pytest.approx(0.05)
    assert summary["by_provider"]["anthropic"] == pytest.approx(0.75)
    assert summary["by_provider"]["openrouter"] == pytest.approx(0.05)
    # today's spend equals everything we seeded at `now`.
    assert summary["today_usd"] == pytest.approx(0.80)


def test_daily_cost_summary_ignores_unknown_cost_rows(db):
    now = time.time()
    _seed_session(db, "s1", "anthropic/claude-opus-4-7", "anthropic", now, 0.50)
    # null estimated cost — should contribute 0, not error.
    db.create_session(session_id="s2", source="cli", model="local/x")
    db._conn.execute("UPDATE sessions SET started_at = ? WHERE id = 's2'", (now,))
    db._conn.commit()
    summary = ct.daily_cost_summary(db, days=7)
    assert summary["total_usd"] == pytest.approx(0.50)


def test_daily_cost_summary_respects_window(db):
    now = time.time()
    _seed_session(db, "old", "anthropic/claude-opus-4-7", "anthropic", now - 30 * 86400, 9.0)
    _seed_session(db, "new", "anthropic/claude-opus-4-7", "anthropic", now, 1.0)
    summary = ct.daily_cost_summary(db, days=7)
    assert summary["total_usd"] == pytest.approx(1.0)


# --------------------------------------------------------------------------
# cost_routing_score (default OFF)
# --------------------------------------------------------------------------

def test_cost_routing_score_inert_by_default():
    # No config / disabled → unchanged quality score.
    assert ct.cost_routing_score(
        "claude-opus-4-7", quality_score=10.0, provider="anthropic", config={}
    ) == 10.0


def test_cost_routing_score_active_when_opted_in():
    cfg = {"routing": {"cost_aware": True}}
    light = ct.cost_routing_score(
        "gpt-4.1-nano", quality_score=10.0, provider="openai", config=cfg
    )
    heavy = ct.cost_routing_score(
        "claude-opus-4-7", quality_score=10.0, provider="anthropic", config=cfg
    )
    # Light model is boosted above its raw quality; heavy is not above light.
    assert light > heavy


def test_is_cost_aware_routing_enabled_reads_config():
    assert ct.is_cost_aware_routing_enabled({}) is False
    assert ct.is_cost_aware_routing_enabled({"routing": {"cost_aware": True}}) is True


# --------------------------------------------------------------------------
# budget_status
# --------------------------------------------------------------------------

def test_budget_status_disabled_by_default(db):
    status = ct.budget_status(db, config={})
    assert status["enabled"] is False
    assert status["over_budget"] is False


def test_budget_status_fires_when_over(db):
    now = time.time()
    _seed_session(db, "s1", "anthropic/claude-opus-4-7", "anthropic", now, 5.0)
    cfg = {"routing": {"daily_budget_usd": 1.0}}
    status = ct.budget_status(db, config=cfg)
    assert status["enabled"] is True
    assert status["spent_today_usd"] == pytest.approx(5.0)
    assert status["over_budget"] is True
    assert status["fraction"] == pytest.approx(5.0)


def test_budget_status_under_budget(db):
    now = time.time()
    _seed_session(db, "s1", "anthropic/claude-opus-4-7", "anthropic", now, 0.25)
    cfg = {"routing": {"daily_budget_usd": 1.0}}
    status = ct.budget_status(db, config=cfg)
    assert status["enabled"] is True
    assert status["over_budget"] is False
