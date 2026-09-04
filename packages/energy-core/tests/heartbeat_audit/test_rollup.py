"""Tests for daily audit rollups."""

from energy_core.db.repositories import FinancialStat
from energy_core.heartbeat_audit.rollup import aggregate_monthly_rollups, build_daily_rollup
from energy_core.price_engine.types import (
    Currency,
    PriceArea,
    PricePeriod,
    PriceQuality,
    PriceSource,
)


def _period(start, import_price: float) -> PricePeriod:
    from datetime import UTC, datetime, timedelta

    return PricePeriod(
        period_start=start,
        period_end=start + timedelta(minutes=15),
        site_id=1,
        price_area=PriceArea.SE4,
        currency=Currency.SEK,
        market_price_sek_kwh=import_price * 0.3,
        import_price_sek_kwh=import_price,
        export_price_sek_kwh=0.4,
        source=PriceSource.HEARTBEAT,
        quality=PriceQuality.REAL,
        is_estimated=False,
    )


def test_build_daily_rollup_with_savings():
    from datetime import UTC, datetime, timedelta

    now = datetime(2026, 9, 2, 10, 0, tzinfo=UTC)
    horizon = tuple(_period(now + timedelta(minutes=15 * i), price) for i, price in enumerate([2.0, 1.8, 0.6, 0.55]))
    financial = FinancialStat(
        period_start="2026-09-02",
        solar_self_consumed_kwh=5.0,
        battery_self_consumed_kwh=2.0,
        exported_kwh=1.0,
        imported_kwh=8.0,
        solar_savings_sek=10.0,
        battery_savings_sek=4.0,
        export_revenue_sek=0.4,
        grid_import_cost_sek=16.0,
        market_priced_fraction=1.0,
    )
    rollup = build_daily_rollup(day="2026-09-02", financial=financial, horizon=horizon, ev_savings_sek=2.0)
    assert rollup.actual_energy_cost_sek == 15.6
    assert rollup.heartbeat_saving_sek == 16.0
    assert rollup.emic_theoretical_optimal_cost_sek <= rollup.actual_energy_cost_sek
    assert rollup.heartbeat_efficiency_pct is not None


def test_aggregate_monthly_rollups():
    from datetime import UTC, datetime, timedelta

    now = datetime(2026, 9, 1, 10, 0, tzinfo=UTC)
    horizon = (_period(now, 1.5),)
    daily = tuple(
        build_daily_rollup(
            day=f"2026-09-0{day}",
            financial=FinancialStat(
                period_start=f"2026-09-0{day}",
                solar_self_consumed_kwh=1.0,
                battery_self_consumed_kwh=0.0,
                exported_kwh=0.0,
                imported_kwh=2.0,
                solar_savings_sek=1.0,
                battery_savings_sek=0.0,
                export_revenue_sek=0.0,
                grid_import_cost_sek=3.0,
                market_priced_fraction=1.0,
            ),
            horizon=horizon,
        )
        for day in (1, 2)
    )
    month = aggregate_monthly_rollups(daily)
    assert month is not None
    assert month.month == "2026-09"
    assert month.days_with_data == 2
    assert month.actual_energy_cost_sek == sum(d.actual_energy_cost_sek for d in daily)
