"""Solar Intelligence Engine persistence."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import (
    SolarDailyForecastSnapshotModel,
    SolarForecastHourlyModel,
    SolarModelRecordModel,
    SolarPerformanceDailyModel,
    SolarProviderHealthModel,
    SolarRadiationSampleModel,
    SolarTrainingSampleModel,
    SolarWeatherSnapshotModel,
)
from energy_core.solar_intelligence.types import (
    HourlyForecastPoint,
    IntelligenceForecast,
    PerformanceDaily,
    ProviderHealth,
    ProviderHealthStatus,
    RadiationSample,
    SampleQuality,
    SolarModelRecord,
    TrainingSample,
    WeatherSnapshot,
)


class SolarDailySnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, *, site_id: int, forecast_date: date, data: dict) -> None:
        row = await self._session.get(SolarDailyForecastSnapshotModel, (site_id, forecast_date))
        now = datetime.now(UTC)
        if row is None:
            self._session.add(
                SolarDailyForecastSnapshotModel(
                    site_id=site_id,
                    forecast_date=forecast_date,
                    snapshot_at=data.get("snapshot_at", now),
                    forecast_kwh_raw=data.get("forecast_kwh_raw"),
                    forecast_kwh_corrected=data.get("forecast_kwh_corrected"),
                    run_id=data.get("run_id"),
                    model_version=data.get("model_version", "solar-forecast-v2"),
                    weather_source=data.get("weather_source"),
                    created_at=now,
                )
            )
        else:
            row.snapshot_at = data.get("snapshot_at", now)
            row.forecast_kwh_raw = data.get("forecast_kwh_raw", row.forecast_kwh_raw)
            row.forecast_kwh_corrected = data.get("forecast_kwh_corrected", row.forecast_kwh_corrected)
            row.run_id = data.get("run_id", row.run_id)
            row.model_version = data.get("model_version", row.model_version)
            row.weather_source = data.get("weather_source", row.weather_source)

    async def get(self, site_id: int, forecast_date: date) -> dict | None:
        row = await self._session.get(SolarDailyForecastSnapshotModel, (site_id, forecast_date))
        if row is None:
            return None
        return {
            "forecast_kwh_raw": row.forecast_kwh_raw,
            "forecast_kwh_corrected": row.forecast_kwh_corrected,
            "snapshot_at": row.snapshot_at,
            "weather_source": row.weather_source,
        }


class SolarHourlyForecastRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_for_site(self, site_id: int, forecast: IntelligenceForecast) -> None:
        await self._session.execute(delete(SolarForecastHourlyModel).where(SolarForecastHourlyModel.site_id == site_id))
        for p in forecast.hourly:
            self._session.add(
                SolarForecastHourlyModel(
                    site_id=site_id,
                    timestamp=p.timestamp,
                    generated_at=forecast.generated_at,
                    physical_w=p.physical_w,
                    corrected_w=p.corrected_w,
                    lower_w=p.lower_w,
                    upper_w=p.upper_w,
                    engine_version=forecast.model_version,
                    confidence=p.confidence,
                    breakdown_json=json.dumps(p.breakdown) if p.breakdown else None,
                )
            )

    async def list_for_site(self, site_id: int, *, limit: int = 96) -> list[HourlyForecastPoint]:
        stmt = (
            select(SolarForecastHourlyModel)
            .where(SolarForecastHourlyModel.site_id == site_id)
            .order_by(SolarForecastHourlyModel.timestamp)
            .limit(limit)
        )
        rows = await self._session.scalars(stmt)
        return [
            HourlyForecastPoint(
                timestamp=r.timestamp,
                physical_w=r.physical_w,
                corrected_w=r.corrected_w,
                lower_w=r.lower_w,
                upper_w=r.upper_w,
                confidence=r.confidence,
                breakdown=json.loads(r.breakdown_json) if r.breakdown_json else {},
            )
            for r in rows
        ]


class SolarModelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_champion(self, site_id: int) -> SolarModelRecord | None:
        stmt = (
            select(SolarModelRecordModel)
            .where(SolarModelRecordModel.site_id == site_id, SolarModelRecordModel.role == "champion")
            .order_by(desc(SolarModelRecordModel.trained_at))
            .limit(1)
        )
        row = await self._session.scalar(stmt)
        return _model_to_domain(row) if row else None

    async def save_challenger(self, model: SolarModelRecord) -> None:
        self._session.add(
            SolarModelRecordModel(
                site_id=model.site_id,
                role=model.role,
                model_version=model.model_version,
                trained_at=model.trained_at,
                sample_count=model.sample_count,
                mae=model.mae,
                mape=model.mape,
                wape=model.wape,
                rmse=model.rmse,
                r2=model.r2,
                bias_pct=model.bias_pct,
                features_json=json.dumps(model.features),
                coefficients_json=json.dumps(model.coefficients),
            )
        )

    async def promote_challenger(self, site_id: int, model_id: int) -> None:
        await self._session.execute(
            delete(SolarModelRecordModel).where(
                SolarModelRecordModel.site_id == site_id,
                SolarModelRecordModel.role == "champion",
            )
        )
        row = await self._session.get(SolarModelRecordModel, model_id)
        if row:
            row.role = "champion"
            row.promoted_at = datetime.now(UTC)


def _model_to_domain(row: SolarModelRecordModel) -> SolarModelRecord:
    return SolarModelRecord(
        site_id=row.site_id,
        role=row.role,
        model_version=row.model_version,
        trained_at=row.trained_at,
        sample_count=row.sample_count,
        mae=row.mae,
        mape=row.mape,
        wape=row.wape,
        rmse=row.rmse,
        r2=row.r2,
        bias_pct=row.bias_pct,
        features=json.loads(row.features_json or "{}"),
        coefficients=json.loads(row.coefficients_json or "{}"),
    )


class SolarTrainingSampleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_samples(self, samples: list[TrainingSample]) -> int:
        count = 0
        for s in samples:
            stmt = select(SolarTrainingSampleModel).where(
                SolarTrainingSampleModel.site_id == s.site_id,
                SolarTrainingSampleModel.sample_date == s.sample_date,
                SolarTrainingSampleModel.hour_utc == s.hour_utc,
            )
            existing = await self._session.scalar(stmt)
            if existing:
                existing.actual_kwh = s.actual_kwh
                existing.physical_kwh = s.physical_kwh
                existing.quality = s.quality.value
            else:
                self._session.add(
                    SolarTrainingSampleModel(
                        site_id=s.site_id,
                        sample_date=s.sample_date,
                        hour_utc=s.hour_utc,
                        actual_kwh=s.actual_kwh,
                        physical_kwh=s.physical_kwh,
                        ghi_wm2=s.ghi_wm2,
                        dni_wm2=s.dni_wm2,
                        dhi_wm2=s.dhi_wm2,
                        poa_wm2=s.poa_wm2,
                        solar_elevation_deg=s.solar_elevation_deg,
                        cloud_cover_pct=s.cloud_cover_pct,
                        temperature_c=s.temperature_c,
                        quality=s.quality.value,
                        provenance=s.provenance,
                        created_at=datetime.now(UTC),
                    )
                )
            count += 1
        return count

    async def list_for_site(self, site_id: int, *, days: int = 90) -> list[TrainingSample]:
        since = date.today().fromordinal(date.today().toordinal() - days)
        stmt = (
            select(SolarTrainingSampleModel)
            .where(SolarTrainingSampleModel.site_id == site_id, SolarTrainingSampleModel.sample_date >= since)
            .order_by(SolarTrainingSampleModel.sample_date, SolarTrainingSampleModel.hour_utc)
        )
        rows = await self._session.scalars(stmt)
        return [_training_to_domain(r) for r in rows]


def _training_to_domain(row: SolarTrainingSampleModel) -> TrainingSample:
    return TrainingSample(
        site_id=row.site_id,
        sample_date=row.sample_date,
        hour_utc=row.hour_utc,
        actual_kwh=row.actual_kwh,
        physical_kwh=row.physical_kwh,
        ghi_wm2=row.ghi_wm2,
        dni_wm2=row.dni_wm2,
        dhi_wm2=row.dhi_wm2,
        poa_wm2=row.poa_wm2,
        solar_elevation_deg=row.solar_elevation_deg,
        cloud_cover_pct=row.cloud_cover_pct,
        temperature_c=row.temperature_c,
        quality=SampleQuality(row.quality),
        provenance=row.provenance,
    )


class SolarProviderHealthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_success(self, site_id: int, provider: str) -> None:
        await self._upsert(site_id, provider, success=True)

    async def record_failure(self, site_id: int, provider: str, error: str) -> None:
        await self._upsert(site_id, provider, success=False, error=error)

    async def list_for_site(self, site_id: int) -> list[ProviderHealth]:
        stmt = select(SolarProviderHealthModel).where(SolarProviderHealthModel.site_id == site_id)
        rows = await self._session.scalars(stmt)
        return [
            ProviderHealth(
                provider=r.provider,
                status=ProviderHealthStatus(r.status),
                last_success_at=r.last_success_at,
                last_failure_at=r.last_failure_at,
                last_error=r.last_error,
                consecutive_failures=r.consecutive_failures,
            )
            for r in rows
        ]

    async def _upsert(self, site_id: int, provider: str, *, success: bool, error: str | None = None) -> None:
        row = await self._session.get(SolarProviderHealthModel, (site_id, provider))
        now = datetime.now(UTC)
        if row is None:
            row = SolarProviderHealthModel(site_id=site_id, provider=provider)
            self._session.add(row)
        if success:
            row.status = ProviderHealthStatus.HEALTHY.value
            row.last_success_at = now
            row.consecutive_failures = 0
            row.last_error = None
        else:
            row.status = ProviderHealthStatus.DEGRADED.value
            row.last_failure_at = now
            row.last_error = (error or "")[:256]
            row.consecutive_failures = (row.consecutive_failures or 0) + 1
        row.updated_at = now


class SolarPerformanceDailyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, site_id: int, perf: PerformanceDaily) -> None:
        row = await self._session.get(SolarPerformanceDailyModel, (site_id, perf.performance_date))
        now = datetime.now(UTC)
        if row is None:
            self._session.add(
                SolarPerformanceDailyModel(
                    site_id=site_id,
                    performance_date=perf.performance_date,
                    actual_kwh=perf.actual_kwh,
                    expected_kwh=perf.expected_kwh,
                    weather_normalized_kwh=perf.weather_normalized_kwh,
                    performance_ratio=perf.performance_ratio,
                    anomaly_score=perf.anomaly_score,
                    anomaly_flag=perf.anomaly_flag,
                    updated_at=now,
                )
            )
        else:
            row.actual_kwh = perf.actual_kwh
            row.expected_kwh = perf.expected_kwh
            row.weather_normalized_kwh = perf.weather_normalized_kwh
            row.performance_ratio = perf.performance_ratio
            row.anomaly_score = perf.anomaly_score
            row.anomaly_flag = perf.anomaly_flag
            row.updated_at = now

    async def list_for_site(self, site_id: int, *, days: int = 90) -> list[PerformanceDaily]:
        since = date.today().fromordinal(date.today().toordinal() - days)
        stmt = (
            select(SolarPerformanceDailyModel)
            .where(SolarPerformanceDailyModel.site_id == site_id, SolarPerformanceDailyModel.performance_date >= since)
            .order_by(SolarPerformanceDailyModel.performance_date)
        )
        rows = await self._session.scalars(stmt)
        return [
            PerformanceDaily(
                performance_date=r.performance_date,
                actual_kwh=r.actual_kwh,
                expected_kwh=r.expected_kwh,
                weather_normalized_kwh=r.weather_normalized_kwh,
                performance_ratio=r.performance_ratio,
                anomaly_score=r.anomaly_score,
                anomaly_flag=r.anomaly_flag,
            )
            for r in rows
        ]


class SolarRadiationCacheRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_samples(self, site_id: int, samples: list[RadiationSample]) -> None:
        now = datetime.now(UTC)
        for s in samples:
            row = await self._session.get(
                SolarRadiationSampleModel, (site_id, s.ts_utc, s.parameter, s.provider)
            )
            if row is None:
                self._session.add(
                    SolarRadiationSampleModel(
                        site_id=site_id,
                        ts_utc=s.ts_utc,
                        parameter=s.parameter,
                        provider=s.provider,
                        value_wm2=s.value_wm2,
                        quality=s.quality.value,
                        fetched_at=now,
                    )
                )


class SolarWeatherSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_snapshots(self, site_id: int, snapshots: list[WeatherSnapshot]) -> None:
        now = datetime.now(UTC)
        for s in snapshots:
            row = await self._session.get(SolarWeatherSnapshotModel, (site_id, s.ts_utc, s.provider))
            if row is None:
                self._session.add(
                    SolarWeatherSnapshotModel(
                        site_id=site_id,
                        ts_utc=s.ts_utc,
                        provider=s.provider,
                        temperature_c=s.temperature_c,
                        cloud_cover_pct=s.cloud_cover_pct,
                        precipitation_mm=s.precipitation_mm,
                        humidity_pct=s.humidity_pct,
                        wind_speed_ms=s.wind_speed_ms,
                        fetched_at=now,
                    )
                )
