"""Tests for energy reasoning diagnostics."""

from datetime import UTC, datetime, timedelta

from energy_core.charging.reasoning import build_energy_reasoning, parse_active_optimizations
from energy_core.db.models import EvChargerModel, SiteModel
from energy_core.energy.state import EnergyState
from energy_core.solar_forecast.types import SolarChargingPlan


def _charger(**kwargs) -> EvChargerModel:
    charger = EvChargerModel(
        id=1,
        site_id=1,
        name="Halo",
        manufacturer="ChargeAmps",
        model="Halo",
        control_source="chargeamp",
        bridge_enabled=True,
        chargeamp_charger_id="halo-1",
        charging_mode="SMART_CHARGE",
    )
    defaults = {
        "last_charging_reason": "cheap_now",
        "last_applied_current_a": 16.0,
        "last_vehicle_connected": True,
        "last_halo_connected": True,
        "externally_limited": False,
        "smart_charging_state": "CHARGING_STABLE",
    }
    defaults.update(kwargs)
    for key, value in defaults.items():
        setattr(charger, key, value)
    return charger


def _site() -> SiteModel:
    return SiteModel(
        id=1,
        slug="akarp",
        name="Åkarp",
        external_system_id="sys-1",
        main_fuse_a=25.0,
        safety_margin_a=2.0,
        timezone="Europe/Stockholm",
    )


def test_build_reasoning_marks_green_price_and_charge():
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    forecast = (
        (now, 0.20),
        (now + timedelta(hours=1), 0.55),
        (now + timedelta(hours=2), 0.60),
    )
    energy = EnergyState(
        timestamp=now,
        electricity_price_eur_kwh=0.20,
        price_forecast=forecast,
        pv_power_w=5000,
        grid_export_w=3000,
        ev_charge_from_grid_recommended=True,
    )
    snapshot = build_energy_reasoning(
        charger=_charger(),
        site=_site(),
        energy=energy,
        now=now,
    )
    assert snapshot.price_tier == "green"
    assert snapshot.price_would_charge is True
    assert snapshot.charging_active is True
    assert any("grönt" in step for step in snapshot.reasoning_steps)


def test_paused_mode_disables_charging_active():
    snapshot = build_energy_reasoning(
        charger=_charger(charging_mode="PAUSED", last_charging_reason="user_paused"),
        site=_site(),
    )
    assert snapshot.charging_active is False
    assert any("pausad" in step.lower() for step in snapshot.reasoning_steps)


def test_override_keeps_charging_active_even_when_paused():
    from datetime import timedelta

    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    snapshot = build_energy_reasoning(
        charger=_charger(
            charging_mode="PAUSED",
            override_until=now + timedelta(hours=4),
            last_charging_reason="override",
        ),
        site=_site(),
        now=now,
    )
    assert snapshot.charging_active is True
    assert any("override" in step.lower() for step in snapshot.reasoning_steps)


def test_bridge_disabled_explains_no_control():
    snapshot = build_energy_reasoning(
        charger=_charger(bridge_enabled=False),
        site=_site(),
    )
    assert snapshot.charging_active is False
    assert snapshot.reasoning_steps[0].startswith("EMIC-styrning är avstängd")


def test_parse_active_optimizations_filters_by_window():
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    items = [
        {
            "type": "EV_CHARGE_FROM_GRID",
            "start": (now - timedelta(minutes=5)).isoformat(),
            "end": (now + timedelta(minutes=5)).isoformat(),
        },
        {
            "type": "OTHER",
            "start": (now + timedelta(hours=2)).isoformat(),
            "end": (now + timedelta(hours=3)).isoformat(),
        },
    ]
    active = parse_active_optimizations(items, now=now)
    assert active == ("EV_CHARGE_FROM_GRID",)


def _plan(*, solar_first: bool) -> SolarChargingPlan:
    return SolarChargingPlan(
        expected_usable_solar_kwh=8.0,
        planning_solar_kwh=8.0,
        quality="HIGH",
        confidence=0.9,
        expected_solar_window_start=None,
        expected_solar_window_end=None,
        cheapest_grid_window=None,
        explanation_sv="Test",
        reason_code="solar_forecast_wait" if solar_first else "solar_forecast_grid_required",
        solar_first=solar_first,
    )


def test_solar_plan_included_in_steps():
    snapshot = build_energy_reasoning(
        charger=_charger(),
        site=_site(),
        solar_plan=_plan(solar_first=True),
    )
    assert snapshot.solar_plan_available is True
    assert snapshot.solar_first is True
    assert any("solel prioriteras" in step for step in snapshot.reasoning_steps)


def test_solar_plan_without_enough_solar_explains_grid_charging():
    snapshot = build_energy_reasoning(
        charger=_charger(),
        site=_site(),
        solar_plan=_plan(solar_first=False),
    )
    assert snapshot.solar_first is False
    assert any("för lite solel" in step.lower() for step in snapshot.reasoning_steps)


def test_reasoning_reports_no_solar_plan_without_deadline():
    snapshot = build_energy_reasoning(charger=_charger(), site=_site())
    assert snapshot.solar_plan_available is False
    assert snapshot.solar_first is False
    assert not any("Solplan" in step for step in snapshot.reasoning_steps)
