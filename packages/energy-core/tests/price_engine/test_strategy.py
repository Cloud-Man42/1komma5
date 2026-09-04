"""Tests for Phase 1 energy strategy heuristics."""

from datetime import UTC, datetime, timedelta

import pytest

from energy_core.price_engine.ev_recommendations import EvChargeRecommendation
from energy_core.price_engine.peak_protection import PeakProtectionHint
from energy_core.price_engine.strategy import build_strategy_snapshot
from energy_core.price_engine.types import (
    Currency,
    OptimizationMode,
    PriceArea,
    PricePeriod,
    PriceQuality,
    PriceSource,
    StrategyState,
)


def _period(start: datetime, import_price: float, market: float = 0.3) -> PricePeriod:
    return PricePeriod(
        period_start=start,
        period_end=start + timedelta(minutes=15),
        site_id=1,
        price_area=PriceArea.SE4,
        currency=Currency.SEK,
        market_price_sek_kwh=market,
        import_price_sek_kwh=import_price,
        export_price_sek_kwh=0.39,
        source=PriceSource.HEARTBEAT,
        quality=PriceQuality.REAL,
        is_estimated=False,
    )


def test_peak_ahead_when_future_import_higher():
    now = datetime(2026, 8, 13, 13, 0, tzinfo=UTC)
    current = _period(now, import_price=1.05)
    future = tuple(
        _period(now + timedelta(hours=h), import_price=price)
        for h, price in ((6, 3.2), (7, 2.8), (8, 1.2))
    )
    snapshot = build_strategy_snapshot(
        site_slug="akarp",
        timezone="Europe/Stockholm",
        current=current,
        horizon=(current, *future),
        battery_soc_pct=74.0,
        now=now,
    )
    assert snapshot.strategy_state in {StrategyState.SAVE_BATTERY, StrategyState.PEAK_AHEAD}
    assert snapshot.confidence >= 0.68
    assert snapshot.recommended_action is not None
    assert snapshot.next_peak_import_sek_kwh == pytest.approx(3.2)


def test_missing_price_fails_safe():
    now = datetime(2026, 8, 13, 13, 0, tzinfo=UTC)
    snapshot = build_strategy_snapshot(
        site_slug="akarp",
        timezone="Europe/Stockholm",
        current=None,
        horizon=(),
        battery_soc_pct=None,
        now=now,
    )
    assert snapshot.strategy_state == StrategyState.NORMAL_SELF_USE
    assert snapshot.optimization_mode == OptimizationMode.MONITOR_ONLY


def test_peak_protection_overrides_eov():
    now = datetime(2026, 8, 13, 13, 0, tzinfo=UTC)
    current = _period(now, import_price=1.05)
    peak_hint = PeakProtectionHint(
        fuse_headroom_a=1.5,
        grid_import_w=16000.0,
        main_fuse_a=25.0,
        utilization_pct=92.0,
        reason="Fuse near limit",
        reason_sv="Säkring nära max",
    )
    snapshot = build_strategy_snapshot(
        site_slug="akarp",
        timezone="Europe/Stockholm",
        current=current,
        horizon=(current,),
        battery_soc_pct=70.0,
        peak_hint=peak_hint,
        now=now,
    )
    assert snapshot.strategy_state == StrategyState.PEAK_PROTECTION
    assert snapshot.fuse_utilization_pct == 92.0
    assert snapshot.reason_sv == "Säkring nära max"


def test_ev_recommendation_when_cheaper_window():
    now = datetime(2026, 8, 13, 13, 0, tzinfo=UTC)
    current = _period(now, import_price=2.0)
    future = tuple(_period(now + timedelta(hours=h), import_price=0.5) for h in range(1, 9))
    ev_rec = EvChargeRecommendation(
        charger_id=7,
        charger_name="Halo",
        window_start=now + timedelta(hours=2),
        window_end=now + timedelta(hours=3),
        avg_import_sek_kwh=0.5,
        current_import_sek_kwh=2.0,
        estimated_saving_sek=15.0,
        reason="Cheaper window",
        reason_sv="Billigare fönster",
    )
    snapshot = build_strategy_snapshot(
        site_slug="akarp",
        timezone="Europe/Stockholm",
        current=current,
        horizon=(current, *future),
        battery_soc_pct=70.0,
        optimization_mode=OptimizationMode.MONITOR_ONLY,
        ev_recommendations=(ev_rec,),
        now=now,
    )
    assert snapshot.strategy_state == StrategyState.CHARGE_VEHICLE
    assert len(snapshot.ev_recommendations) == 1
    assert "17:00" in snapshot.reason_sv or "18:00" in snapshot.reason_sv
    assert "UTC" not in snapshot.reason_sv
    assert snapshot.grid_surcharge_sek_kwh == pytest.approx(1.7)
