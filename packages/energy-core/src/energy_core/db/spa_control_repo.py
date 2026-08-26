"""Repository for spa smart control configuration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import SpaControlConfigModel


@dataclass(frozen=True, slots=True)
class SpaControlConfigRecord:
    consumer_id: int
    smart_control_enabled: bool
    strategy: str
    dry_run: bool
    shadow_mode: bool
    shadow_mode_until: datetime | None
    min_cleaning_hours_per_day: float
    allowed_window_start: str
    allowed_window_end: str
    prefer_solar: bool
    allow_battery: bool
    min_battery_soc_pct: float
    min_run_minutes: int
    min_stop_minutes: int
    max_starts_per_day: int
    filter_cycles_per_day: int
    filter_duration_minutes: int
    minimum_cycle_separation_minutes: int
    filter_optimization_enabled: bool
    last_known_safe_filter_schedule_json: str | None
    safety_floor_frequency_per_day: float
    safety_floor_duration_hours: float
    smart_preheat_enabled: bool
    normal_temperature_c: float
    max_preheat_temperature_c: float
    min_comfort_temperature_c: float
    load_priority: int
    fixed_schedule_start: str | None
    fixed_schedule_end: str | None


def _to_record(model: SpaControlConfigModel) -> SpaControlConfigRecord:
    return SpaControlConfigRecord(
        consumer_id=model.consumer_id,
        smart_control_enabled=model.smart_control_enabled,
        strategy=model.strategy,
        dry_run=model.dry_run,
        shadow_mode=model.shadow_mode,
        shadow_mode_until=model.shadow_mode_until,
        min_cleaning_hours_per_day=model.min_cleaning_hours_per_day,
        allowed_window_start=model.allowed_window_start,
        allowed_window_end=model.allowed_window_end,
        prefer_solar=model.prefer_solar,
        allow_battery=model.allow_battery,
        min_battery_soc_pct=model.min_battery_soc_pct,
        min_run_minutes=model.min_run_minutes,
        min_stop_minutes=model.min_stop_minutes,
        max_starts_per_day=model.max_starts_per_day,
        filter_cycles_per_day=model.filter_cycles_per_day,
        filter_duration_minutes=model.filter_duration_minutes,
        minimum_cycle_separation_minutes=model.minimum_cycle_separation_minutes,
        filter_optimization_enabled=model.filter_optimization_enabled,
        last_known_safe_filter_schedule_json=model.last_known_safe_filter_schedule_json,
        safety_floor_frequency_per_day=model.safety_floor_frequency_per_day,
        safety_floor_duration_hours=model.safety_floor_duration_hours,
        smart_preheat_enabled=model.smart_preheat_enabled,
        normal_temperature_c=model.normal_temperature_c,
        max_preheat_temperature_c=model.max_preheat_temperature_c,
        min_comfort_temperature_c=model.min_comfort_temperature_c,
        load_priority=model.load_priority,
        fixed_schedule_start=model.fixed_schedule_start,
        fixed_schedule_end=model.fixed_schedule_end,
    )


class SpaControlConfigRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, consumer_id: int) -> SpaControlConfigRecord:
        model = await self._session.get(SpaControlConfigModel, consumer_id)
        if model is None:
            model = SpaControlConfigModel(consumer_id=consumer_id)
            self._session.add(model)
            await self._session.flush()
        return _to_record(model)

    async def get(self, consumer_id: int) -> SpaControlConfigRecord | None:
        model = await self._session.get(SpaControlConfigModel, consumer_id)
        return None if model is None else _to_record(model)

    async def update(
        self,
        consumer_id: int,
        **fields: object,
    ) -> SpaControlConfigRecord | None:
        model = await self._session.get(SpaControlConfigModel, consumer_id)
        if model is None:
            return None
        for key, value in fields.items():
            if value is not None and hasattr(model, key):
                setattr(model, key, value)
        await self._session.flush()
        return _to_record(model)
