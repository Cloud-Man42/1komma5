"""Solar Intelligence Engine API routes."""

from __future__ import annotations

from datetime import UTC, datetime

from app.deps import get_app_settings, get_db_session
from app.schemas import (
    SolarHourlyForecastResponse,
    SolarHourlyPointResponse,
    SolarIntelligenceForecastResponse,
    SolarModelMetricsResponse,
    SolarModelResponse,
    SolarPerformanceResponse,
    SolarProviderStatusResponse,
    SolarRadiationResponse,
)
from energy_core.db.repositories import SiteRepository
from energy_core.db.solar_forecast_repo import SolarForecastModelProfileRepository, SolarSiteConfigRepository
from energy_core.db.solar_intelligence_repo import (
    SolarHourlyForecastRepository,
    SolarModelRepository,
    SolarPerformanceDailyRepository,
    SolarProviderHealthRepository,
)
from energy_core.solar_forecast.calibration import metrics_insufficient
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
):
    site = await _get_site(session, slug)
    await _require_intelligence(session, site)
    records = await SolarPerformanceDailyRepository(session).list_for_site(site.id, days=90)
    return SolarPerformanceResponse(
        site_slug=slug,
        days=[
            {
                "date": r.performance_date.isoformat(),
                "actual_kwh": r.actual_kwh,
                "expected_kwh": r.expected_kwh,
                "performance_ratio": r.performance_ratio,
                "anomaly_flag": r.anomaly_flag,
            }
            for r in records
        ],
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
    rows = await session.scalars(stmt)
    samples = [{"ts": r.ts_utc.isoformat(), "parameter": r.parameter, "value_wm2": r.value_wm2} for r in rows]
    return SolarRadiationResponse(site_slug=slug, provider="smhi-strang", samples=samples)


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
