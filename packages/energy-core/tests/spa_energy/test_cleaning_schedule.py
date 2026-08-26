"""Tests for spa daily cleaning schedule planning."""

from datetime import UTC, datetime, timedelta

import pytest

from energy_core.flexible_load.types import EnergySource, HorizonBlock, ScoredBlock
from energy_core.spa_energy.cleaning_schedule import (
    build_config_summary_sv,
    plan_daily_cleaning_windows,
    validate_cleaning_config,
)


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


def test_validate_cleaning_config_infeasible_max_starts():
    result = validate_cleaning_config(
        daily_hours=4,
        min_cycle_minutes=60,
        min_pause_minutes=20,
        max_starts=1,
        allowed_start="07:00",
        allowed_end="10:00",
    )
    assert result.feasible is False
    assert result.warning_sv is not None
    assert "4 timmar" in result.warning_sv


def test_validate_cleaning_config_feasible():
    result = validate_cleaning_config(
        daily_hours=4,
        min_cycle_minutes=60,
        min_pause_minutes=20,
        max_starts=2,
        allowed_start="07:00",
        allowed_end="22:00",
    )
    assert result.feasible is True


def test_build_config_summary_sv():
    summary = build_config_summary_sv(
        daily_hours=4,
        min_cycle_minutes=60,
        max_starts=2,
        allowed_start="07:00",
        allowed_end="22:00",
    )
    assert "4 timmar" in summary
    assert "2 starter" in summary
    assert "60 minuter" in summary


def test_plan_daily_cleaning_prefers_fewer_starts():
    now = datetime(2026, 8, 26, 6, 0, tzinfo=UTC)
    earliest = now
    latest = now + timedelta(hours=16)
    scored = tuple(
        _block(now + timedelta(minutes=15 * i), surplus_w=2500 if 9 <= (6 + i * 0.25) < 16 else 800)
        for i in range(64)
    )
    windows = plan_daily_cleaning_windows(
        scored,
        daily_hours=4,
        min_cycle=timedelta(hours=1),
        min_pause=timedelta(minutes=20),
        max_starts=2,
        earliest=earliest,
        latest=latest,
        now=now,
        strategy=__import__("energy_core.flexible_load.types", fromlist=["LoadStrategy"]).LoadStrategy.SMART,
        nominal_power_w=2000,
    )
    assert len(windows) <= 2
    total_hours = sum(w.duration.total_seconds() for w in windows) / 3600.0
    assert total_hours >= 3.5
