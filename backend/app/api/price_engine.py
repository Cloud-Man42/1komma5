"""Price engine and energy strategy API routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.deps import get_db_session, get_site_repository
from app.schemas import (
    BatteryOpportunityResponse,
    EnergyStrategyCurrentResponse,
    EvRecommendationResponse,
    PriceEngineCurrentResponse,
    PriceEngineDayResponse,
    PriceEngineRangeResponse,
    PriceEngineStatusResponse,
    PricePeriodResponse,
)
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.models import EnergyReadingModel
from energy_core.db.price_period_repo import PriceEngineStateRepository
from energy_core.db.repositories import SiteRepository
from energy_core.config import get_settings
from energy_core.cache.service import current_price_cache_key, get_cache_service
from energy_core.energy_optimizer.advisor import build_battery_opportunity_advice
from energy_core.price_engine.engine import EmicPriceEngine
from energy_core.price_engine.ev_recommendations import build_ev_recommendations
from energy_core.price_engine.observability import get_engine_status
from energy_core.price_engine.peak_protection import assess_peak_protection
from energy_core.price_engine.periods import local_today
from energy_core.price_engine.strategy import build_strategy_snapshot
from energy_core.price_engine.types import PricePeriod
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["price-engine"])


def _period_response(period: PricePeriod) -> PricePeriodResponse:
    return PricePeriodResponse(
        period_start=period.period_start,
        period_end=period.period_end,
        price_area=period.price_area.value,
        currency=period.currency.value,
        market_price_sek_kwh=period.market_price_sek_kwh,
        import_price_sek_kwh=period.import_price_sek_kwh,
        export_price_sek_kwh=period.export_price_sek_kwh,
        source=period.source.value,
        quality=period.quality.value,
        is_estimated=period.is_estimated,
        components=period.components,
    )


async def _engine(session: AsyncSession) -> EmicPriceEngine:
    from energy_core.config import get_settings

    settings = get_settings()
    return EmicPriceEngine(session, is_sqlite=settings.is_sqlite)


async def _latest_reading(session: AsyncSession, site_id: int) -> EnergyReadingModel | None:
    return await session.scalar(
        select(EnergyReadingModel)
        .where(EnergyReadingModel.site_id == site_id)
        .order_by(EnergyReadingModel.recorded_at.desc())
        .limit(1)
    )


@router.get("/sites/{slug}/price-engine/current", response_model=PriceEngineCurrentResponse)
async def get_price_engine_current(
    slug: str,
    site_repo: SiteRepository = Depends(get_site_repository),
    session: AsyncSession = Depends(get_db_session),
) -> PriceEngineCurrentResponse:
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site '{slug}' not found")

    settings = get_settings()
    cache = get_cache_service(settings)
    cache_key = current_price_cache_key(site.id)
    ttl_seconds = settings.current_price_redis_cache_ttl_seconds

    cached = await cache.get(cache_key)
    if cached is not None:
        return PriceEngineCurrentResponse.model_validate(cached)

    async def factory() -> dict:
        engine = await _engine(session)
        period = await engine.get_current(site.id, site.timezone)
        return PriceEngineCurrentResponse(
            slug=slug,
            timezone=site.timezone,
            period=_period_response(period) if period else None,
        ).model_dump(mode="json")

    payload = await cache.get_or_set(cache_key, factory, ttl_seconds=ttl_seconds)
    return PriceEngineCurrentResponse.model_validate(payload)


@router.get("/sites/{slug}/price-engine/today", response_model=PriceEngineDayResponse)
async def get_price_engine_today(
    slug: str,
    site_repo: SiteRepository = Depends(get_site_repository),
    session: AsyncSession = Depends(get_db_session),
) -> PriceEngineDayResponse:
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site '{slug}' not found")

    engine = await _engine(session)
    day = local_today(site.timezone)
    periods = await engine.get_day(site.id, day, site.timezone)
    return PriceEngineDayResponse(
        slug=slug,
        timezone=site.timezone,
        day=day,
        periods=[_period_response(p) for p in periods],
    )


@router.get("/sites/{slug}/price-engine/tomorrow", response_model=PriceEngineDayResponse)
async def get_price_engine_tomorrow(
    slug: str,
    site_repo: SiteRepository = Depends(get_site_repository),
    session: AsyncSession = Depends(get_db_session),
) -> PriceEngineDayResponse:
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site '{slug}' not found")

    engine = await _engine(session)
    day = local_today(site.timezone) + timedelta(days=1)
    periods = await engine.get_day(site.id, day, site.timezone)
    return PriceEngineDayResponse(
        slug=slug,
        timezone=site.timezone,
        day=day,
        periods=[_period_response(p) for p in periods],
    )


@router.get("/sites/{slug}/price-engine/range", response_model=PriceEngineRangeResponse)
async def get_price_engine_range(
    slug: str,
    from_time: datetime = Query(alias="from"),
    to_time: datetime = Query(alias="to"),
    site_repo: SiteRepository = Depends(get_site_repository),
    session: AsyncSession = Depends(get_db_session),
) -> PriceEngineRangeResponse:
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site '{slug}' not found")

    if from_time.tzinfo is None:
        from_time = from_time.replace(tzinfo=UTC)
    if to_time.tzinfo is None:
        to_time = to_time.replace(tzinfo=UTC)
    if to_time <= from_time:
        raise HTTPException(status_code=422, detail="'to' must be after 'from'")

    engine = await _engine(session)
    periods = await engine.get_range(site.id, start=from_time, end=to_time)
    return PriceEngineRangeResponse(
        slug=slug,
        timezone=site.timezone,
        from_time=from_time,
        to_time=to_time,
        periods=[_period_response(p) for p in periods],
    )


@router.get("/sites/{slug}/price-engine/status", response_model=PriceEngineStatusResponse)
async def get_price_engine_status(
    slug: str,
    site_repo: SiteRepository = Depends(get_site_repository),
    session: AsyncSession = Depends(get_db_session),
) -> PriceEngineStatusResponse:
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site '{slug}' not found")

    state_repo = PriceEngineStateRepository(session)
    state = await get_engine_status(state_repo, site.id)
    return PriceEngineStatusResponse(
        slug=slug,
        last_market_refresh_at=state.last_market_refresh_at,
        last_import_refresh_at=state.last_import_refresh_at,
        last_export_refresh_at=state.last_export_refresh_at,
        last_error=state.last_error,
        missing_periods_count=state.missing_periods_count,
        data_age_seconds=state.data_age_seconds,
        optimization_mode=state.optimization_mode.value,
    )


@router.get("/sites/{slug}/energy-strategy/current", response_model=EnergyStrategyCurrentResponse)
async def get_energy_strategy_current(
    slug: str,
    site_repo: SiteRepository = Depends(get_site_repository),
    session: AsyncSession = Depends(get_db_session),
) -> EnergyStrategyCurrentResponse:
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site '{slug}' not found")

    engine = await _engine(session)
    current = await engine.get_current(site.id, site.timezone)
    today = local_today(site.timezone)
    tomorrow = today + timedelta(days=1)
    horizon = (
        await engine.get_day(site.id, today, site.timezone)
        + await engine.get_day(site.id, tomorrow, site.timezone)
    )
    latest_reading = await _latest_reading(session, site.id)
    battery_soc = latest_reading.battery_soc_pct if latest_reading else None
    mode = await engine.get_status(site.id)

    chargers = await EvChargerRepository(session).list_for_site(site.id)
    peak_hint = assess_peak_protection(
        main_fuse_a=site.main_fuse_a,
        safety_margin_a=site.safety_margin_a or 2.0,
        grid_import_w=latest_reading.grid_import_w if latest_reading else None,
    )
    ev_recs = build_ev_recommendations(
        site=site,
        chargers=tuple(chargers),
        horizon=horizon,
        current_import_sek_kwh=current.import_price_sek_kwh if current else None,
    )

    snapshot = build_strategy_snapshot(
        site_slug=slug,
        timezone=site.timezone,
        current=current,
        horizon=horizon,
        battery_soc_pct=battery_soc,
        optimization_mode=mode,
        peak_hint=peak_hint,
        ev_recommendations=ev_recs,
    )

    return EnergyStrategyCurrentResponse(
        slug=slug,
        timezone=site.timezone,
        period_start=snapshot.period_start,
        market_price_sek_kwh=snapshot.market_price_sek_kwh,
        import_price_sek_kwh=snapshot.import_price_sek_kwh,
        export_price_sek_kwh=snapshot.export_price_sek_kwh,
        market_quality=snapshot.market_quality.value,
        import_quality=snapshot.import_quality.value,
        export_quality=snapshot.export_quality.value,
        battery_soc_pct=snapshot.battery_soc_pct,
        strategy_state=snapshot.strategy_state.value,
        confidence=snapshot.confidence,
        reason=snapshot.reason,
        reason_sv=snapshot.reason_sv,
        next_peak_at=snapshot.next_peak_at,
        next_peak_import_sek_kwh=snapshot.next_peak_import_sek_kwh,
        optimization_mode=snapshot.optimization_mode.value,
        expected_saving_today_sek=snapshot.expected_saving_today_sek,
        recommended_reserve_soc_pct=snapshot.recommended_reserve_soc_pct,
        recommended_action=snapshot.recommended_action,
        eov_value_sek_kwh=snapshot.eov_value_sek_kwh,
        grid_surcharge_sek_kwh=snapshot.grid_surcharge_sek_kwh,
        fuse_headroom_a=snapshot.fuse_headroom_a,
        fuse_utilization_pct=snapshot.fuse_utilization_pct,
        ev_recommendations=[
            EvRecommendationResponse(
                charger_id=rec.charger_id,
                charger_name=rec.charger_name,
                window_start=rec.window_start,
                window_end=rec.window_end,
                avg_import_sek_kwh=rec.avg_import_sek_kwh,
                current_import_sek_kwh=rec.current_import_sek_kwh,
                estimated_saving_sek=rec.estimated_saving_sek,
                reason_sv=rec.reason_sv,
            )
            for rec in snapshot.ev_recommendations
        ],
    )


@router.get("/sites/{slug}/battery-opportunity", response_model=BatteryOpportunityResponse)
async def get_battery_opportunity(
    slug: str,
    site_repo: SiteRepository = Depends(get_site_repository),
    session: AsyncSession = Depends(get_db_session),
) -> BatteryOpportunityResponse:
    from energy_core.price_engine.strategy_service import build_current_strategy_for_slug

    settings = get_settings()
    snapshot = await build_current_strategy_for_slug(session, slug, is_sqlite=settings.is_sqlite)
    if snapshot is None:
        raise HTTPException(status_code=404, detail=f"Site '{slug}' not found")

    site = await site_repo.get_by_slug(slug)
    assert site is not None
    advice = build_battery_opportunity_advice(snapshot)
    return BatteryOpportunityResponse(
        slug=slug,
        timezone=site.timezone,
        available=advice.available,
        monitor_only=advice.monitor_only,
        unavailable_reason_sv=advice.unavailable_reason_sv,
        action=advice.action,
        action_label_sv=advice.action_label_sv,
        headline_sv=advice.headline_sv,
        reason_sv=advice.reason_sv,
        confidence=advice.confidence,
        battery_soc_pct=advice.battery_soc_pct,
        recommended_reserve_soc_pct=advice.recommended_reserve_soc_pct,
        expected_value_sek_kwh=advice.expected_value_sek_kwh,
        next_peak_at=advice.next_peak_at,
        next_peak_import_sek_kwh=advice.next_peak_import_sek_kwh,
        optimization_mode=advice.optimization_mode,
        strategy_state=advice.strategy_state,
    )
