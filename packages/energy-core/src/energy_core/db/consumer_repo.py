"""Repositories for generic energy consumers (Arctic Spa)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import (
    ConsumerAggregateModel,
    ConsumerIntervalModel,
    ConsumerSampleModel,
    EnergyConsumerModel,
    SiteModel,
    SpaDeviceConfigModel,
    SpaPollStateModel,
)


@dataclass(frozen=True, slots=True)
class ConsumerRecord:
    id: int
    site_id: int
    site_slug: str
    consumer_type: str
    name: str
    enabled: bool
    timezone: str


@dataclass(frozen=True, slots=True)
class SpaConfigRecord:
    consumer_id: int
    integration_enabled: bool
    api_base_url: str
    api_key: str
    external_spa_id: str
    poll_interval_seconds: int
    energy_collection_enabled: bool
    cost_calculation_enabled: bool
    power_profiles_json: str
    last_status_json: str
    last_status_at: datetime | None


class ConsumerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_spa_for_site(self, site_id: int) -> tuple[EnergyConsumerModel, SpaDeviceConfigModel] | None:
        result = await self._session.execute(
            select(EnergyConsumerModel, SpaDeviceConfigModel)
            .join(SpaDeviceConfigModel, SpaDeviceConfigModel.consumer_id == EnergyConsumerModel.id)
            .where(
                EnergyConsumerModel.site_id == site_id,
                EnergyConsumerModel.consumer_type == "SPA",
            )
        )
        row = result.first()
        return row if row is None else (row[0], row[1])

    async def get_spa_by_site_slug(self, slug: str) -> tuple[EnergyConsumerModel, SpaDeviceConfigModel, SiteModel] | None:
        result = await self._session.execute(
            select(EnergyConsumerModel, SpaDeviceConfigModel, SiteModel)
            .join(SiteModel, SiteModel.id == EnergyConsumerModel.site_id)
            .join(SpaDeviceConfigModel, SpaDeviceConfigModel.consumer_id == EnergyConsumerModel.id)
            .where(SiteModel.slug == slug, EnergyConsumerModel.consumer_type == "SPA")
        )
        row = result.first()
        return None if row is None else (row[0], row[1], row[2])

    async def get_or_create_spa(self, site: SiteModel) -> tuple[EnergyConsumerModel, SpaDeviceConfigModel]:
        existing = await self.get_spa_for_site(site.id)
        if existing is not None:
            return existing
        consumer = EnergyConsumerModel(
            site_id=site.id,
            consumer_type="SPA",
            name="Arctic Spa",
            enabled=True,
            timezone=site.timezone or "Europe/Stockholm",
        )
        self._session.add(consumer)
        await self._session.flush()
        config = SpaDeviceConfigModel(consumer_id=consumer.id)
        poll = SpaPollStateModel(consumer_id=consumer.id)
        self._session.add(config)
        self._session.add(poll)
        await self._session.flush()
        return consumer, config

    async def list_enabled_spa_consumers(self) -> list[tuple[EnergyConsumerModel, SpaDeviceConfigModel, SiteModel]]:
        result = await self._session.execute(
            select(EnergyConsumerModel, SpaDeviceConfigModel, SiteModel)
            .join(SiteModel, SiteModel.id == EnergyConsumerModel.site_id)
            .join(SpaDeviceConfigModel, SpaDeviceConfigModel.consumer_id == EnergyConsumerModel.id)
            .where(
                EnergyConsumerModel.enabled.is_(True),
                EnergyConsumerModel.consumer_type == "SPA",
                SpaDeviceConfigModel.integration_enabled.is_(True),
            )
        )
        return list(result.all())

    async def update_spa_config(
        self,
        consumer_id: int,
        *,
        integration_enabled: bool | None = None,
        api_base_url: str | None = None,
        api_key: str | None = None,
        external_spa_id: str | None = None,
        poll_interval_seconds: int | None = None,
        energy_collection_enabled: bool | None = None,
        cost_calculation_enabled: bool | None = None,
        power_profiles_json: str | None = None,
    ) -> SpaDeviceConfigModel | None:
        config = await self._session.get(SpaDeviceConfigModel, consumer_id)
        if config is None:
            return None
        if integration_enabled is not None:
            config.integration_enabled = integration_enabled
        if api_base_url is not None:
            config.api_base_url = api_base_url
        if api_key is not None and api_key.strip():
            config.api_key = api_key.strip()
        if external_spa_id is not None:
            config.external_spa_id = external_spa_id
        if poll_interval_seconds is not None:
            config.poll_interval_seconds = poll_interval_seconds
        if energy_collection_enabled is not None:
            config.energy_collection_enabled = energy_collection_enabled
        if cost_calculation_enabled is not None:
            config.cost_calculation_enabled = cost_calculation_enabled
        if power_profiles_json is not None:
            config.power_profiles_json = power_profiles_json
        return config

    async def save_status_snapshot(
        self,
        consumer_id: int,
        *,
        status_json: dict,
        recorded_at: datetime,
    ) -> None:
        config = await self._session.get(SpaDeviceConfigModel, consumer_id)
        if config is None:
            return
        config.last_status_json = json.dumps(status_json)
        config.last_status_at = recorded_at

    async def get_poll_state(self, consumer_id: int) -> SpaPollStateModel | None:
        return await self._session.get(SpaPollStateModel, consumer_id)

    async def upsert_poll_state(
        self,
        consumer_id: int,
        *,
        last_success_at: datetime | None = None,
        last_error_at: datetime | None = None,
        last_error_message: str | None = None,
        consecutive_failures: int | None = None,
        last_sample_at: datetime | None = None,
        backoff_until: datetime | None = None,
        polling_active: bool | None = None,
    ) -> None:
        state = await self.get_poll_state(consumer_id)
        if state is None:
            state = SpaPollStateModel(consumer_id=consumer_id)
            self._session.add(state)
        if last_success_at is not None:
            state.last_success_at = last_success_at
        if last_error_at is not None:
            state.last_error_at = last_error_at
        if last_error_message is not None:
            state.last_error_message = last_error_message
        if consecutive_failures is not None:
            state.consecutive_failures = consecutive_failures
        if last_sample_at is not None:
            state.last_sample_at = last_sample_at
        if backoff_until is not None:
            state.backoff_until = backoff_until
        if polling_active is not None:
            state.polling_active = polling_active


class ConsumerSampleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_sample(
        self,
        *,
        consumer_id: int,
        recorded_at: datetime,
        power_w: float | None,
        energy_delta_wh: float | None,
        water_temperature_c: float | None,
        set_temperature_c: float | None,
        heater_active: bool | None,
        pump_states: dict,
        filter_status: str | None,
        spa_connected: bool | None,
        source: str,
        quality: str,
        component_breakdown: dict,
    ) -> ConsumerSampleModel | None:
        existing = await self._session.execute(
            select(ConsumerSampleModel).where(
                ConsumerSampleModel.consumer_id == consumer_id,
                ConsumerSampleModel.recorded_at == recorded_at,
            )
        )
        if existing.scalar_one_or_none() is not None:
            return None
        row = ConsumerSampleModel(
            consumer_id=consumer_id,
            recorded_at=recorded_at,
            power_w=power_w,
            energy_delta_wh=energy_delta_wh,
            water_temperature_c=water_temperature_c,
            set_temperature_c=set_temperature_c,
            heater_active=heater_active,
            pump_states_json=json.dumps(pump_states),
            filter_status=filter_status,
            spa_connected=spa_connected,
            source=source,
            quality=quality,
            component_breakdown_json=json.dumps(component_breakdown),
        )
        self._session.add(row)
        return row

    async def get_latest(self, consumer_id: int) -> ConsumerSampleModel | None:
        result = await self._session.execute(
            select(ConsumerSampleModel)
            .where(ConsumerSampleModel.consumer_id == consumer_id)
            .order_by(ConsumerSampleModel.recorded_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def count_since(self, consumer_id: int, since: datetime) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(ConsumerSampleModel)
            .where(ConsumerSampleModel.consumer_id == consumer_id, ConsumerSampleModel.recorded_at >= since)
        )
        return int(result.scalar_one())

    async def list_for_period(
        self,
        consumer_id: int,
        *,
        start: datetime,
        end: datetime,
    ) -> list[ConsumerSampleModel]:
        result = await self._session.execute(
            select(ConsumerSampleModel)
            .where(
                ConsumerSampleModel.consumer_id == consumer_id,
                ConsumerSampleModel.recorded_at >= start,
                ConsumerSampleModel.recorded_at < end,
            )
            .order_by(ConsumerSampleModel.recorded_at)
        )
        return list(result.scalars().all())

    async def sum_for_period(self, consumer_id: int, *, start: datetime, end: datetime) -> dict:
        rows = await self.list_for_period(consumer_id, start=start, end=end)
        if not rows:
            return {}
        energy_kwh = sum((row.energy_delta_wh or 0.0) for row in rows) / 1000.0
        powered = [row for row in rows if (row.power_w or 0.0) > 0]
        return {
            "energy_kwh": energy_kwh,
            "max_power_w": max((row.power_w or 0.0 for row in rows), default=0.0),
            "avg_power_w": (sum(row.power_w or 0.0 for row in powered) / len(powered)) if powered else None,
            "samples_with_energy": sum(1 for row in rows if (row.energy_delta_wh or 0.0) > 0),
            "samples_with_power": len(powered),
        }


class ConsumerIntervalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(self, **kwargs) -> ConsumerIntervalModel:
        row = ConsumerIntervalModel(**kwargs)
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_for_period(
        self,
        consumer_id: int,
        *,
        start: datetime,
        end: datetime,
    ) -> list[ConsumerIntervalModel]:
        result = await self._session.execute(
            select(ConsumerIntervalModel)
            .where(
                ConsumerIntervalModel.consumer_id == consumer_id,
                ConsumerIntervalModel.start_time >= start,
                ConsumerIntervalModel.start_time < end,
            )
            .order_by(ConsumerIntervalModel.start_time)
        )
        return list(result.scalars().all())

    async def sum_for_period(self, consumer_id: int, *, start: datetime, end: datetime) -> dict:
        rows = await self.list_for_period(consumer_id, start=start, end=end)
        if not rows:
            return {}
        return {
            "energy_kwh": sum(r.energy_kwh for r in rows),
            "solar_direct_kwh": sum(r.solar_direct_kwh for r in rows),
            "solar_battery_kwh": sum(r.solar_battery_kwh for r in rows),
            "grid_battery_kwh": sum(r.grid_battery_kwh for r in rows),
            "grid_direct_kwh": sum(r.grid_direct_kwh for r in rows),
            "unknown_kwh": sum(r.unknown_kwh for r in rows),
            "actual_cost_sek": sum(r.actual_cost_sek for r in rows),
            "reference_cost_sek": sum(r.reference_cost_sek or 0.0 for r in rows),
            "savings_sek": sum(r.savings_sek or 0.0 for r in rows),
            "heater_runtime_seconds": sum(r.heater_runtime_seconds for r in rows),
            "pump_runtime_seconds": sum(r.pump_runtime_seconds for r in rows),
            "max_power_w": max((r.average_power_w or 0.0 for r in rows), default=0.0),
        }

    async def delete_for_consumer(self, consumer_id: int) -> int:
        result = await self._session.execute(
            delete(ConsumerIntervalModel).where(ConsumerIntervalModel.consumer_id == consumer_id)
        )
        return int(result.rowcount or 0)

    async def delete_since(self, consumer_id: int, since: datetime) -> int:
        result = await self._session.execute(
            delete(ConsumerIntervalModel).where(
                ConsumerIntervalModel.consumer_id == consumer_id,
                ConsumerIntervalModel.start_time >= since,
            )
        )
        return int(result.rowcount or 0)

    async def max_energy_kwh(self, consumer_id: int) -> float:
        result = await self._session.execute(
            select(func.max(ConsumerIntervalModel.energy_kwh)).where(
                ConsumerIntervalModel.consumer_id == consumer_id
            )
        )
        value = result.scalar_one_or_none()
        return float(value or 0.0)

    async def has_interval_for_window(
        self,
        consumer_id: int,
        *,
        start_time: datetime,
        end_time: datetime,
    ) -> bool:
        tolerance_seconds = 5.0
        result = await self._session.execute(
            select(ConsumerIntervalModel.id)
            .where(
                ConsumerIntervalModel.consumer_id == consumer_id,
                ConsumerIntervalModel.start_time >= start_time,
                ConsumerIntervalModel.end_time <= end_time,
            )
            .limit(1)
        )
        if result.scalar_one_or_none() is not None:
            return True
        delta = abs((end_time - start_time).total_seconds())
        if delta <= tolerance_seconds:
            return False
        result = await self._session.execute(
            select(ConsumerIntervalModel.id)
            .where(
                ConsumerIntervalModel.consumer_id == consumer_id,
                ConsumerIntervalModel.end_time > start_time,
                ConsumerIntervalModel.start_time < end_time,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def count_for_period(self, consumer_id: int, *, start: datetime, end: datetime) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(ConsumerIntervalModel)
            .where(
                ConsumerIntervalModel.consumer_id == consumer_id,
                ConsumerIntervalModel.start_time >= start,
                ConsumerIntervalModel.start_time < end,
            )
        )
        return int(result.scalar_one())


class ConsumerAggregateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, **kwargs) -> None:
        dialect = self._session.bind.dialect.name if self._session.bind else "sqlite"
        if dialect == "sqlite":
            stmt = sqlite_insert(ConsumerAggregateModel).values(**kwargs)
            stmt = stmt.on_conflict_do_update(
                index_elements=["consumer_id", "granularity", "period_start"],
                set_={k: v for k, v in kwargs.items() if k not in {"consumer_id", "granularity", "period_start"}},
            )
            await self._session.execute(stmt)
        else:
            existing = await self._session.execute(
                select(ConsumerAggregateModel).where(
                    ConsumerAggregateModel.consumer_id == kwargs["consumer_id"],
                    ConsumerAggregateModel.granularity == kwargs["granularity"],
                    ConsumerAggregateModel.period_start == kwargs["period_start"],
                )
            )
            row = existing.scalar_one_or_none()
            if row is None:
                self._session.add(ConsumerAggregateModel(**kwargs))
            else:
                for key, value in kwargs.items():
                    setattr(row, key, value)

    async def get_for_period(
        self,
        consumer_id: int,
        *,
        granularity: str,
        period_start: datetime,
    ) -> ConsumerAggregateModel | None:
        result = await self._session.execute(
            select(ConsumerAggregateModel).where(
                ConsumerAggregateModel.consumer_id == consumer_id,
                ConsumerAggregateModel.granularity == granularity,
                ConsumerAggregateModel.period_start == period_start,
            )
        )
        return result.scalar_one_or_none()

    async def list_since(
        self,
        consumer_id: int,
        *,
        granularity: str,
        start: datetime,
    ) -> list[ConsumerAggregateModel]:
        result = await self._session.execute(
            select(ConsumerAggregateModel)
            .where(
                ConsumerAggregateModel.consumer_id == consumer_id,
                ConsumerAggregateModel.granularity == granularity,
                ConsumerAggregateModel.period_start >= start,
            )
            .order_by(ConsumerAggregateModel.period_start)
        )
        return list(result.scalars().all())

    async def sum_total(self, consumer_id: int) -> dict:
        result = await self._session.execute(
            select(
                func.coalesce(func.sum(ConsumerAggregateModel.energy_kwh), 0.0),
                func.coalesce(func.sum(ConsumerAggregateModel.actual_cost_sek), 0.0),
                func.coalesce(func.sum(ConsumerAggregateModel.savings_sek), 0.0),
            ).where(
                ConsumerAggregateModel.consumer_id == consumer_id,
                ConsumerAggregateModel.granularity == "day",
            )
        )
        row = result.one()
        return {"energy_kwh": float(row[0]), "actual_cost_sek": float(row[1]), "savings_sek": float(row[2])}
