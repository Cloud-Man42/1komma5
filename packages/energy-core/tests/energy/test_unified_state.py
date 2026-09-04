"""Tests for UnifiedEnergyState and adapters."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.energy.state import EnergyState
from energy_core.energy.unified import DataFreshness
from energy_core.energy.unified_adapters import (
    from_energy_state,
    from_site_snapshot,
    from_snapshot_payload,
)
from energy_core.energy_state.models import (
    BatteryState,
    DataQuality,
    EnergySiteSnapshot,
    EvState,
    SmartChargingMode,
    SmartChargingState,
    SystemStatus,
)


def _minimal_site_snapshot(**overrides) -> EnergySiteSnapshot:
    base = dict(
        site_id=1,
        site_slug="akarp",
        site_name="Åkarp",
        timezone="Europe/Stockholm",
        solar_power_kw=3.5,
        solar_energy_today_kwh=12.0,
        house_power_kw=1.2,
        house_energy_today_kwh=8.0,
        grid_power_kw=0.5,
        grid_import_power_kw=0.5,
        grid_export_power_kw=0.0,
        grid_import_today_kwh=2.0,
        grid_export_today_kwh=0.0,
        battery_soc_percent=80.0,
        battery_power_kw=-1.5,
        battery_state=BatteryState.DISCHARGING,
        battery_state_text_sv="Urladdar",
        battery_energy_charged_today_kwh=1.0,
        battery_energy_discharged_today_kwh=2.0,
        ev_state=EvState.CHARGING,
        ev_state_text_sv="Laddar",
        ev_power_kw=7.4,
        ev_energy_today_kwh=5.0,
        current_electricity_price=0.12,
        current_electricity_price_including_fees=1.45,
        saved_today_sek=10.0,
        saved_month_sek=100.0,
        economic_data_quality=DataQuality.CALCULATED,
        self_consumption_percent=70.0,
        self_sufficiency_percent=60.0,
        operating_mode=None,
        decision_text="Test",
        smart_charging_mode=SmartChargingMode.SMART,
        smart_charging_state=SmartChargingState.SMART,
        smart_charging_decision_text="Smart",
        system_status=SystemStatus.ONLINE,
        updated_at=datetime(2026, 9, 3, 12, 0, tzinfo=UTC),
        data_age_seconds=30,
        is_stale=False,
    )
    base.update(overrides)
    return EnergySiteSnapshot(**base)


def test_from_energy_state_maps_power_and_ev():
    state = EnergyState(
        timestamp=datetime(2026, 9, 3, 12, 0, tzinfo=UTC),
        pv_power_w=3500.0,
        grid_import_w=500.0,
        home_consumption_w=1200.0,
        battery_charge_power_w=0.0,
        battery_discharge_power_w=1500.0,
        battery_soc=80.0,
        ev_actual_power_w=7400.0,
        ev_soc=55.0,
        target_soc=80.0,
        import_price_sek_kwh=1.45,
        electricity_price_eur_kwh=0.12,
        data_age_seconds=15.0,
    )
    unified = from_energy_state(state, site_id=1, site_slug="akarp")

    assert unified.site_id == 1
    assert unified.site_slug == "akarp"
    assert unified.solar.production_kw == 3.5
    assert unified.grid.import_kw == 0.5
    assert unified.house.consumption_kw == 1.2
    assert unified.battery.soc_percent == 80.0
    assert unified.battery.discharge_kw == 1.5
    assert unified.battery.state == "discharging"
    assert unified.ev.charging is True
    assert unified.ev.power_kw == 7.4
    assert unified.ev.soc_percent == 55.0
    assert unified.prices.import_price_sek_kwh == 1.45


def test_from_energy_state_marks_stale():
    state = EnergyState(
        timestamp=datetime(2026, 9, 3, 12, 0, tzinfo=UTC),
        stale=True,
        data_age_seconds=600.0,
    )
    unified = from_energy_state(state, site_id=1, site_slug="akarp")
    assert unified.stale is True
    assert unified.data_freshness == DataFreshness.STALE


def test_from_site_snapshot_maps_sections():
    snapshot = _minimal_site_snapshot()
    unified = from_site_snapshot(snapshot)

    assert unified.site_id == 1
    assert unified.solar.production_kw == 3.5
    assert unified.solar.today_kwh == 12.0
    assert unified.ev.charging is True
    assert unified.ev.connected is True
    assert unified.battery.state == "discharging"
    assert unified.battery.discharge_kw == 1.5
    assert unified.prices.import_price_eur_kwh == 0.12


def test_from_site_snapshot_stale_flag():
    snapshot = _minimal_site_snapshot(is_stale=True, data_age_seconds=900)
    unified = from_site_snapshot(snapshot)
    assert unified.stale is True
    assert unified.data_freshness == DataFreshness.STALE


def test_from_snapshot_payload_maps_live_and_today():
    payload = {
        "site": {"slug": "akarp", "name": "Åkarp", "timezone": "Europe/Stockholm"},
        "generated_at": "2026-09-03T12:22:02.573511+00:00",
        "age_seconds": 10,
        "freshness": "LIVE",
        "source_status": {"heartbeat": "db_only", "forecast": "db_only"},
        "live": {
            "solar_production_w": 4200.0,
            "consumption_w": 1500.0,
            "grid_import_w": 200.0,
            "grid_export_w": 0.0,
            "battery_soc_pct": 75.0,
            "battery_power_w": 1000.0,
        },
        "today": {
            "produced_kwh": 15.0,
            "consumed_kwh": 10.0,
            "imported_kwh": 3.0,
            "exported_kwh": 1.0,
        },
        "solar": {
            "expected_today_kwh": 20.0,
            "remaining_kwh": 5.0,
            "confidence_pct": 85.0,
        },
        "economy": {"current_eur_kwh": 0.11, "tier": "normal"},
        "ev": {"available": True, "charging": True, "power_w": 11000.0},
    }
    unified = from_snapshot_payload(payload)

    assert unified.site_slug == "akarp"
    assert unified.data_freshness == DataFreshness.LIVE
    assert unified.solar.production_kw == 4.2
    assert unified.solar.today_kwh == 15.0
    assert unified.solar.expected_today_kwh == 20.0
    assert unified.grid.import_kw == 0.2
    assert unified.house.consumption_kw == 1.5
    assert unified.battery.charge_kw == 1.0
    assert unified.ev.charging is True
    assert unified.ev.power_kw == 11.0
    assert unified.prices.current_tier == "normal"
    assert unified.health.heartbeat.status.value == "ok"


def test_from_snapshot_payload_degraded_freshness():
    payload = {
        "site": {"slug": "akarp"},
        "generated_at": "2026-09-03T10:00:00+00:00",
        "freshness": "DEGRADED",
        "age_seconds": 7200,
        "live": {},
        "today": {},
        "solar": {},
        "economy": {},
        "ev": {},
    }
    unified = from_snapshot_payload(payload)
    assert unified.data_freshness == DataFreshness.DEGRADED
    assert unified.stale is True
