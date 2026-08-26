"""Tests for flexible load optimizer scenarios."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from energy_core.flexible_load.horizon import HorizonBlock
from energy_core.flexible_load.optimizer import FlexibleLoadOptimizer
from energy_core.flexible_load.types import EnergySource, FlexibleLoad, LoadStrategy


def _block(
    ts: datetime,
    *,
    solar_w: float = 0.0,
    house_w: float = 500.0,
    surplus_w: float | None = None,
    price_eur: float = 0.2,
    battery_soc: float = 50.0,
) -> HorizonBlock:
    surplus = surplus_w if surplus_w is not None else max(0.0, solar_w - house_w)
    return HorizonBlock(
        timestamp=ts,
        solar_forecast_w=solar_w,
        house_load_forecast_w=house_w,
        higher_priority_loads_w=0.0,
        available_surplus_w=surplus,
        battery_soc_pct=battery_soc,
        spot_price_eur_kwh=price_eur,
        all_in_price_eur_kwh=price_eur,
        export_value_sek_kwh=0.8,
        price_estimated=False,
        forecast_confidence=0.8,
    )


def _load(now: datetime, *, deadline_hours: float = 24.0) -> FlexibleLoad:
    return FlexibleLoad(
        load_id="spa_cleaning",
        name="Spa cleaning",
        nominal_power_w=1400.0,
        minimum_runtime=timedelta(hours=2),
        maximum_runtime=timedelta(hours=2.5),
        earliest_start=now,
        latest_finish=now + timedelta(hours=12),
        deadline=now + timedelta(hours=deadline_hours),
        safety_critical=True,
    )


def _horizon(now: datetime, blocks: list[HorizonBlock]) -> tuple[HorizonBlock, ...]:
    return tuple(blocks)


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 8, 26, 8, 0, tzinfo=UTC)


def test_scenario_heavy_sun(now: datetime):
    blocks = [_block(now + timedelta(hours=i), solar_w=5000, house_w=800, surplus_w=4200) for i in range(12)]
    plan = FlexibleLoadOptimizer().plan(_load(now), _horizon(now, blocks), LoadStrategy.SMART, now=now)
    assert plan.windows
    assert plan.windows[0].expected_energy_source == EnergySource.SOLAR


def test_scenario_no_sun(now: datetime):
    blocks = [_block(now + timedelta(hours=i), solar_w=0, house_w=600, surplus_w=0, price_eur=0.35) for i in range(12)]
    plan = FlexibleLoadOptimizer(prefer_solar=True).plan(_load(now), _horizon(now, blocks), LoadStrategy.SMART, now=now)
    assert plan.windows


def test_scenario_expensive_power(now: datetime):
    blocks = [_block(now + timedelta(hours=i), solar_w=0, price_eur=0.8) for i in range(12)]
    plan = FlexibleLoadOptimizer().plan(_load(now), _horizon(now, blocks), LoadStrategy.CHEAPEST, now=now)
    assert plan.windows


def test_scenario_cheap_night_power(now: datetime):
    blocks = []
    for i in range(12):
        price = 0.08 if i < 4 else 0.5
        blocks.append(_block(now + timedelta(hours=i), solar_w=0, price_eur=price))
    plan = FlexibleLoadOptimizer().plan(_load(now), _horizon(now, blocks), LoadStrategy.CHEAPEST, now=now)
    assert plan.windows
    assert plan.windows[0].start.hour <= (now + timedelta(hours=3)).hour


def test_scenario_full_battery(now: datetime):
    blocks = [_block(now + timedelta(hours=i), solar_w=1000, battery_soc=90.0) for i in range(12)]
    plan = FlexibleLoadOptimizer(allow_battery=True, min_battery_soc_pct=40).plan(
        _load(now), _horizon(now, blocks), LoadStrategy.SMART, now=now
    )
    assert plan.windows


def test_scenario_empty_battery(now: datetime):
    blocks = [_block(now + timedelta(hours=i), solar_w=500, battery_soc=15.0) for i in range(12)]
    plan = FlexibleLoadOptimizer(allow_battery=False, min_battery_soc_pct=40).plan(
        _load(now), _horizon(now, blocks), LoadStrategy.SMART, now=now
    )
    assert plan.windows


def test_scenario_deadline_near(now: datetime):
    load = _load(now, deadline_hours=1.5)
    blocks = [_block(now + timedelta(minutes=15 * i), solar_w=0, price_eur=0.9) for i in range(8)]
    plan = FlexibleLoadOptimizer().plan(load, _horizon(now, blocks), LoadStrategy.SMART, now=now)
    assert plan.windows
    assert plan.reason in {"deadline_critical", "solar_surplus", "smart_scheduled", "cheapest_energy"}


def test_scenario_solar_only_fallback(now: datetime):
    load = _load(now, deadline_hours=1.0)
    blocks = [_block(now + timedelta(minutes=15 * i), solar_w=0, surplus_w=0) for i in range(8)]
    plan = FlexibleLoadOptimizer().plan(load, _horizon(now, blocks), LoadStrategy.SOLAR_ONLY, now=now)
    assert plan.fallback_from_solar_only or plan.windows


def test_scenario_fixed_schedule(now: datetime):
    fixed_start = now + timedelta(hours=2)
    fixed_end = fixed_start + timedelta(hours=2)
    load = FlexibleLoad(
        load_id="spa_cleaning",
        name="Spa",
        nominal_power_w=1400,
        minimum_runtime=timedelta(hours=2),
        maximum_runtime=timedelta(hours=2),
        earliest_start=now,
        latest_finish=now + timedelta(hours=12),
        deadline=now + timedelta(hours=24),
        safety_critical=True,
        fixed_start=fixed_start,
        fixed_end=fixed_end,
    )
    blocks = [_block(now + timedelta(hours=i), solar_w=4000 if i >= 4 else 0) for i in range(12)]
    plan = FlexibleLoadOptimizer().plan(load, _horizon(now, blocks), LoadStrategy.FIXED_SCHEDULE, now=now)
    assert plan.fixed_schedule_analysis
    assert plan.windows
    assert plan.windows[0].start == fixed_start


def test_scenario_no_forecast_empty_horizon(now: datetime):
    plan = FlexibleLoadOptimizer().plan(_load(now), (), LoadStrategy.SMART, now=now)
    assert plan.windows or plan.reason == "no_window"


def test_scenario_large_house_loads(now: datetime):
    blocks = [_block(now + timedelta(hours=i), solar_w=3000, house_w=2800, surplus_w=200) for i in range(12)]
    plan = FlexibleLoadOptimizer().plan(_load(now), _horizon(now, blocks), LoadStrategy.SOLAR_ONLY, now=now)
    assert plan.windows or plan.fallback_from_solar_only


def test_scenario_poor_solar_forecast(now: datetime):
    blocks = [
        HorizonBlock(
            timestamp=now + timedelta(hours=i),
            solar_forecast_w=100,
            house_load_forecast_w=500,
            higher_priority_loads_w=0,
            available_surplus_w=0,
            battery_soc_pct=50,
            spot_price_eur_kwh=0.2,
            all_in_price_eur_kwh=0.2,
            export_value_sek_kwh=0.8,
            price_estimated=True,
            forecast_confidence=0.2,
        )
        for i in range(12)
    ]
    plan = FlexibleLoadOptimizer().plan(_load(now), tuple(blocks), LoadStrategy.SMART, now=now)
    assert plan.windows or plan.reason == "no_window"


def test_scenario_dst_stockholm(now: datetime):
    """Planning around DST transition uses timezone-aware bounds."""
    from energy_core.spa_energy.requirement import window_bounds

    ref = datetime(2026, 3, 29, 12, 0, tzinfo=UTC)
    start, end = window_bounds(ref, timezone="Europe/Stockholm", start_hhmm="07:00", end_hhmm="22:00")
    assert start < end


def test_scenario_denmark_timezone(now: datetime):
    from energy_core.spa_energy.requirement import window_bounds

    ref = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    start, end = window_bounds(ref, timezone="Europe/Copenhagen", start_hhmm="08:00", end_hhmm="21:00")
    assert start.tzinfo is not None
    assert end > start
