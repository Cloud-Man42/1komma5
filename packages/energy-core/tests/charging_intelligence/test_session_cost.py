"""Tests for charging session cost resolution."""

from energy_core.vehicles.charging_intelligence.cost import CostSource, resolve_session_cost


def test_resolve_session_cost_chargefinder_per_kwh():
    result = resolve_session_cost(
        home_charging=False,
        actual_cost_sek=None,
        price_model="PER_KWH",
        price_value=4.5,
        energy_kwh=12.0,
        price_from_chargefinder=True,
    )
    assert result.cost_sek == 54.0
    assert result.cost_source == CostSource.CHARGEFINDER


def test_resolve_session_cost_operator_without_chargefinder_flag():
    result = resolve_session_cost(
        home_charging=False,
        actual_cost_sek=None,
        price_model="PER_KWH",
        price_value=3.0,
        energy_kwh=10.0,
    )
    assert result.cost_sek == 30.0
    assert result.cost_source == CostSource.OPERATOR


def test_resolve_session_cost_free_charging():
    result = resolve_session_cost(
        home_charging=False,
        actual_cost_sek=None,
        price_model="FREE",
        price_value=0.0,
        energy_kwh=12.0,
        price_from_chargefinder=True,
    )
    assert result.cost_sek == 0.0
    assert result.cost_source == CostSource.CONFIGURED_FREE_CHARGING


def test_resolve_session_cost_unknown_without_price():
    result = resolve_session_cost(
        home_charging=False,
        actual_cost_sek=None,
        price_model="UNKNOWN",
        price_value=None,
        energy_kwh=5.0,
    )
    assert result.cost_sek is None
    assert result.cost_source == CostSource.UNKNOWN
