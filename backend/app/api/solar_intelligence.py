"""Solar Intelligence Engine API routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.deps import get_app_settings, get_db_session
from app.schemas import (
    DmiForecastPointResponse,
    DmiForecastResponse,
    SolarHourlyForecastResponse,
    SolarHourlyPointResponse,
    SolarIntelligenceForecastResponse,
    SolarModelMetricsResponse,
    SolarModelResponse,
    SolarPerformanceResponse,
    SolarProviderStatusResponse,
    SolarRadiationResponse,
)
from energy_core.db.repositories import EnergyReadingRepository, SiteRepository
from energy_core.db.solar_forecast_repo import (
    SolarForecastModelProfileRepository,
    SolarForecastObservationRepository,
    SolarForecastRepository,
    SolarSiteConfigRepository,
    _to_domain_config,
)
from energy_core.db.solar_intelligence_repo import (
    SolarHourlyForecastRepository,
    SolarModelRepository,
    SolarPerformanceDailyRepository,
    SolarProviderHealthRepository,
)
from energy_core.solar_forecast.calibration import metrics_insufficient
from energy_core.solar_forecast.coordinator import SolarForecastCoordinator
from energy_core.solar_forecast.rollup_queries import actual_solar_kwh_today
from energy_core.solar_forecast.performance import (
    build_performance_summary,
    estimate_raw_so_far_from_totals,
    performance_days_from_observations,
    raw_forecast_so_far,
)
from energy_core.solar_intelligence.provider_factory import resolve_country_code
from energy_core.solar_intelligence.service import SolarIntelligenceCoordinator
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["solar-intelligence"])


async def _get_site(session: AsyncSession, slug: str):
    repo = SiteRepository(session)
    site = await repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")
    return site


async def _require_solar_enabled(session: AsyncSession, site):
    config_repo = SolarSiteConfigRepository(session)
    record = await config_repo.get(site.id, timezone=site.timezone)
    if record is None or not record.enabled:
        raise HTTPException(status_code=404, detail="Solar forecast not enabled")
    return record


async def _require_intelligence(session: AsyncSession, site):
    config_repo = SolarSiteConfigRepository(session)
    record = await config_repo.get(site.id, timezone=site.timezone)
    if record is None or not record.enabled:
        raise HTTPException(status_code=404, detail="Solar forecast not enabled")
    if not record.solar_intelligence_enabled:
        raise HTTPException(status_code=503, detail="Solar Intelligence not enabled for this site")
    return record


@router.get("/sites/{slug}/solar/forecast/hourly", response_model=SolarHourlyForecastResponse)
async def get_hourly_forecast(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
):
    site = await _get_site(session, slug)
    await _require_intelligence(session, site)
    points = await SolarHourlyForecastRepository(session).list_for_site(site.id)
    return SolarHourlyForecastResponse(
        site_slug=slug,
        points=[
            SolarHourlyPointResponse(
                timestamp=p.timestamp,
                physical_w=p.physical_w,
                corrected_w=p.corrected_w,
                lower_w=p.lower_w,
                upper_w=p.upper_w,
                confidence=p.confidence,
            )
            for p in points
        ],
    )


@router.get("/sites/{slug}/solar/performance", response_model=SolarPerformanceResponse)
async def get_performance(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    settings=Depends(get_app_settings),
):
    site = await _get_site(session, slug)
    await _require_solar_enabled(session, site)

    coordinator = SolarForecastCoordinator(settings)
    await coordinator.evaluate_site_observations(session, site)

    perf_repo = SolarPerformanceDailyRepository(session)
    records = await perf_repo.list_for_site(site.id, days=90)
    if records:
        days = [
            {
                "date": r.performance_date.isoformat(),
                "actual_kwh": r.actual_kwh,
                "expected_kwh": r.expected_kwh,
                "performance_ratio": r.performance_ratio,
                "anomaly_flag": r.anomaly_flag,
            }
            for r in records
            if r.performance_ratio is not None
        ]
    else:
        observations = await SolarForecastObservationRepository(session).list_for_site(site.id, limit=90)
        days = performance_days_from_observations(observations)

    now = datetime.now(UTC)
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    actual_today = await actual_solar_kwh_today(
        reading_repo,
        site.id,
        timezone=site.timezone,
        now=now,
    )

    raw_so_far = None
    forecast = await SolarForecastRepository(session).get_latest(site.id)
    if forecast is not None:
        from energy_core.solar_forecast.day_metrics import compute_solar_day_metrics

        day_metrics = compute_solar_day_metrics(forecast, timezone=site.timezone, now=now)
        raw_so_far, _ = raw_forecast_so_far(forecast, timezone=site.timezone, now=now)
        estimated = estimate_raw_so_far_from_totals(
            raw_today_kwh=getattr(forecast, "raw_forecast_today_kwh", None),
            corrected_so_far_kwh=day_metrics.forecast_so_far_kwh,
            corrected_today_kwh=day_metrics.expected_today_kwh,
        )
        if estimated is not None and (raw_so_far is None or raw_so_far < estimated * 0.5):
            raw_so_far = estimated

    summary = build_performance_summary(
        days,
        actual_today_kwh=actual_today,
        raw_forecast_so_far_kwh=raw_so_far,
        settings=settings,
    )
    await session.commit()

    return SolarPerformanceResponse(
        site_slug=slug,
        days=days,
        headline_ratio=summary["headline_ratio"],
        today_deviation_pct=summary["today_deviation_pct"],
        week_avg=summary["week_avg"],
        month_avg=summary["month_avg"],
        quarter_avg=summary["quarter_avg"],
        ytd_avg=summary["ytd_avg"],
        raw_forecast_so_far_kwh=raw_so_far,
        actual_today_kwh=round(actual_today, 3),
    )


@router.get("/sites/{slug}/solar/radiation", response_model=SolarRadiationResponse)
async def get_radiation(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
):
    site = await _get_site(session, slug)
    record = await _require_intelligence(session, site)
    from sqlalchemy import select
    from energy_core.db.models import SolarRadiationSampleModel

    today = datetime.now(UTC).date()
    stmt = (
        select(SolarRadiationSampleModel)
        .where(SolarRadiationSampleModel.site_id == site.id)
        .order_by(SolarRadiationSampleModel.ts_utc.desc())
        .limit(24)
    )
    rows = list(await session.scalars(stmt))
    samples = [{"ts": r.ts_utc.isoformat(), "parameter": r.parameter, "value_wm2": r.value_wm2} for r in rows]
    provider = rows[0].provider if rows else None
    if not provider:
        domain = _to_domain_config(record)
        country = resolve_country_code(record.country_code, latitude=domain.latitude, longitude=domain.longitude)
        provider = "dmi-harmonie" if country == "DK" else "smhi-strang"
    return SolarRadiationResponse(site_slug=slug, provider=provider, samples=samples)


@router.get("/sites/{slug}/solar/dmi/forecast", response_model=DmiForecastResponse)
async def get_dmi_forecast(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    settings=Depends(get_app_settings),
):
    site = await _get_site(session, slug)
    record = await _require_solar_enabled(session, site)
    domain = _to_domain_config(record)
    country = resolve_country_code(record.country_code, latitude=domain.latitude, longitude=domain.longitude)
    if country != "DK":
        raise HTTPException(
            status_code=422,
            detail="DMI forecast is only available for Danish sites",
        )

    now = datetime.now(UTC)
    to_ts = now + timedelta(hours=settings.solar_forecast_horizon_hours)
    coord = SolarIntelligenceCoordinator(settings)
    rows = await coord.fetch_dmi_forecast(
        latitude=domain.latitude,
        longitude=domain.longitude,
        from_ts=now,
        to_ts=to_ts,
    )
    return DmiForecastResponse(
        site_slug=slug,
        country_code=country,
        points=[
            DmiForecastPointResponse(
                timestamp=datetime.fromisoformat(row["timestamp"]),
                ghi_wm2=row.get("ghi_wm2"),
                dhi_wm2=row.get("dhi_wm2"),
                temperature_c=row.get("temperature_c"),
                cloud_cover_pct=row.get("cloud_cover_pct"),
                precipitation_mm=row.get("precipitation_mm"),
                humidity_pct=row.get("humidity_pct"),
                wind_speed_ms=row.get("wind_speed_ms"),
            )
            for row in rows
        ],
    )


@router.get("/sites/{slug}/solar/model", response_model=SolarModelResponse)
async def get_model(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
):
    site = await _get_site(session, slug)
    await _require_intelligence(session, site)
    champion = await SolarModelRepository(session).get_champion(site.id)
    if champion is None:
        return SolarModelResponse(site_slug=slug, model_version=None, sample_count=0)
    return SolarModelResponse(
        site_slug=slug,
        model_version=champion.model_version,
        sample_count=champion.sample_count,
        trained_at=champion.trained_at,
        role=champion.role,
    )


@router.get("/sites/{slug}/solar/model/metrics", response_model=SolarModelMetricsResponse)
async def get_model_metrics(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    settings=Depends(get_app_settings),
):
    site = await _get_site(session, slug)
    await _require_intelligence(session, site)
    profile = await SolarForecastModelProfileRepository(session).get(site.id)
    champion = await SolarModelRepository(session).get_champion(site.id)
    insufficient = metrics_insufficient(profile, settings)
    reason = None
    if insufficient:
        if profile.historical_samples <= 0:
            reason = "no_training_samples"
        elif profile.model_state.value in ("NO_DATA", "LEARNING"):
            reason = "model_learning"
        else:
            reason = "insufficient_samples"
    return SolarModelMetricsResponse(
        site_slug=slug,
        model_version=champion.model_version if champion else profile.model_version,
        mae=champion.mae if champion else profile.mae_30d,
        mape=champion.mape if champion else profile.mape_30d,
        wape=champion.wape if champion else profile.wape_30d,
        rmse=champion.rmse if champion else profile.rmse_30d,
        r2=champion.r2 if champion else profile.r2_30d,
        bias_pct=champion.bias_pct if champion else profile.bias_30d,
        metrics_insufficient=insufficient,
        insufficient_reason=reason,
        historical_samples=profile.historical_samples,
    )


@router.get("/sites/{slug}/solar/provider-status", response_model=SolarProviderStatusResponse)
async def get_provider_status(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
):
    site = await _get_site(session, slug)
    await _require_intelligence(session, site)
    health = await SolarProviderHealthRepository(session).list_for_site(site.id)
    return SolarProviderStatusResponse(
        site_slug=slug,
        providers=[
            {
                "provider": h.provider,
                "status": h.status.value,
                "last_success_at": h.last_success_at.isoformat() if h.last_success_at else None,
                "last_failure_at": h.last_failure_at.isoformat() if h.last_failure_at else None,
                "consecutive_failures": h.consecutive_failures,
            }
            for h in health
        ],
    )


@router.post("/sites/{slug}/solar/intelligence/backfill")
async def trigger_backfill(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    settings=Depends(get_app_settings),
):
    site = await _get_site(session, slug)
    await _require_intelligence(session, site)
    coord = SolarIntelligenceCoordinator(settings)
    count = await coord.run_backfill(session, site, days=60)
    await session.commit()
    return {"site_slug": slug, "samples_upserted": count}


@router.post("/sites/{slug}/solar/intelligence/train")
async def trigger_train(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    settings=Depends(get_app_settings),
):
    site = await _get_site(session, slug)
    await _require_intelligence(session, site)
    coord = SolarIntelligenceCoordinator(settings)
    ok = await coord.train_model(session, site)
    await session.commit()
    return {"site_slug": slug, "trained": ok}


@router.get("/sites/{slug}/solar/intelligence/forecast", response_model=SolarIntelligenceForecastResponse)
async def get_intelligence_forecast(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    settings=Depends(get_app_settings),
):
    site = await _get_site(session, slug)
    await _require_intelligence(session, site)
    hourly = await SolarHourlyForecastRepository(session).list_for_site(site.id)
    if not hourly:
        coord = SolarIntelligenceCoordinator(settings)
        await coord.refresh_site(session, site)
        await session.commit()
        hourly = await SolarHourlyForecastRepository(session).list_for_site(site.id)

    from zoneinfo import ZoneInfo

    tz = ZoneInfo(site.timezone)
    today = datetime.now(UTC).astimezone(tz).date()
    today_kwh = sum(p.corrected_w / 1000.0 for p in hourly if p.timestamp.astimezone(tz).date() == today)
    return SolarIntelligenceForecastResponse(
        site_slug=slug,
        expected_today_kwh=round(today_kwh, 2),
        status="HEALTHY" if hourly else "UNAVAILABLE",
        point_count=len(hourly),
    )
