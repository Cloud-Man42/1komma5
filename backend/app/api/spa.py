"""Arctic Spa API routes."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.admin_audit_helpers import audit_admin_mutation
from app.admin_auth import require_admin_token
from app.deps import get_db_session
from app.schemas import (
    SpaConfigResponse,
    SpaConfigUpdateRequest,
    SpaConnectionTestResponse,
    SpaControlConfigResponse,
    SpaControlConfigUpdateRequest,
    SpaEconomicsResponse,
    SpaEnergyBreakdownResponse,
    SpaEnergyBreakdownRow,
    SpaEnergyEventResponse,
    SpaEnergyPeriodResponse,
    SpaEventsResponse,
    SpaHealthResponse,
    SpaHistoryPoint,
    SpaHistoryResponse,
    SpaPlanBlockResponse,
    SpaCleaningWindowResponse,
    SpaPlanResponse,
    SpaRunCleaningResponse,
    SpaShadowDayResponse,
    SpaShadowResponse,
    SpaStatusResponse,
    SpaTimelineEntry,
    SpaTimelineResponse,
)
from energy_core.config import get_settings
from energy_core.consumer_accounting.aggregator import (
    group_intervals_by_local_period,
    period_bounds,
    spa_cost_split,
    sum_interval_fields,
)
from energy_core.consumer_accounting.coordinator import ConsumerAccountingCoordinator
from energy_core.consumer_accounting.sample_backfill import MAX_PLAUSIBLE_INTERVAL_KWH
from energy_core.db.consumer_repo import (
    ConsumerAggregateRepository,
    ConsumerIntervalRepository,
    ConsumerRepository,
    ConsumerSampleRepository,
)
from energy_core.db.flexible_load_plan_repo import FlexibleLoadPlanRepository
from energy_core.db.spa_actuator_repo import SpaActuatorStateRepository
from energy_core.db.spa_control_repo import SpaControlConfigRepository
from energy_core.db.spa_event_repo import SpaEnergyEventRepository
from energy_core.spa_energy.shadow import SpaShadowModeAnalyzer
from energy_core.spa_energy.cleaning_schedule import (
    build_filter_plan_summary_sv,
    compute_cleaning_hours_today,
    energy_source_label_sv,
)
from energy_core.spa_energy.filter_cycle_tracker import (
    count_completed_cycles,
    minutes_until,
    next_upcoming_window,
    reconcile_filter_cycles,
    remaining_cycles,
)
from energy_core.spa_energy.filter_policy import SpaFilterPolicy
from energy_core.spa_energy.service import SmartSpaEnergyService
from energy_core.integrations.arctic_spa.config import ArcticSpaConfiguration, mask_api_key
from energy_core.integrations.arctic_spa.service import ArcticSpaService
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
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


def _normalize_spa_period(period: str) -> str:
    if period == "day":
        return "24h"
    return period


def _period_range(period: str, timezone: str) -> tuple[datetime, datetime, str]:
    period = _normalize_spa_period(period)
    now = datetime.now(UTC)
    if period == "24h":
        return now - timedelta(hours=24), now, "hour"
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


def _build_period_response(
    period: str,
    totals: dict,
    *,
    fallback_price_sek_kwh: float,
) -> SpaEnergyPeriodResponse:
    energy = totals.get("energy_kwh", 0.0) or 0.0
    actual = totals.get("actual_cost_sek", 0.0) or 0.0
    reference = totals.get("reference_cost_sek")
    savings = totals.get("savings_sek")
    renewable = (totals.get("solar_direct_kwh", 0.0) or 0.0) + (totals.get("solar_battery_kwh", 0.0) or 0.0)
    own_pct = round(100.0 * renewable / energy, 1) if energy > 0 else None
    savings_pct = round(100.0 * savings / reference, 1) if savings and reference else None
    avg_cost = round(actual / energy, 4) if energy > 0 else None
    costs = spa_cost_split(totals, fallback_price_sek_kwh=fallback_price_sek_kwh)
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
        solar_kwh=costs["solar_kwh"],
        battery_kwh=costs["battery_kwh"],
        grid_kwh=costs["grid_kwh"],
        grid_cost_sek=costs["grid_cost_sek"],
        solar_value_sek=costs["solar_value_sek"],
        battery_value_sek=costs["battery_value_sek"],
        max_power_w=totals.get("max_power_w"),
        avg_power_w=totals.get("avg_power_w"),
        heater_runtime_hours=round((totals.get("heater_runtime_seconds", 0.0) or 0.0) / 3600.0, 2),
        pump_runtime_hours=round((totals.get("pump_runtime_seconds", 0.0) or 0.0) / 3600.0, 2),
        avg_cost_sek_kwh=avg_cost,
        has_data=energy > 0,
    )


def _format_period_label(timestamp: datetime, granularity: str, timezone: str) -> str:
    from zoneinfo import ZoneInfo

    local = timestamp.astimezone(ZoneInfo(timezone))
    if granularity == "month":
        return local.strftime("%B %Y")
    return local.strftime("%Y-%m-%d")


def _breakdown_granularity(period: str) -> str:
    if period in {"year", "total", "rolling12"}:
        return "month"
    return "day"


async def _needs_attribution_rebuild(
    session: AsyncSession,
    *,
    site_id: int,
    consumer_id: int,
    since: datetime,
    is_sqlite: bool,
) -> bool:
    """Detect intervals attributed entirely to grid while site had solar production."""
    interval_repo = ConsumerIntervalRepository(session)
    totals = await interval_repo.sum_for_period(consumer_id, start=since, end=datetime.now(UTC))
    energy = totals.get("energy_kwh", 0.0) or 0.0
    if energy <= 0:
        return False
    solar_attr = (totals.get("solar_direct_kwh", 0.0) or 0.0) + (totals.get("solar_battery_kwh", 0.0) or 0.0)
    if solar_attr / energy >= 0.01:
        return False
    from energy_core.db.repositories import EnergyReadingRepository

    readings = await EnergyReadingRepository(session, is_sqlite=is_sqlite).list_readings(
        site_id,
        from_time=since,
        to_time=datetime.now(UTC),
        limit=5000,
    )
    max_solar_w = max((reading.solar_production_w or 0.0 for reading in readings), default=0.0)
    return max_solar_w >= 500.0


async def _ensure_spa_intervals(session: AsyncSession, site, consumer_id: int, poll_interval_seconds: int = 60) -> None:
    interval_repo = ConsumerIntervalRepository(session)
    corrupt = await interval_repo.max_energy_kwh(consumer_id) > MAX_PLAUSIBLE_INTERVAL_KWH
    since = datetime.now(UTC) - timedelta(days=30)
    is_sqlite = session.bind.dialect.name == "sqlite" if session.bind else True
    interval_count = await interval_repo.count_for_period(consumer_id, start=since, end=datetime.now(UTC))
    rebuild_existing = await _needs_attribution_rebuild(
        session,
        site_id=site.id,
        consumer_id=consumer_id,
        since=since,
        is_sqlite=is_sqlite,
    )
    if not corrupt and interval_count > 0 and not rebuild_existing:
        return
    sample_repo = ConsumerSampleRepository(session)
    sample_totals = await sample_repo.sum_for_period(consumer_id, start=since, end=datetime.now(UTC))
    if (sample_totals.get("samples_with_power", 0) or 0) <= 0:
        return
    created = await ConsumerAccountingCoordinator().rebuild_spa_intervals_for_site(
        session,
        site=site,
        rebuild_existing=rebuild_existing or corrupt,
    )
    if created or corrupt or rebuild_existing:
        await session.commit()


async def _period_energy_totals(
    session: AsyncSession,
    consumer_id: int,
    *,
    start: datetime,
    end: datetime,
    fallback_price_sek_kwh: float,
    site,
) -> dict:
    interval_repo = ConsumerIntervalRepository(session)
    totals = await interval_repo.sum_for_period(consumer_id, start=start, end=end)
    if totals:
        return totals

    sample_repo = ConsumerSampleRepository(session)
    sample_totals = await sample_repo.sum_for_period(consumer_id, start=start, end=end)
    energy = sample_totals.get("energy_kwh", 0.0) or 0.0
    if energy <= 0:
        return {}
    return {
        "energy_kwh": energy,
        "solar_direct_kwh": 0.0,
        "solar_battery_kwh": 0.0,
        "grid_battery_kwh": 0.0,
        "grid_direct_kwh": energy,
        "unknown_kwh": 0.0,
        "actual_cost_sek": energy * fallback_price_sek_kwh,
        "reference_cost_sek": energy * fallback_price_sek_kwh,
        "savings_sek": 0.0,
        "heater_runtime_seconds": 0.0,
        "pump_runtime_seconds": 0.0,
        "max_power_w": sample_totals.get("max_power_w"),
    }


@router.get("/sites/{slug}/spa/status", response_model=SpaStatusResponse)
async def get_spa_status(slug: str, session: AsyncSession = Depends(get_db_session)) -> SpaStatusResponse:
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
    from energy_core.integrations.arctic_spa.operational_state import (
        filter_cycle_active,
        heater_drawing_power,
    )

    parsed = ArcticSpaStatus.from_api(status_payload) if status_payload else None
    breakdown: dict[str, float] = {}
    if latest and latest.component_breakdown_json:
        try:
            raw_breakdown = json.loads(latest.component_breakdown_json)
            if isinstance(raw_breakdown, dict):
                breakdown = {str(k): float(v) for k, v in raw_breakdown.items()}
        except (json.JSONDecodeError, TypeError, ValueError):
            breakdown = {}

    power_note_sv = "Beräknad effekt utifrån spa-läge och effektprofil — inte en direktmätning."
    if latest and latest.quality == "ESTIMATED":
        power_note_sv = (
            "Beräknad effekt, justerad mot husets aktuella last. "
            "Spa har ingen egen effektmätare i EMIC."
        )

    filter_status = parsed.filter_status if parsed else (latest.filter_status if latest else None)
    current_power_w = latest.power_w if latest else None
    heater_reported = parsed.heater_element_active if parsed else bool(latest and latest.heater_active)
    live_heater = heater_drawing_power(
        heater_active_reported=heater_reported,
        current_power_w=current_power_w,
        breakdown=breakdown,
    )
    live_filter = filter_cycle_active(
        filter_status=filter_status,
        current_power_w=current_power_w,
        breakdown=breakdown,
    )

    return SpaStatusResponse(
        consumer_id=consumer.id,
        site_slug=slug,
        online=bool(parsed.connected) if parsed else False,
        water_temperature_c=parsed.temperature_c if parsed else (latest.water_temperature_c if latest else None),
        set_temperature_c=parsed.setpoint_c if parsed else (latest.set_temperature_c if latest else None),
        heater_active=live_heater,
        pump_label=parsed.primary_pump_label if parsed else "Pump: Av",
        filter_status=filter_status,
        filter_cycle_active=live_filter,
        errors=list(parsed.errors) if parsed else [],
        current_power_w=current_power_w,
        power_breakdown=breakdown,
        last_updated=config.last_status_at or (latest.recorded_at if latest else None),
        data_quality=latest.quality if latest else "MISSING",
        power_note_sv=power_note_sv,
        integration_enabled=config.integration_enabled,
    )


@router.get("/sites/{slug}/spa/energy/breakdown", response_model=SpaEnergyBreakdownResponse)
async def get_spa_energy_breakdown(
    slug: str,
    period: str = Query(default="month"),
    session: AsyncSession = Depends(get_db_session),
) -> SpaEnergyBreakdownResponse:
    site, consumer, _config = await _get_spa_context(session, slug)
    timezone = consumer.timezone or site.timezone
    start, end, _gran = _period_range(period, timezone)
    interval_repo = ConsumerIntervalRepository(session)
    intervals = await interval_repo.list_for_period(consumer.id, start=start, end=end)
    granularity = _breakdown_granularity(period)
    grouped = group_intervals_by_local_period(intervals, granularity=granularity, timezone=timezone)
    rows: list[SpaEnergyBreakdownRow] = []
    for period_start, bucket in grouped:
        totals = sum_interval_fields(bucket)
        costs = spa_cost_split(totals, fallback_price_sek_kwh=site.fallback_purchase_price_sek_kwh)
        rows.append(
            SpaEnergyBreakdownRow(
                period_start=period_start,
                period_label=_format_period_label(period_start, granularity, timezone),
                energy_kwh=round(totals.get("energy_kwh", 0.0) or 0.0, 3),
                solar_kwh=costs["solar_kwh"],
                battery_kwh=costs["battery_kwh"],
                grid_kwh=costs["grid_kwh"],
                grid_cost_sek=costs["grid_cost_sek"],
                solar_value_sek=costs["solar_value_sek"],
                battery_value_sek=costs["battery_value_sek"],
                savings_sek=round(totals.get("savings_sek", 0.0) or 0.0, 2) or None,
            )
        )
    total = _build_period_response(
        period,
        sum_interval_fields(intervals),
        fallback_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
    )
    return SpaEnergyBreakdownResponse(period=period, granularity=granularity, rows=rows, total=total)


@router.get("/sites/{slug}/spa/energy/{period}", response_model=SpaEnergyPeriodResponse)
async def get_spa_energy_period(
    slug: str,
    period: str,
    session: AsyncSession = Depends(get_db_session),
) -> SpaEnergyPeriodResponse:
    site, consumer, _config = await _get_spa_context(session, slug)
    start, end, _gran = _period_range(period, consumer.timezone or site.timezone)
    totals = await _period_energy_totals(
        session,
        consumer.id,
        start=start,
        end=end,
        fallback_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
        site=site,
    )
    if not totals:
        return _build_period_response(period, {}, fallback_price_sek_kwh=site.fallback_purchase_price_sek_kwh)
    return _build_period_response(
        period,
        totals,
        fallback_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
    )


@router.get("/sites/{slug}/spa/energy/today", response_model=SpaEnergyPeriodResponse)
async def get_spa_energy_today(slug: str, session: AsyncSession = Depends(get_db_session)) -> SpaEnergyPeriodResponse:
    return await get_spa_energy_period(slug, "today", session)


def _history_points_from_grouped_intervals(
    grouped: list[tuple[datetime, list]],
    *,
    granularity: str,
    timezone: str,
    fallback_price_sek_kwh: float,
) -> list[SpaHistoryPoint]:
    points: list[SpaHistoryPoint] = []
    tz = ZoneInfo(timezone)
    for period_start, bucket in grouped:
        totals = sum_interval_fields(bucket)
        costs = spa_cost_split(totals, fallback_price_sek_kwh=fallback_price_sek_kwh)
        if granularity == "hour":
            period_label = period_start.astimezone(tz).strftime("%H:%M")
        else:
            period_label = _format_period_label(period_start, granularity, timezone)
        points.append(
            SpaHistoryPoint(
                timestamp=period_start,
                period_label=period_label,
                power_w=totals.get("max_power_w"),
                energy_kwh=round(totals.get("energy_kwh", 0.0) or 0.0, 3),
                cost_sek=costs["grid_cost_sek"],
                solar_kwh=costs["solar_kwh"],
                battery_kwh=costs["battery_kwh"],
                grid_kwh=costs["grid_kwh"],
                grid_cost_sek=costs["grid_cost_sek"],
                solar_value_sek=costs["solar_value_sek"],
                battery_value_sek=costs["battery_value_sek"],
            )
        )
    return points


@router.get("/sites/{slug}/spa/history", response_model=SpaHistoryResponse)
async def get_spa_history(
    slug: str,
    period: str = Query(default="today"),
    session: AsyncSession = Depends(get_db_session),
) -> SpaHistoryResponse:
    site, consumer, _config = await _get_spa_context(session, slug)
    period = _normalize_spa_period(period)
    timezone = consumer.timezone or site.timezone
    start, end, _gran = _period_range(period, timezone)
    interval_repo = ConsumerIntervalRepository(session)
    intervals = await interval_repo.list_for_period(consumer.id, start=start, end=end)
    granularity = _breakdown_granularity(period) if period not in {"today", "24h"} else "hour"
    if period in {"today", "week"}:
        points = [
            SpaHistoryPoint(
                timestamp=row.end_time,
                period_label=row.end_time.astimezone(ZoneInfo(timezone)).strftime("%H:%M"),
                power_w=row.average_power_w,
                energy_kwh=row.energy_kwh,
                cost_sek=row.actual_cost_sek,
                solar_kwh=round(row.solar_direct_kwh + row.solar_battery_kwh, 3),
                battery_kwh=round(row.solar_battery_kwh + row.grid_battery_kwh, 3),
                grid_kwh=round(row.grid_direct_kwh, 3),
                grid_cost_sek=round(row.actual_cost_sek, 2),
                solar_value_sek=round((row.solar_direct_kwh + row.solar_battery_kwh) * (row.electricity_price_sek_kwh or 0.0), 2),
                battery_value_sek=round((row.solar_battery_kwh + row.grid_battery_kwh) * (row.electricity_price_sek_kwh or 0.0), 2),
                price_sek_kwh=row.electricity_price_sek_kwh,
            )
            for row in intervals
        ]
    elif period == "24h":
        grouped = group_intervals_by_local_period(intervals, granularity="hour", timezone=timezone)
        points = _history_points_from_grouped_intervals(
            grouped,
            granularity="hour",
            timezone=timezone,
            fallback_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
        )
    else:
        grouped = group_intervals_by_local_period(intervals, granularity=granularity, timezone=timezone)
        points = _history_points_from_grouped_intervals(
            grouped,
            granularity=granularity,
            timezone=timezone,
            fallback_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
        )
    return SpaHistoryResponse(period=period, points=points)


@router.get("/sites/{slug}/spa/cost", response_model=SpaEnergyPeriodResponse)
async def get_spa_cost(
    slug: str,
    period: str = Query(default="today"),
    session: AsyncSession = Depends(get_db_session),
) -> SpaEnergyPeriodResponse:
    return await get_spa_energy_period(slug, period, session)


@router.get("/sites/{slug}/spa/health", response_model=SpaHealthResponse)
async def get_spa_health(slug: str, session: AsyncSession = Depends(get_db_session)) -> SpaHealthResponse:
    site, consumer, config = await _get_spa_context(session, slug)
    repo = ConsumerRepository(session)
    sample_repo = ConsumerSampleRepository(session)
    poll = await repo.get_poll_state(consumer.id)
    since = datetime.now(UTC) - timedelta(hours=24)
    samples_24h = await sample_repo.count_since(consumer.id, since)
    recent_samples = await sample_repo.list_for_period(consumer.id, start=since, end=datetime.now(UTC))
    from energy_core.consumer_accounting.sample_backfill import SpaSampleBackfillService

    sample_totals_24h = SpaSampleBackfillService.sample_totals(
        recent_samples,
        poll_interval_seconds=config.poll_interval_seconds or 60,
    )
    intervals_24h = await ConsumerIntervalRepository(session).count_for_period(consumer.id, start=since, end=datetime.now(UTC))
    latest = await sample_repo.get_latest(consumer.id)
    settings = get_settings()
    agg_repo = ConsumerAggregateRepository(session)
    day_start, _ = period_bounds(granularity="day", reference=datetime.now(UTC), timezone=consumer.timezone)
    agg = await agg_repo.get_for_period(consumer.id, granularity="day", period_start=day_start)
    api_status = "OK" if poll and poll.last_success_at else (
        "ERROR" if config.integration_enabled else "DISABLED"
    )
    if config.integration_enabled and not settings.arctic_spa_enabled:
        api_status = "DISABLED"
    spa_status = "ONLINE" if latest and latest.spa_connected else "OFFLINE"
    last_error = poll.last_error_message if poll else None
    if last_error is not None:
        last_error = last_error.strip()
        if not last_error or last_error == "Request failed after retries:":
            last_error = None
    actuator_runtime = await SpaActuatorStateRepository(session).get_or_create(consumer.id)
    return SpaHealthResponse(
        consumer_id=consumer.id,
        api_status=api_status,
        spa_status=spa_status,
        polling_status="ACTIVE" if poll and poll.polling_active else "IDLE",
        database_status="OK",
        last_success_at=poll.last_success_at if poll else None,
        last_sample_at=poll.last_sample_at if poll else None,
        samples_last_24h=samples_24h,
        samples_with_power_24h=sample_totals_24h.get("samples_with_power", 0),
        sample_energy_kwh_24h=round(sample_totals_24h.get("energy_kwh", 0.0) or 0.0, 3),
        intervals_last_24h=intervals_24h,
        data_quality=latest.quality if latest else "MISSING",
        measured_pct=agg.measured_pct if agg else None,
        calculated_pct=agg.calculated_pct if agg else None,
        estimated_pct=agg.estimated_pct if agg else None,
        missing_pct=agg.missing_pct if agg else None,
        last_error=last_error,
        actuator_state=actuator_runtime.state.value,
        integration_degraded=actuator_runtime.integration_degraded,
        integration_degraded_message_sv=actuator_runtime.integration_degraded_message_sv,
    )


@router.get("/sites/{slug}/spa/config", response_model=SpaConfigResponse)
async def get_spa_config(slug: str, session: AsyncSession = Depends(get_db_session)) -> SpaConfigResponse:
    site, consumer, config = await _get_spa_context(session, slug)
    repo = ConsumerRepository(session)
    return SpaConfigResponse(
        consumer_id=consumer.id,
        integration_enabled=config.integration_enabled,
        api_base_url=config.api_base_url,
        masked_api_key=mask_api_key(repo.decrypt_spa_api_key(config)),
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
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_admin_token),
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
    await audit_admin_mutation(
        request,
        session,
        action="spa.config.update",
        site_slug=slug,
        resource_type="spa",
        resource_id=str(consumer.id),
        summary=payload.model_dump(exclude_unset=True),
    )
    await session.commit()
    return await get_spa_config(slug, session)


@router.post("/sites/{slug}/spa/test-connection", response_model=SpaConnectionTestResponse)
async def test_spa_connection(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_admin_token),
) -> SpaConnectionTestResponse:
    site, consumer, config = await _get_spa_context(session, slug)
    repo = ConsumerRepository(session)
    cfg = ArcticSpaConfiguration.merge(
        db_enabled=True,
        db_base_url=config.api_base_url,
        db_api_key=repo.decrypt_spa_api_key(config),
        db_spa_id=config.external_spa_id,
        db_poll_interval=config.poll_interval_seconds,
        db_energy_enabled=config.energy_collection_enabled,
        db_cost_enabled=config.cost_calculation_enabled,
        db_profiles_json=config.power_profiles_json,
    )
    result = await ArcticSpaService(cfg).test_connection()
    await audit_admin_mutation(
        request,
        session,
        action="spa.test_connection",
        site_slug=slug,
        resource_type="spa",
        resource_id=str(consumer.id),
        summary={"success": result.success, "spa_online": result.spa_online},
    )
    await session.commit()
    return SpaConnectionTestResponse(
        success=result.success,
        spa_found=result.spa_found,
        spa_online=result.spa_online,
        message=result.message,
        last_update=result.last_update,
        masked_api_key=result.masked_api_key,
    )


VALID_STRATEGIES = frozenset({"SMART", "SOLAR_ONLY", "CHEAPEST", "FIXED_SCHEDULE"})
VALID_ECONOMICS_PERIODS = frozenset({"today", "month", "year"})


def _control_config_response(record) -> SpaControlConfigResponse:
    return SpaControlConfigResponse(
        consumer_id=record.consumer_id,
        smart_control_enabled=record.smart_control_enabled,
        strategy=record.strategy,
        dry_run=record.dry_run,
        shadow_mode=record.shadow_mode,
        shadow_mode_until=record.shadow_mode_until,
        min_cleaning_hours_per_day=record.min_cleaning_hours_per_day,
        allowed_window_start=record.allowed_window_start,
        allowed_window_end=record.allowed_window_end,
        prefer_solar=record.prefer_solar,
        allow_battery=record.allow_battery,
        min_battery_soc_pct=record.min_battery_soc_pct,
        min_run_minutes=record.min_run_minutes,
        min_stop_minutes=record.min_stop_minutes,
        max_starts_per_day=record.max_starts_per_day,
        filter_cycles_per_day=record.filter_cycles_per_day,
        filter_duration_minutes=record.filter_duration_minutes,
        minimum_cycle_separation_minutes=record.minimum_cycle_separation_minutes,
        filter_optimization_enabled=record.filter_optimization_enabled,
        safety_floor_frequency_per_day=record.safety_floor_frequency_per_day,
        safety_floor_duration_hours=record.safety_floor_duration_hours,
        smart_preheat_enabled=record.smart_preheat_enabled,
        normal_temperature_c=record.normal_temperature_c,
        max_preheat_temperature_c=record.max_preheat_temperature_c,
        min_comfort_temperature_c=record.min_comfort_temperature_c,
        load_priority=record.load_priority,
        fixed_schedule_start=record.fixed_schedule_start,
        fixed_schedule_end=record.fixed_schedule_end,
    )


@router.get("/sites/{slug}/spa/control/config", response_model=SpaControlConfigResponse)
async def get_spa_control_config(slug: str, session: AsyncSession = Depends(get_db_session)) -> SpaControlConfigResponse:
    _site, consumer, _config = await _get_spa_context(session, slug)
    repo = SpaControlConfigRepository(session)
    record = await repo.get_or_create(consumer.id)
    return _control_config_response(record)


@router.put("/sites/{slug}/spa/control/config", response_model=SpaControlConfigResponse)
async def update_spa_control_config(
    slug: str,
    payload: SpaControlConfigUpdateRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_admin_token),
) -> SpaControlConfigResponse:
    _site, consumer, _config = await _get_spa_context(session, slug)
    if payload.strategy is not None and payload.strategy not in VALID_STRATEGIES:
        raise HTTPException(status_code=422, detail="Invalid strategy")
    repo = SpaControlConfigRepository(session)
    await repo.get_or_create(consumer.id)
    update_fields = {
        "smart_control_enabled": payload.smart_control_enabled,
        "strategy": payload.strategy,
        "dry_run": payload.dry_run,
        "shadow_mode": payload.shadow_mode,
        "allowed_window_start": payload.allowed_window_start,
        "allowed_window_end": payload.allowed_window_end,
        "prefer_solar": payload.prefer_solar,
        "allow_battery": payload.allow_battery,
        "min_battery_soc_pct": payload.min_battery_soc_pct,
        "load_priority": payload.load_priority,
        "smart_preheat_enabled": payload.smart_preheat_enabled,
        "normal_temperature_c": payload.normal_temperature_c,
        "max_preheat_temperature_c": payload.max_preheat_temperature_c,
        "min_comfort_temperature_c": payload.min_comfort_temperature_c,
        "fixed_schedule_start": payload.fixed_schedule_start,
        "fixed_schedule_end": payload.fixed_schedule_end,
        "filter_cycles_per_day": payload.filter_cycles_per_day,
        "filter_duration_minutes": payload.filter_duration_minutes,
        "minimum_cycle_separation_minutes": payload.minimum_cycle_separation_minutes,
        "filter_optimization_enabled": payload.filter_optimization_enabled,
    }
    if payload.min_cleaning_hours_per_day is not None:
        update_fields["min_cleaning_hours_per_day"] = payload.min_cleaning_hours_per_day
    if payload.min_run_minutes is not None:
        update_fields["min_run_minutes"] = payload.min_run_minutes
    if payload.min_stop_minutes is not None:
        update_fields["min_stop_minutes"] = payload.min_stop_minutes
    if payload.max_starts_per_day is not None:
        update_fields["max_starts_per_day"] = payload.max_starts_per_day

    updated = await repo.update(consumer.id, **{k: v for k, v in update_fields.items() if v is not None})
    if updated is None:
        raise HTTPException(status_code=404, detail="Spa control config not found")

    policy = SpaFilterPolicy.from_control(updated)
    synced = policy.sync_legacy_control_fields()
    updated = await repo.update(consumer.id, **synced)
    await audit_admin_mutation(
        request,
        session,
        action="spa.control.update",
        site_slug=slug,
        resource_type="spa_control",
        resource_id=str(consumer.id),
        summary=payload.model_dump(exclude_unset=True),
    )
    await session.commit()
    if updated is None:
        raise HTTPException(status_code=404, detail="Spa control config not found")
    return _control_config_response(updated)


@router.get("/sites/{slug}/spa/plan", response_model=SpaPlanResponse)
async def get_spa_plan(slug: str, session: AsyncSession = Depends(get_db_session)) -> SpaPlanResponse:
    site, consumer, _config = await _get_spa_context(session, slug)
    control_repo = SpaControlConfigRepository(session)
    control = await control_repo.get_or_create(consumer.id)
    if not control.smart_control_enabled and not control.shadow_mode:
        return SpaPlanResponse(enabled=False, consumer_id=consumer.id)

    policy = SpaFilterPolicy.from_control(control)
    validation = policy.validate()
    config_summary = build_filter_plan_summary_sv(
        cycles_per_day=policy.cycles_per_day,
        duration_minutes=policy.duration_per_cycle_minutes,
        allowed_start=policy.earliest_start,
        allowed_end=policy.latest_finish,
    )

    tz = ZoneInfo(consumer.timezone or site.timezone)
    now = datetime.now(UTC)
    local_now = now.astimezone(tz)
    day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
    day_end = day_start + timedelta(days=1)

    sample_repo = ConsumerSampleRepository(session)
    samples = await sample_repo.list_for_period(consumer.id, start=day_start - timedelta(days=1), end=now)
    sample_pairs = [(s.recorded_at, s.filter_status) for s in samples]
    completed_hours, starts_used = compute_cleaning_hours_today(
        sample_pairs,
        day_start=day_start,
        day_end=day_end,
    )
    progress_pct = min(
        100.0,
        round(100.0 * completed_hours / max(policy.total_daily_runtime_hours, 0.01), 1),
    )

    plan_repo = FlexibleLoadPlanRepository(session)
    plan = await plan_repo.get_latest_for_site(site.id)
    if plan is None:
        service = SmartSpaEnergyService(get_settings())
        await service.plan_for_site_slug(session, slug)
        await session.commit()
        plan = await plan_repo.get_latest_for_site(site.id)

    if plan is None:
        return SpaPlanResponse(
            enabled=True,
            consumer_id=consumer.id,
            dry_run=control.dry_run,
            daily_target_hours=policy.total_daily_runtime_hours,
            daily_completed_hours=completed_hours,
            daily_progress_pct=progress_pct,
            max_starts_per_day=policy.cycles_per_day,
            starts_used_today=starts_used,
            config_summary_sv=config_summary,
            config_validation_warning_sv=validation.warning_sv,
            filter_control_source_sv="Arctic Spa",
            timing_optimization_source_sv="EMIC" if policy.optimization_enabled else "Inaktiv",
            filter_policy_summary_sv=policy.summary_sv(),
            optimization_hint_sv=policy.optimization_summary_sv(),
        )

    blocks = await plan_repo.list_blocks(plan.id)
    duration_hours = None
    if plan.window_start and plan.window_end:
        duration_hours = round((plan.window_end - plan.window_start).total_seconds() / 3600.0, 2)

    source_labels = {
        "SOLAR": "Solel",
        "BATTERY": "Batteri",
        "GRID": "Nät",
        "MIXED": "Blandat",
    }

    from energy_core.flexible_load.types import EnergySource

    daily_windows = [
        SpaCleaningWindowResponse(
            start=w.start,
            end=w.end,
            duration_hours=w.duration_hours,
            energy_source_label_sv=energy_source_label_sv(
                EnergySource(w.expected_energy_source),
                w.solar_share,
            ),
            solar_share_pct=round(w.solar_share * 100) if w.solar_share is not None else None,
        )
        for w in plan.windows
    ]

    next_window = next_upcoming_window(tuple(plan.windows), now)
    cycle_records = reconcile_filter_cycles(
        tuple(plan.windows),
        sample_pairs,
        day_start=day_start,
        day_end=day_end,
        required_duration_minutes=policy.duration_per_cycle_minutes,
        now=now,
    )
    hours_planned = sum(w.duration_hours for w in plan.windows)

    return SpaPlanResponse(
        enabled=True,
        consumer_id=consumer.id,
        load_id=plan.load_id,
        strategy=plan.strategy,
        next_cleaning_start=next_window.start if next_window else plan.window_start,
        next_cleaning_end=next_window.end if next_window else plan.window_end,
        duration_hours=next_window.duration_hours if next_window else duration_hours,
        planned_energy_source=source_labels.get(plan.expected_energy_source or "", plan.expected_energy_source),
        estimated_energy_kwh=plan.expected_energy_kwh,
        estimated_cost_sek=plan.expected_cost_sek,
        baseline_cost_sek=plan.baseline_cost_sek,
        savings_sek=plan.savings_sek,
        explanation_sv=plan.explanation_sv,
        reason=plan.reason,
        reason_sv=plan.reason_sv,
        fallback_from_solar_only=plan.fallback_from_solar_only,
        dry_run=plan.dry_run,
        data_quality="ESTIMATED",
        daily_windows=daily_windows,
        daily_target_hours=policy.total_daily_runtime_hours,
        daily_completed_hours=completed_hours,
        daily_progress_pct=progress_pct,
        planned_starts=len(plan.windows),
        max_starts_per_day=policy.cycles_per_day,
        starts_used_today=starts_used,
        config_summary_sv=config_summary,
        config_validation_warning_sv=validation.warning_sv,
        filter_control_source_sv="Arctic Spa",
        timing_optimization_source_sv="EMIC" if policy.optimization_enabled else "Inaktiv",
        filter_policy_summary_sv=policy.summary_sv(),
        optimization_hint_sv=policy.optimization_summary_sv(),
        cycles_planned=len(plan.windows),
        cycles_completed_today=count_completed_cycles(cycle_records),
        hours_planned=round(hours_planned, 2),
        next_cycle_starts_in_minutes=minutes_until(next_window, now) if next_window else None,
        remaining_cycles_today=remaining_cycles(cycle_records),
        blocks=[
            SpaPlanBlockResponse(
                timestamp=b.timestamp,
                score=b.score,
                solar_forecast_w=b.solar_forecast_w,
                house_load_forecast_w=b.house_load_forecast_w,
                available_surplus_w=b.available_surplus_w,
                marginal_cost_sek_kwh=b.marginal_cost_sek_kwh,
                expected_energy_source=b.expected_energy_source,
                price_estimated=b.price_estimated,
            )
            for b in blocks
        ],
    )


@router.get("/sites/{slug}/spa/timeline", response_model=SpaTimelineResponse)
async def get_spa_timeline(slug: str, session: AsyncSession = Depends(get_db_session)) -> SpaTimelineResponse:
    site, consumer, _config = await _get_spa_context(session, slug)
    plan_repo = FlexibleLoadPlanRepository(session)
    plan = await plan_repo.get_latest_for_site(site.id)
    entries: list[SpaTimelineEntry] = []
    if plan:
        tz = ZoneInfo(consumer.timezone or site.timezone)
        windows = plan.windows or ()
        for window in windows:
            cursor = window.start
            while cursor < window.end:
                local = cursor.astimezone(tz)
                entries.append(
                    SpaTimelineEntry(
                        timestamp=cursor,
                        hour_label=local.strftime("%H:%M"),
                        action="spa_cleaning",
                        action_sv="Spa cleaning",
                        load_id=plan.load_id,
                        energy_source=window.expected_energy_source,
                    )
                )
                cursor += timedelta(hours=1)
    return SpaTimelineResponse(entries=entries)


@router.get("/sites/{slug}/spa/events", response_model=SpaEventsResponse)
async def get_spa_events(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> SpaEventsResponse:
    _site, consumer, _config = await _get_spa_context(session, slug)
    repo = SpaEnergyEventRepository(session)
    events = await repo.list_for_consumer(consumer.id, limit=limit, offset=offset)
    return SpaEventsResponse(
        events=[
            SpaEnergyEventResponse(
                id=e.id,
                timestamp=e.timestamp,
                event_type=e.event_type,
                start_time=e.start_time,
                stop_time=e.stop_time,
                runtime_seconds=e.runtime_seconds,
                estimated_kwh=e.estimated_kwh,
                actual_kwh=e.actual_kwh,
                estimated_cost=e.estimated_cost,
                actual_cost=e.actual_cost,
                solar_share=e.solar_share,
                battery_share=e.battery_share,
                grid_share=e.grid_share,
                reason=e.reason,
                reason_sv=e.reason_sv,
                strategy=e.strategy,
                decision_score=e.decision_score,
                manual_override=e.manual_override,
                dry_run=e.dry_run,
                data_quality="ESTIMATED" if e.estimated_kwh is not None else "MEASURED",
            )
            for e in events
        ],
        total=len(events),
    )


@router.get("/sites/{slug}/spa/economics", response_model=SpaEconomicsResponse)
async def get_spa_economics(
    slug: str,
    period: str = Query(default="today"),
    session: AsyncSession = Depends(get_db_session),
) -> SpaEconomicsResponse:
    if period not in VALID_ECONOMICS_PERIODS:
        raise HTTPException(status_code=422, detail="Invalid period")
    site, consumer, _config = await _get_spa_context(session, slug)
    start, end, _gran = _period_range(period, consumer.timezone or site.timezone)
    interval_repo = ConsumerIntervalRepository(session)
    totals = await interval_repo.sum_for_period(consumer.id, start=start, end=end)
    energy = totals.get("energy_kwh", 0.0) or 0.0
    cost = totals.get("actual_cost_sek", 0.0) or 0.0
    reference = totals.get("reference_cost_sek")
    savings = totals.get("savings_sek")
    solar = (totals.get("solar_direct_kwh", 0.0) or 0.0) + (totals.get("solar_battery_kwh", 0.0) or 0.0)
    battery = totals.get("grid_battery_kwh", 0.0) or 0.0
    grid = totals.get("grid_direct_kwh", 0.0) or 0.0
    return SpaEconomicsResponse(
        period=period,
        energy_kwh=round(energy, 3),
        cost_sek=round(cost, 2),
        baseline_cost_sek=round(reference, 2) if reference else None,
        savings_sek=round(savings, 2) if savings else None,
        solar_share_pct=round(100.0 * solar / energy, 1) if energy > 0 else None,
        battery_share_pct=round(100.0 * battery / energy, 1) if energy > 0 else None,
        grid_share_pct=round(100.0 * grid / energy, 1) if energy > 0 else None,
        data_quality="MEASURED" if energy > 0 else "ESTIMATED",
    )


@router.get("/sites/{slug}/spa/shadow", response_model=SpaShadowResponse)
async def get_spa_shadow(slug: str, session: AsyncSession = Depends(get_db_session)) -> SpaShadowResponse:
    site, consumer, _config = await _get_spa_context(session, slug)
    control_repo = SpaControlConfigRepository(session)
    control = await control_repo.get_or_create(consumer.id)
    now = datetime.now(UTC)
    start = now - timedelta(days=7)
    interval_repo = ConsumerIntervalRepository(session)
    intervals = await interval_repo.list_for_period(consumer.id, start=start, end=now)
    tz = ZoneInfo(consumer.timezone or site.timezone)
    actual_by_day: dict[str, tuple[float, float]] = {}
    for row in intervals:
        label = row.start_time.astimezone(tz).strftime("%Y-%m-%d")
        energy, cost = actual_by_day.get(label, (0.0, 0.0))
        actual_by_day[label] = (energy + row.energy_kwh, cost + row.actual_cost_sek)

    plan_repo = FlexibleLoadPlanRepository(session)
    plan = await plan_repo.get_latest_for_site(site.id)
    optimized_by_day: dict[str, tuple[float, float]] = {}
    if plan and plan.expected_energy_kwh and plan.expected_cost_sek:
        label = (plan.window_start or now).astimezone(tz).strftime("%Y-%m-%d")
        optimized_by_day[label] = (plan.expected_energy_kwh, plan.expected_cost_sek)

    result = SpaShadowModeAnalyzer().compare(
        actual_by_day=actual_by_day,
        optimized_by_day=optimized_by_day,
        shadow_mode_active=control.shadow_mode,
        period_start=start,
        period_end=now,
    )
    actuator_runtime = await SpaActuatorStateRepository(session).get_or_create(consumer.id)
    return SpaShadowResponse(
        shadow_mode_active=result.shadow_mode_active,
        total_actual_cost_sek=round(result.total_actual_cost_sek, 2),
        total_optimized_cost_sek=round(result.total_optimized_cost_sek, 2),
        total_potential_saving_sek=round(result.total_potential_saving_sek, 2),
        days=[
            SpaShadowDayResponse(
                date_label=d.date_label,
                actual_cost_sek=round(d.actual_cost_sek, 2),
                optimized_cost_sek=round(d.optimized_cost_sek, 2),
                potential_saving_sek=round(d.potential_saving_sek, 2),
            )
            for d in result.days
        ],
        integration_degraded=actuator_runtime.integration_degraded,
        integration_degraded_message_sv=actuator_runtime.integration_degraded_message_sv,
    )


@router.post("/sites/{slug}/spa/cleaning/run-now", response_model=SpaRunCleaningResponse)
async def run_spa_cleaning_now(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_admin_token),
) -> SpaRunCleaningResponse:
    _site, consumer, _config = await _get_spa_context(session, slug)
    control_repo = SpaControlConfigRepository(session)
    control = await control_repo.get_or_create(consumer.id)
    if not control.smart_control_enabled:
        raise HTTPException(status_code=422, detail="Smartstyrning är inte aktiverad")
    service = SmartSpaEnergyService(get_settings())
    decision = await service.run_cleaning_now(session, slug)
    await audit_admin_mutation(
        request,
        session,
        action="spa.cleaning.run_now",
        site_slug=slug,
        resource_type="spa",
        resource_id=str(consumer.id),
        summary={"dry_run": control.dry_run, "shadow_mode": control.shadow_mode},
    )
    await session.commit()
    if decision is None:
        raise HTTPException(status_code=404, detail="Spa hittades inte")
    dry_run = decision.dry_run
    if decision.command_sent:
        msg = "Filtercykel startad (testläge)" if dry_run else "Filtercykel startad"
        return SpaRunCleaningResponse(success=True, message=msg, dry_run=dry_run)
    if dry_run and decision.action == "start":
        return SpaRunCleaningResponse(
            success=True,
            message="Filtercykel simulerad (testläge)",
            dry_run=True,
        )
    failure_messages = {
        "max_starter": "Dagens max antal filtercykler är redan nått.",
        "torrkorning": "Testläge aktivt — inget kommando skickades till spabadet.",
        "api_fel": "Kunde inte nå Arctic Spa — kontrollera API-anslutningen.",
        "spa_fel": "Spabadet rapporterar fel — manuell start blockeras.",
        "integration_degraderad": "Integrationen är degraderad — försök igen senare.",
        "paus": "Filtercykeln väntar på minsta paus mellan cyklerna.",
    }
    msg = failure_messages.get(decision.reason_sv, "Kunde inte starta filtercykel")
    return SpaRunCleaningResponse(success=False, message=msg, dry_run=dry_run)
