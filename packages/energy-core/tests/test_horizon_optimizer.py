"""Tests for Horizon Optimizer snapshot builder."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from energy_core.energy_optimizer.horizon import build_horizon_optimizer_snapshot, load_type_from_id
from energy_core.flexible_load.horizon import HorizonBlock
from energy_core.flexible_load.orchestrator import OrchestratedLoadPlan, OrchestratedLoadSpec
from energy_core.flexible_load.types import EnergySource, FlexibleLoad, LoadPlan, LoadStrategy, PlanWindow


def _block(ts: datetime) -> HorizonBlock:
    return HorizonBlock(
        timestamp=ts,
        solar_forecast_w=4000.0,
        house_load_forecast_w=500.0,
        higher_priority_loads_w=0.0,
        available_surplus_w=3500.0,
        battery_soc_pct=55.0,
        spot_price_eur_kwh=0.2,
        all_in_price_eur_kwh=0.25,
        export_value_sek_kwh=0.8,
    )


def test_load_type_from_id() -> None:
    assert load_type_from_id("spa_cleaning") == "spa"
    assert load_type_from_id("ev_charger_3") == "ev"
    assert load_type_from_id("other") == "other"


def test_build_snapshot_unavailable_without_specs() -> None:
    now = datetime(2026, 9, 4, 8, 0, tzinfo=UTC)
    snapshot = build_horizon_optimizer_snapshot(
        specs=(),
        horizon=(),
        results=(),
        now=now,
    )
    assert snapshot.available is False
    assert snapshot.monitor_only is True
    assert snapshot.unavailable_reason_sv is not None


def test_build_snapshot_available_with_planned_load() -> None:
    now = datetime(2026, 9, 4, 8, 0, tzinfo=UTC)
    horizon = (_block(now + timedelta(minutes=15 * i)) for i in range(8))
    horizon = tuple(horizon)
    load = FlexibleLoad(
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
    spec = OrchestratedLoadSpec(load=load, strategy=LoadStrategy.SMART)
    window = PlanWindow(
        start=now + timedelta(hours=2),
        end=now + timedelta(hours=3),
        duration=timedelta(hours=1),
        expected_energy_kwh=3.0,
        expected_cost_sek=4.5,
        expected_energy_source=EnergySource.SOLAR,
        average_score=0.8,
    )
    plan = LoadPlan(
        load_id="ev_charger_1",
        strategy=LoadStrategy.SMART,
        windows=(window,),
        reason="smart",
        reason_sv="smart",
        explanation_sv="Billigt fönster",
        savings_sek=2.5,
    )
    result = OrchestratedLoadPlan(
        load_id="ev_charger_1",
        name="EV",
        priority=60,
        plan=plan,
    )
    snapshot = build_horizon_optimizer_snapshot(
        specs=(spec,),
        horizon=horizon,
        results=(result,),
        now=now,
    )
    assert snapshot.available is True
    assert snapshot.horizon_blocks == 8
    assert len(snapshot.loads) == 1
    assert snapshot.loads[0].load_type == "ev"
    assert snapshot.loads[0].window_start == window.start
    assert snapshot.total_planned_savings_sek == 2.5
    assert snapshot.headline_sv is not None
