"""Tests for EV flexible load adapter."""

from datetime import UTC, datetime

from energy_core.db.models import EvChargerModel, SiteModel
from energy_core.flexible_load.ev_load import build_ev_orchestrated_load


def test_build_ev_load_requires_smart_mode_and_vehicle():
    now = datetime(2026, 8, 26, 8, 0, tzinfo=UTC)
    site = SiteModel(
        id=1,
        slug="akarp",
        name="Åkarp",
        timezone="Europe/Stockholm",
        fallback_purchase_price_sek_kwh=2.0,
        export_compensation_sek_kwh=0.8,
    )
    charger = EvChargerModel(
        id=7,
        site_id=1,
        name="Halo",
        manufacturer="ChargeAmps",
        model="Halo",
        bridge_enabled=True,
        charging_mode="SMART_CHARGE",
        last_vehicle_connected=True,
        max_current_a=16,
        phases=3,
        nominal_voltage_v=230,
        load_priority=45,
    )

    spec = build_ev_orchestrated_load(charger, site, now=now)
    assert spec is not None
    assert spec.load.load_id == "ev_charger_7"
    assert spec.load.priority == 45

    charger.charging_mode = "QUICK"
    assert build_ev_orchestrated_load(charger, site, now=now) is None

    charger.charging_mode = "SMART_CHARGE"
    charger.last_vehicle_connected = False
    assert build_ev_orchestrated_load(charger, site, now=now) is None
