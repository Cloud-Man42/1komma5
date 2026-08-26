"""Tests for site energy orchestrator."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from energy_core.flexible_load.horizon import HorizonBlock
from energy_core.flexible_load.orchestrator import EnergyOrchestrator, OrchestratedLoadSpec
from energy_core.flexible_load.types import FlexibleLoad, LoadStrategy


def _block(ts: datetime, *, solar_w: float, house_w: float = 500.0) -> HorizonBlock:
    surplus = max(0.0, solar_w - house_w)
    return HorizonBlock(
        timestamp=ts,
        solar_forecast_w=solar_w,
        house_load_forecast_w=house_w,
        higher_priority_loads_w=0.0,
        available_surplus_w=surplus,
        battery_soc_pct=60.0,
        spot_price_eur_kwh=0.2,
        all_in_price_eur_kwh=0.2,
        export_value_sek_kwh=0.8,
    )


def test_higher_priority_load_reduces_surplus_for_lower_priority():
    now = datetime(2026, 8, 26, 8, 0, tzinfo=UTC)
    horizon = tuple(_block(now + timedelta(minutes=15 * i), solar_w=5000) for i in range(12))

    high = FlexibleLoad(
        load_id="ev_charger_1",
        name="EV",
        nominal_power_w=3000.0,
        minimum_runtime=timedelta(hours=1),
        maximum_runtime=timedelta(hours=2),
        earliest_start=now,
        latest_finish=now + timedelta(hours=8),
        deadline=now + timedelta(hours=8),
        priority=60,
        safety_critical=False,
    )
    low = FlexibleLoad(
        load_id="spa_cleaning",
        name="Spa",
        nominal_power_w=1400.0,
        minimum_runtime=timedelta(hours=2),
        maximum_runtime=timedelta(hours=2),
        earliest_start=now,
        latest_finish=now + timedelta(hours=8),
        deadline=now + timedelta(hours=8),
        priority=40,
        safety_critical=True,
    )

    orchestrator = EnergyOrchestrator()
    results = orchestrator.plan_all(
        [
            OrchestratedLoadSpec(load=high, strategy=LoadStrategy.SMART),
            OrchestratedLoadSpec(load=low, strategy=LoadStrategy.SMART),
        ],
        horizon,
        now=now,
    )

    assert len(results) == 2
    assert results[0].load_id == "ev_charger_1"
    assert results[1].load_id == "spa_cleaning"
    assert results[0].plan.windows
    assert results[1].plan.windows
