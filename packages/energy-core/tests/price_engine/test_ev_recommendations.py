"""Tests for EV smart-charging window recommendations."""

from datetime import UTC, datetime, timedelta

from energy_core.db.models import EvChargerModel, SiteModel
from energy_core.price_engine.ev_recommendations import (
    build_ev_recommendations,
    find_cheapest_charge_window,
)
from energy_core.price_engine.types import (
    Currency,
    PriceArea,
    PricePeriod,
    PriceQuality,
    PriceSource,
)


def _period(start: datetime, import_price: float) -> PricePeriod:
    return PricePeriod(
        period_start=start,
        period_end=start + timedelta(minutes=15),
        site_id=1,
        price_area=PriceArea.SE4,
        currency=Currency.SEK,
        market_price_sek_kwh=import_price * 0.3,
        import_price_sek_kwh=import_price,
        export_price_sek_kwh=0.39,
        source=PriceSource.HEARTBEAT,
        quality=PriceQuality.REAL,
        is_estimated=False,
    )


def test_find_cheapest_charge_window():
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    horizon = tuple(_period(now + timedelta(minutes=15 * i), price) for i, price in enumerate(
        [2.0, 1.9, 1.8, 0.6, 0.55, 0.58, 0.62, 1.5]
    ))
    window = find_cheapest_charge_window(horizon, now=now, window_periods=4)
    assert window is not None
    assert window[2] == 0.5875


def test_build_ev_recommendations_requires_spread_and_connected_charger():
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
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
        max_current_a=16.0,
        phases=3,
        nominal_voltage_v=230.0,
    )
    horizon = tuple(
        _period(now + timedelta(minutes=15 * (i + 1)), price)
        for i, price in enumerate([2.0, 1.9, 1.8, 0.6, 0.55, 0.58, 0.62, 1.5])
    )

    recs = build_ev_recommendations(
        site=site,
        chargers=(charger,),
        horizon=horizon,
        current_import_sek_kwh=2.0,
        now=now,
        min_spread_sek_kwh=0.05,
    )
    assert len(recs) == 1
    assert recs[0].charger_name == "Halo"
    assert recs[0].estimated_saving_sek is not None
    assert recs[0].estimated_saving_sek > 0
    assert "12:" in recs[0].reason_sv or "13:" in recs[0].reason_sv


def test_build_ev_recommendations_uses_site_timezone_in_reason():
    now = datetime(2026, 8, 13, 22, 0, tzinfo=UTC)  # 00:00 Stockholm next day
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
        max_current_a=16.0,
        phases=3,
        nominal_voltage_v=230.0,
    )
    horizon = tuple(
        _period(now + timedelta(minutes=15 * (i + 1)), price)
        for i, price in enumerate([2.0, 1.9, 1.8, 0.6, 0.55, 0.58, 0.62, 1.5])
    )
    recs = build_ev_recommendations(
        site=site,
        chargers=(charger,),
        horizon=horizon,
        current_import_sek_kwh=2.0,
        now=now,
        min_spread_sek_kwh=0.05,
    )
    assert len(recs) == 1
    assert "00:" in recs[0].reason_sv or "01:" in recs[0].reason_sv
    assert "UTC" not in recs[0].reason_sv


def test_build_ev_recommendations_empty_when_current_already_cheap():
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    site = SiteModel(id=1, slug="akarp", name="Åkarp", timezone="Europe/Stockholm")
    charger = EvChargerModel(
        id=7,
        site_id=1,
        name="Halo",
        manufacturer="ChargeAmps",
        model="Halo",
        bridge_enabled=True,
        charging_mode="SMART_CHARGE",
        last_vehicle_connected=True,
        max_current_a=16.0,
        phases=3,
        nominal_voltage_v=230.0,
    )
    horizon = tuple(_period(now + timedelta(minutes=15 * (i + 1)), 0.6) for i in range(8))
    recs = build_ev_recommendations(
        site=site,
        chargers=(charger,),
        horizon=horizon,
        current_import_sek_kwh=0.55,
        now=now,
    )
    assert recs == ()
