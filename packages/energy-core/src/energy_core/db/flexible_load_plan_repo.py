"""Repository for flexible load plans."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import FlexibleLoadPlanBlockModel, FlexibleLoadPlanModel
from energy_core.flexible_load.types import LoadPlan


@dataclass(frozen=True, slots=True)
class StoredPlanWindow:
    start: datetime
    end: datetime
    duration_hours: float
    expected_energy_kwh: float
    expected_cost_sek: float
    expected_energy_source: str
    solar_share: float | None = None


@dataclass(frozen=True, slots=True)
class FlexibleLoadPlanRecord:
    id: int
    site_id: int
    consumer_id: int | None
    load_id: str
    strategy: str
    reason: str
    reason_sv: str
    explanation_sv: str
    window_start: datetime | None
    window_end: datetime | None
    expected_energy_kwh: float | None
    expected_cost_sek: float | None
    baseline_cost_sek: float | None
    savings_sek: float | None
    expected_energy_source: str | None
    fallback_from_solar_only: bool
    dry_run: bool
    created_at: datetime
    windows: tuple[StoredPlanWindow, ...] = ()


@dataclass(frozen=True, slots=True)
class FlexibleLoadPlanBlockRecord:
    id: int
    plan_id: int
    timestamp: datetime
    score: float
    solar_forecast_w: float
    house_load_forecast_w: float
    available_surplus_w: float
    marginal_cost_sek_kwh: float
    expected_energy_source: str
    price_estimated: bool


class FlexibleLoadPlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_plan(
        self,
        *,
        site_id: int,
        consumer_id: int | None,
        plan: LoadPlan,
        dry_run: bool,
    ) -> FlexibleLoadPlanRecord:
        window = plan.windows[0] if plan.windows else None
        windows_payload = [
            {
                "start": w.start.isoformat(),
                "end": w.end.isoformat(),
                "duration_hours": round(w.duration.total_seconds() / 3600.0, 2),
                "expected_energy_kwh": w.expected_energy_kwh,
                "expected_cost_sek": w.expected_cost_sek,
                "expected_energy_source": w.expected_energy_source.value,
            }
            for w in plan.windows
        ]
        model = FlexibleLoadPlanModel(
            site_id=site_id,
            consumer_id=consumer_id,
            load_id=plan.load_id,
            strategy=plan.strategy.value,
            reason=plan.reason,
            reason_sv=plan.reason_sv,
            explanation_sv=plan.explanation_sv,
            window_start=window.start if window else None,
            window_end=window.end if window else None,
            expected_energy_kwh=sum(w.expected_energy_kwh for w in plan.windows) if plan.windows else None,
            expected_cost_sek=sum(w.expected_cost_sek for w in plan.windows) if plan.windows else None,
            baseline_cost_sek=plan.baseline_cost_sek,
            savings_sek=plan.savings_sek,
            expected_energy_source=window.expected_energy_source.value if window else None,
            fallback_from_solar_only=plan.fallback_from_solar_only,
            dry_run=dry_run,
            windows_json=json.dumps(windows_payload) if windows_payload else None,
        )
        self._session.add(model)
        await self._session.flush()

        for scored in plan.scored_blocks:
            block = FlexibleLoadPlanBlockModel(
                plan_id=model.id,
                timestamp=scored.block.timestamp,
                score=scored.score,
                solar_forecast_w=scored.block.solar_forecast_w,
                house_load_forecast_w=scored.block.house_load_forecast_w,
                available_surplus_w=scored.block.available_surplus_w,
                marginal_cost_sek_kwh=scored.marginal_cost_sek_kwh,
                expected_energy_source=scored.expected_energy_source.value,
                price_estimated=scored.block.price_estimated,
            )
            self._session.add(block)
        await self._session.flush()
        return self._to_record(model)

    async def list_latest_for_site(self, site_id: int) -> list[FlexibleLoadPlanRecord]:
        result = await self._session.scalars(
            select(FlexibleLoadPlanModel)
            .where(FlexibleLoadPlanModel.site_id == site_id)
            .order_by(desc(FlexibleLoadPlanModel.created_at))
        )
        latest_by_load: dict[str, FlexibleLoadPlanRecord] = {}
        for row in result:
            if row.load_id not in latest_by_load:
                latest_by_load[row.load_id] = self._to_record(row)
        return list(latest_by_load.values())

    async def get_latest_for_site(self, site_id: int, *, load_id: str = "spa_cleaning") -> FlexibleLoadPlanRecord | None:
        row = await self._session.scalar(
            select(FlexibleLoadPlanModel)
            .where(FlexibleLoadPlanModel.site_id == site_id, FlexibleLoadPlanModel.load_id == load_id)
            .order_by(desc(FlexibleLoadPlanModel.created_at))
            .limit(1)
        )
        return None if row is None else self._to_record(row)

    async def list_blocks(self, plan_id: int) -> list[FlexibleLoadPlanBlockRecord]:
        result = await self._session.scalars(
            select(FlexibleLoadPlanBlockModel)
            .where(FlexibleLoadPlanBlockModel.plan_id == plan_id)
            .order_by(FlexibleLoadPlanBlockModel.timestamp)
        )
        return [
            FlexibleLoadPlanBlockRecord(
                id=row.id,
                plan_id=row.plan_id,
                timestamp=row.timestamp,
                score=row.score,
                solar_forecast_w=row.solar_forecast_w,
                house_load_forecast_w=row.house_load_forecast_w,
                available_surplus_w=row.available_surplus_w,
                marginal_cost_sek_kwh=row.marginal_cost_sek_kwh,
                expected_energy_source=row.expected_energy_source,
                price_estimated=row.price_estimated,
            )
            for row in result
        ]

    def _to_record(self, model: FlexibleLoadPlanModel) -> FlexibleLoadPlanRecord:
        windows = self._parse_windows_json(model)
        return FlexibleLoadPlanRecord(
            id=model.id,
            site_id=model.site_id,
            consumer_id=model.consumer_id,
            load_id=model.load_id,
            strategy=model.strategy,
            reason=model.reason,
            reason_sv=model.reason_sv,
            explanation_sv=model.explanation_sv,
            window_start=model.window_start,
            window_end=model.window_end,
            expected_energy_kwh=model.expected_energy_kwh,
            expected_cost_sek=model.expected_cost_sek,
            baseline_cost_sek=model.baseline_cost_sek,
            savings_sek=model.savings_sek,
            expected_energy_source=model.expected_energy_source,
            fallback_from_solar_only=model.fallback_from_solar_only,
            dry_run=model.dry_run,
            created_at=model.created_at,
            windows=windows,
        )

    def _parse_windows_json(self, model: FlexibleLoadPlanModel) -> tuple[StoredPlanWindow, ...]:
        if model.windows_json:
            try:
                payload = json.loads(model.windows_json)
            except json.JSONDecodeError:
                payload = []
            if isinstance(payload, list) and payload:
                return tuple(
                    StoredPlanWindow(
                        start=datetime.fromisoformat(item["start"]),
                        end=datetime.fromisoformat(item["end"]),
                        duration_hours=float(item.get("duration_hours", 0)),
                        expected_energy_kwh=float(item.get("expected_energy_kwh", 0)),
                        expected_cost_sek=float(item.get("expected_cost_sek", 0)),
                        expected_energy_source=str(item.get("expected_energy_source", "GRID")),
                        solar_share=item.get("solar_share"),
                    )
                    for item in payload
                )
        if model.window_start and model.window_end:
            return (
                StoredPlanWindow(
                    start=model.window_start,
                    end=model.window_end,
                    duration_hours=round((model.window_end - model.window_start).total_seconds() / 3600.0, 2),
                    expected_energy_kwh=model.expected_energy_kwh or 0.0,
                    expected_cost_sek=model.expected_cost_sek or 0.0,
                    expected_energy_source=model.expected_energy_source or "GRID",
                ),
            )
        return ()
