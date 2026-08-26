"""Coordinate flexible loads on a shared energy horizon."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

from energy_core.solar_forecast.types import INTERVAL_MINUTES
from energy_core.flexible_load.optimizer import FlexibleLoadOptimizer
from energy_core.flexible_load.types import FlexibleLoad, HorizonBlock, LoadPlan, LoadStrategy


@dataclass(frozen=True, slots=True)
class OrchestratedLoadSpec:
    load: FlexibleLoad
    strategy: LoadStrategy
    allow_battery: bool = True
    prefer_solar: bool = True
    min_battery_soc_pct: float = 40.0
    fallback_price_sek_kwh: float = 2.0


@dataclass(frozen=True, slots=True)
class OrchestratedLoadPlan:
    load_id: str
    name: str
    priority: int
    plan: LoadPlan


class EnergyOrchestrator:
    """Plan multiple flexible loads without double-booking forecast surplus."""

    def plan_all(
        self,
        specs: list[OrchestratedLoadSpec],
        horizon: tuple[HorizonBlock, ...],
        *,
        now: datetime | None = None,
    ) -> tuple[OrchestratedLoadPlan, ...]:
        if not specs or not horizon:
            return ()

        now = now or datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        ordered = sorted(specs, key=lambda spec: spec.load.priority, reverse=True)
        reserved_w_by_ts: dict[datetime, float] = {}
        results: list[OrchestratedLoadPlan] = []

        for spec in ordered:
            adjusted = self._apply_reservations(horizon, reserved_w_by_ts)
            optimizer = FlexibleLoadOptimizer(
                allow_battery=spec.allow_battery,
                prefer_solar=spec.prefer_solar,
                min_battery_soc_pct=spec.min_battery_soc_pct,
                fallback_price_sek_kwh=spec.fallback_price_sek_kwh,
            )
            plan = optimizer.plan(spec.load, adjusted, spec.strategy, now=now)
            results.append(
                OrchestratedLoadPlan(
                    load_id=spec.load.load_id,
                    name=spec.load.name,
                    priority=spec.load.priority,
                    plan=plan,
                )
            )
            self._reserve_plan(reserved_w_by_ts, spec.load, plan)

        return tuple(results)

    def _apply_reservations(
        self,
        horizon: tuple[HorizonBlock, ...],
        reserved_w_by_ts: dict[datetime, float],
    ) -> tuple[HorizonBlock, ...]:
        adjusted: list[HorizonBlock] = []
        for block in horizon:
            reserved = reserved_w_by_ts.get(block.timestamp, 0.0)
            raw_surplus = block.solar_forecast_w - block.house_load_forecast_w - reserved
            adjusted.append(
                replace(
                    block,
                    higher_priority_loads_w=reserved,
                    available_surplus_w=max(0.0, raw_surplus),
                )
            )
        return tuple(adjusted)

    def _reserve_plan(
        self,
        reserved_w_by_ts: dict[datetime, float],
        load: FlexibleLoad,
        plan: LoadPlan,
    ) -> None:
        if not plan.windows:
            return
        for window in plan.windows:
            reserved_timestamps: set[datetime] = {
                block.block.timestamp
                for block in plan.scored_blocks
                if window.start <= block.block.timestamp < window.end
            }
            if not reserved_timestamps:
                ts = window.start
                step = timedelta(minutes=INTERVAL_MINUTES)
                while ts < window.end:
                    reserved_timestamps.add(ts)
                    ts += step
            for ts in reserved_timestamps:
                reserved_w_by_ts[ts] = reserved_w_by_ts.get(ts, 0.0) + load.nominal_power_w
