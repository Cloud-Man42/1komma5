"""Tests for energy state decision text."""

from energy_core.energy_state.decision_text import EnergyDecisionTextService
from energy_core.energy_state.models import (
    BatteryState,
    DataQuality,
    EnergySiteSnapshot,
    EvState,
    SystemStatus,
)


def _snapshot(**overrides) -> EnergySiteSnapshot:
    base = dict(
        site_id=1,
        site_slug="akarp",
        site_name="Åkarp",
        timezone="Europe/Stockholm",
        solar_power_kw=5.4,
        solar_energy_today_kwh=21.6,
        house_power_kw=1.6,
        house_energy_today_kwh=11.8,
        grid_power_kw=-1.5,
        grid_import_power_kw=0.0,
        grid_export_power_kw=1.5,
        grid_import_today_kwh=0.0,
        grid_export_today_kwh=3.0,
        battery_soc_percent=74.0,
        battery_power_kw=2.3,
        battery_state=BatteryState.CHARGING,
        battery_state_text_sv="Laddar",
        battery_energy_charged_today_kwh=4.0,
        battery_energy_discharged_today_kwh=0.0,
        ev_state=EvState.WAITING,
        ev_state_text_sv="Väntar",
        ev_power_kw=0.0,
        ev_energy_today_kwh=None,
        current_electricity_price=1.2,
        current_electricity_price_including_fees=1.5,
        saved_today_sek=63.0,
        saved_month_sek=1187.0,
        economic_data_quality=DataQuality.MEASURED,
        self_consumption_percent=80.0,
        self_sufficiency_percent=60.0,
        operating_mode="SMART_CHARGE",
        decision_text="",
        smart_charging_mode=None,
        smart_charging_state=None,
        smart_charging_decision_text=None,
        system_status=SystemStatus.ONLINE,
        updated_at=None,
        data_age_seconds=9,
        is_stale=False,
    )
    base.update(overrides)
    return EnergySiteSnapshot(**base)


def test_decision_text_battery_charging_from_solar():
    text = EnergyDecisionTextService.build(
        _snapshot(
            battery_state=BatteryState.CHARGING,
            battery_power_kw=2.3,
            ev_state=EvState.UNAVAILABLE,
        )
    )
    assert text == "Laddar batteriet med solel"


def test_decision_text_grid_export():
    text = EnergyDecisionTextService.build(
        _snapshot(
            battery_state=BatteryState.IDLE,
            battery_power_kw=0.0,
            grid_export_power_kw=1.5,
            grid_power_kw=-1.5,
            ev_state=EvState.UNAVAILABLE,
        )
    )
    assert text == "Säljer solelöverskott"


def test_decision_text_offline():
    text = EnergyDecisionTextService.build(
        _snapshot(system_status=SystemStatus.OFFLINE, solar_power_kw=None)
    )
    assert "Ingen färsk mätdata" in text
