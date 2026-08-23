"""Arctic Spa API routes."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta

from app.deps import get_db_session
from app.schemas import (
    SpaConfigResponse,
    SpaConfigUpdateRequest,
    SpaConnectionTestResponse,
    SpaEnergyPeriodResponse,
    SpaHealthResponse,
    SpaHistoryPoint,
    SpaHistoryResponse,
    SpaStatusResponse,
)
from energy_core.config import get_settings
from energy_core.consumer_accounting.aggregator import period_bounds
from energy_core.db.consumer_repo import (
    ConsumerAggregateRepository,
    ConsumerIntervalRepository,
    ConsumerRepository,
    ConsumerSampleRepository,
)
from energy_core.integrations.arctic_spa.config import ArcticSpaConfiguration, mask_api_key
from energy_core.integrations.arctic_spa.service import ArcticSpaService
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["spa"])
logger = logging.getLogger(__name__)


async def _get_spa_context(session: AsyncSession, slug: str):
    from energy_core.db.repositories import SiteRepository

    site_repo = SiteRepository(session)
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    repo = ConsumerRepository(session)
    row = await repo.get_spa_by_site_slug(slug)
    if row is None:
        consumer, config = await repo.get_or_create_spa(site)
        await session.flush()
        return site, consumer, config
    consumer, config, _site = row
    return site, consumer, config


def _period_range(period: str, timezone: str) -> tuple[datetime, datetime, str]:
    now = datetime.now(UTC)
    if period == "today":
        start, end = period_bounds(granularity="day", reference=now, timezone=timezone)
        return start, end, "day"
    if period == "week":
        start = now - timedelta(days=7)
        return start, now, "day"
    if period == "month":
        start, end = period_bounds(granularity="month", reference=now, timezone=timezone)
        return start, end, "month"
    if period == "year":
        start, end = period_bounds(granularity="year", reference=now, timezone=timezone)
        return start, end, "year"
    if period == "rolling12":
        return now - timedelta(days=365), now, "month"
    if period == "total":
        return datetime(1970, 1, 1, tzinfo=UTC), now, "day"
    raise HTTPException(status_code=422, detail="Invalid period")


def _build_period_response(period: str, totals: dict) -> SpaEnergyPeriodResponse:
    energy = totals.get("energy_kwh", 0.0) or 0.0
    actual = totals.get("actual_cost_sek", 0.0) or 0.0
    reference = totals.get("reference_cost_sek")
    savings = totals.get("savings_sek")
    renewable = (totals.get("solar_direct_kwh", 0.0) or 0.0) + (
        totals.get("solar_battery_kwh", 0.0) or 0.0
    )
    own_pct = round(100.0 * renewable / energy, 1) if energy > 0 else None
    savings_pct = round(100.0 * savings / reference, 1) if savings and reference else None
    avg_cost = round(actual / energy, 4) if energy > 0 else None
    return SpaEnergyPeriodResponse(
        period=period,
        energy_kwh=round(energy, 3),
        actual_cost_sek=round(actual, 2),
        reference_cost_sek=round(reference, 2) if reference else None,
        savings_sek=round(savings, 2) if savings else None,
        savings_pct=savings_pct,
        own_energy_pct=own_pct,
        solar_direct_kwh=round(totals.get("solar_direct_kwh", 0.0) or 0.0, 3),
        solar_battery_kwh=round(totals.get("solar_battery_kwh", 0.0) or 0.0, 3),
        grid_battery_kwh=round(totals.get("grid_battery_kwh", 0.0) or 0.0, 3),
        grid_direct_kwh=round(totals.get("grid_direct_kwh", 0.0) or 0.0, 3),
        unknown_kwh=round(totals.get("unknown_kwh", 0.0) or 0.0, 3),
        max_power_w=totals.get("max_power_w"),
        avg_power_w=totals.get("avg_power_w"),
        heater_runtime_hours=round((totals.get("heater_runtime_seconds", 0.0) or 0.0) / 3600.0, 2),
        pump_runtime_hours=round((totals.get("pump_runtime_seconds", 0.0) or 0.0) / 3600.0, 2),
        avg_cost_sek_kwh=avg_cost,
        has_data=energy > 0,
    )


@router.get("/sites/{slug}/spa/status", response_model=SpaStatusResponse)
async def get_spa_status(
    slug: str, session: AsyncSession = Depends(get_db_session)
) -> SpaStatusResponse:
    site, consumer, config = await _get_spa_context(session, slug)
    sample_repo = ConsumerSampleRepository(session)
    latest = await sample_repo.get_latest(consumer.id)
    status_payload = {}
    if config.last_status_json:
        try:
            status_payload = json.loads(config.last_status_json)
        except json.JSONDecodeError:
            status_payload = {}
    from energy_core.integrations.arctic_spa.models import ArcticSpaStatus

    parsed = ArcticSpaStatus.from_api(status_payload) if status_payload else None
    return SpaStatusResponse(
        consumer_id=consumer.id,
        site_slug=slug,
        online=bool(parsed.connected) if parsed else False,
        water_temperature_c=parsed.temperature_c
        if parsed
        else (latest.water_temperature_c if latest else None),
        set_temperature_c=parsed.setpoint_c
        if parsed
        else (latest.set_temperature_c if latest else None),
        heater_active=parsed.heater_active if parsed else bool(latest and latest.heater_active),
        pump_label=parsed.primary_pump_label if parsed else "Pump: Av",
        filter_status=parsed.filter_status
        if parsed
        else (latest.filter_status if latest else None),
        errors=list(parsed.errors) if parsed else [],
        current_power_w=latest.power_w if latest else None,
        last_updated=config.last_status_at or (latest.recorded_at if latest else None),
        data_quality=latest.quality if latest else "MISSING",
        integration_enabled=config.integration_enabled,
    )


@router.get("/sites/{slug}/spa/energy/{period}", response_model=SpaEnergyPeriodResponse)
async def get_spa_energy_period(
    slug: str,
    period: str,
    session: AsyncSession = Depends(get_db_session),
) -> SpaEnergyPeriodResponse:
    site, consumer, _config = await _get_spa_context(session, slug)
    start, end, _gran = _period_range(period, consumer.timezone or site.timezone)
    interval_repo = ConsumerIntervalRepository(session)
    totals = await interval_repo.sum_for_period(consumer.id, start=start, end=end)
    if not totals:
        return _build_period_response(period, {})
    return _build_period_response(period, totals)


@router.get("/sites/{slug}/spa/energy/today", response_model=SpaEnergyPeriodResponse)
async def get_spa_energy_today(
    slug: str, session: AsyncSession = Depends(get_db_session)
) -> SpaEnergyPeriodResponse:
    return await get_spa_energy_period(slug, "today", session)


@router.get("/sites/{slug}/spa/history", response_model=SpaHistoryResponse)
async def get_spa_history(
    slug: str,
    period: str = Query(default="today"),
    session: AsyncSession = Depends(get_db_session),
) -> SpaHistoryResponse:
    site, consumer, _config = await _get_spa_context(session, slug)
    start, end, _gran = _period_range(period, consumer.timezone or site.timezone)
    interval_repo = ConsumerIntervalRepository(session)
    intervals = await interval_repo.list_for_period(consumer.id, start=start, end=end)
    points = [
        SpaHistoryPoint(
            timestamp=row.end_time,
            power_w=row.average_power_w,
            energy_kwh=row.energy_kwh,
            cost_sek=row.actual_cost_sek,
            temperature_c=None,
            price_sek_kwh=row.electricity_price_sek_kwh,
        )
        for row in intervals
    ]
    return SpaHistoryResponse(period=period, points=points)


@router.get("/sites/{slug}/spa/cost", response_model=SpaEnergyPeriodResponse)
async def get_spa_cost(
    slug: str,
    period: str = Query(default="today"),
    session: AsyncSession = Depends(get_db_session),
) -> SpaEnergyPeriodResponse:
    return await get_spa_energy_period(slug, period, session)


@router.get("/sites/{slug}/spa/health", response_model=SpaHealthResponse)
async def get_spa_health(
    slug: str, session: AsyncSession = Depends(get_db_session)
) -> SpaHealthResponse:
    site, consumer, config = await _get_spa_context(session, slug)
    repo = ConsumerRepository(session)
    sample_repo = ConsumerSampleRepository(session)
    poll = await repo.get_poll_state(consumer.id)
    since = datetime.now(UTC) - timedelta(hours=24)
    samples_24h = await sample_repo.count_since(consumer.id, since)
    latest = await sample_repo.get_latest(consumer.id)
    settings = get_settings()
    agg_repo = ConsumerAggregateRepository(session)
    day_start, _ = period_bounds(
        granularity="day", reference=datetime.now(UTC), timezone=consumer.timezone
    )
    agg = await agg_repo.get_for_period(consumer.id, granularity="day", period_start=day_start)
    api_status = (
        "OK"
        if poll and poll.last_success_at
        else ("ERROR" if config.integration_enabled else "DISABLED")
    )
    if config.integration_enabled and not settings.arctic_spa_enabled:
        api_status = "DISABLED"
    spa_status = "ONLINE" if latest and latest.spa_connected else "OFFLINE"
    return SpaHealthResponse(
        consumer_id=consumer.id,
        api_status=api_status,
        spa_status=spa_status,
        polling_status="ACTIVE" if poll and poll.polling_active else "IDLE",
        database_status="OK",
        last_success_at=poll.last_success_at if poll else None,
        last_sample_at=poll.last_sample_at if poll else None,
        samples_last_24h=samples_24h,
        data_quality=latest.quality if latest else "MISSING",
        measured_pct=agg.measured_pct if agg else None,
        calculated_pct=agg.calculated_pct if agg else None,
        estimated_pct=agg.estimated_pct if agg else None,
        missing_pct=agg.missing_pct if agg else None,
        last_error=poll.last_error_message if poll else None,
    )


@router.get("/sites/{slug}/spa/config", response_model=SpaConfigResponse)
async def get_spa_config(
    slug: str, session: AsyncSession = Depends(get_db_session)
) -> SpaConfigResponse:
    site, consumer, config = await _get_spa_context(session, slug)
    return SpaConfigResponse(
        consumer_id=consumer.id,
        integration_enabled=config.integration_enabled,
        api_base_url=config.api_base_url,
        masked_api_key=mask_api_key(config.api_key),
        external_spa_id=config.external_spa_id,
        poll_interval_seconds=config.poll_interval_seconds,
        energy_collection_enabled=config.energy_collection_enabled,
        cost_calculation_enabled=config.cost_calculation_enabled,
        timezone=consumer.timezone or site.timezone,
    )


@router.put("/sites/{slug}/spa/config", response_model=SpaConfigResponse)
async def update_spa_config(
    slug: str,
    payload: SpaConfigUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SpaConfigResponse:
    site, consumer, config = await _get_spa_context(session, slug)
    repo = ConsumerRepository(session)
    await repo.update_spa_config(
        consumer.id,
        integration_enabled=payload.integration_enabled,
        api_base_url=payload.api_base_url,
        api_key=payload.api_key,
        external_spa_id=payload.external_spa_id,
        poll_interval_seconds=payload.poll_interval_seconds,
        energy_collection_enabled=payload.energy_collection_enabled,
        cost_calculation_enabled=payload.cost_calculation_enabled,
    )
    await session.commit()
    return await get_spa_config(slug, session)


@router.post("/sites/{slug}/spa/test-connection", response_model=SpaConnectionTestResponse)
async def test_spa_connection(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
) -> SpaConnectionTestResponse:
    site, consumer, config = await _get_spa_context(session, slug)
    cfg = ArcticSpaConfiguration.merge(
        db_enabled=True,
        db_base_url=config.api_base_url,
        db_api_key=config.api_key,
        db_spa_id=config.external_spa_id,
        db_poll_interval=config.poll_interval_seconds,
        db_energy_enabled=config.energy_collection_enabled,
        db_cost_enabled=config.cost_calculation_enabled,
        db_profiles_json=config.power_profiles_json,
    )
    result = await ArcticSpaService(cfg).test_connection()
    return SpaConnectionTestResponse(
        success=result.success,
        spa_found=result.spa_found,
        spa_online=result.spa_online,
        message=result.message,
        last_update=result.last_update,
        masked_api_key=result.masked_api_key,
    )
