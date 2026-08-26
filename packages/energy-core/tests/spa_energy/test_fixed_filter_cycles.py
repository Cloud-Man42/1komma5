"""Tests for fixed 4×2 h filter cycle planning."""

from datetime import UTC, datetime, timedelta

from energy_core.flexible_load.types import EnergySource, HorizonBlock, LoadStrategy, ScoredBlock
from energy_core.spa_energy.cleaning_schedule import plan_fixed_filter_cycles


def _block(ts: datetime, surplus_w: float = 3000.0, score: float = 10.0) -> ScoredBlock:
    horizon = HorizonBlock(
        timestamp=ts,
        solar_forecast_w=surplus_w,
        house_load_forecast_w=500,
        higher_priority_loads_w=0,
        available_surplus_w=surplus_w,
        battery_soc_pct=60,
        spot_price_eur_kwh=0.1,
        all_in_price_eur_kwh=1.2,
        export_value_sek_kwh=0.5,
    )
    return ScoredBlock(
        block=horizon,
        score=score,
        solar_surplus_score=score,
        low_price_score=0,
        battery_availability_score=0,
        deadline_score=0,
        grid_import_penalty=0,
        battery_depletion_penalty=0,
        export_opportunity_penalty=0,
        expected_energy_source=EnergySource.SOLAR if surplus_w >= 2000 else EnergySource.GRID,
        marginal_cost_sek_kwh=1.0,
        load_feasible=True,
    )


def test_plan_fixed_filter_cycles_exactly_four_two_hour_windows():
    now = datetime(2026, 8, 26, 6, 0, tzinfo=UTC)
    earliest = now
    latest = now + timedelta(hours=16)
    scored = tuple(
        _block(
            now + timedelta(minutes=15 * i),
            surplus_w=2500 if 10 <= (6 + i * 0.25) < 18 else 400,
            score=20 if 10 <= (6 + i * 0.25) < 18 else 2,
        )
        for i in range(64)
    )
    windows = plan_fixed_filter_cycles(
        scored,
        cycles_per_day=4,
        duration_minutes=120,
        min_separation=timedelta(minutes=60),
        earliest=earliest,
        latest=latest,
        now=now,
        strategy=LoadStrategy.SMART,
        nominal_power_w=1200,
    )
    assert len(windows) == 4
    for window in windows:
        assert abs(window.duration.total_seconds() - 7200) < 1
    total_hours = sum(w.duration.total_seconds() for w in windows) / 3600.0
    assert total_hours >= 7.9


def test_plan_fixed_filter_cycles_never_merges_into_one():
    now = datetime(2026, 8, 26, 6, 0, tzinfo=UTC)
    earliest = now
    latest = now + timedelta(hours=16)
    scored = tuple(_block(now + timedelta(minutes=15 * i), score=float(i)) for i in range(64))
    windows = plan_fixed_filter_cycles(
        scored,
        cycles_per_day=4,
        duration_minutes=120,
        min_separation=timedelta(minutes=60),
        earliest=earliest,
        latest=latest,
        now=now,
        strategy=LoadStrategy.SMART,
        nominal_power_w=1200,
    )
    assert len(windows) == 4
    for i in range(len(windows) - 1):
        gap = windows[i + 1].start - windows[i].end
        assert gap >= timedelta(minutes=60) - timedelta(seconds=1)
