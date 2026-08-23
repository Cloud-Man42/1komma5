"""EV charging session and statistics API."""

from __future__ import annotations

from datetime import UTC, datetime

from app.deps import get_db_session
from app.schemas import (
    EvChargingIntervalResponse,
    EvChargingSessionResponse,
    EvChargingStatsResponse,
    EvEnergySourcesResponse,
)
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.ev_interval_repo import EvChargingIntervalRepository
from energy_core.db.ev_session_repo import EvChargingSessionRecord, EvChargingSessionRepository
from energy_core.ev_accounting.statistics import EVStatisticsService
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["ev-sessions"])


def _sources_from_session(record: EvChargingSessionRecord) -> EvEnergySourcesResponse:
    return EvEnergySourcesResponse(
        solar_direct_kwh=record.solar_direct_kwh or 0.0,
        solar_battery_kwh=record.solar_battery_kwh or 0.0,
        grid_battery_kwh=record.grid_battery_kwh or 0.0,
        grid_direct_kwh=record.grid_direct_kwh or 0.0,
    )


def _session_response(
    record: EvChargingSessionRecord,
    *,
    intervals: list | None = None,
) -> EvChargingSessionResponse:
    total = record.total_energy_kwh or 0.0
    avg_cost = (record.actual_cost_sek / total) if total > 0 and record.actual_cost_sek else None
    interval_responses: list[EvChargingIntervalResponse] = []
    if intervals:
        for i in intervals:
            interval_responses.append(
                EvChargingIntervalResponse(
                    id=i.id,
                    start_time=i.start_time,
                    end_time=i.end_time,
                    charged_energy_kwh=i.charged_energy_kwh,
                    average_charging_power_w=i.average_charging_power_w,
                    pv_production_kwh=i.pv_production_kwh,
                    house_consumption_kwh=i.house_consumption_kwh,
                    grid_import_kwh=i.grid_import_kwh,
                    grid_export_kwh=i.grid_export_kwh,
                    battery_charge_kwh=i.battery_charge_kwh,
                    battery_discharge_kwh=i.battery_discharge_kwh,
                    electricity_price_sek_kwh=i.electricity_price_sek_kwh,
                    energy_sources=EvEnergySourcesResponse(
                        solar_direct_kwh=i.solar_direct_kwh,
                        solar_battery_kwh=i.solar_battery_kwh,
                        grid_battery_kwh=i.grid_battery_kwh,
                        grid_direct_kwh=i.grid_direct_kwh,
                    ),
                    actual_cost_sek=i.actual_cost_sek,
                    reference_cost_sek=i.reference_cost_sek,
                    savings_sek=i.savings_sek,
                    confidence=i.confidence,
                    data_quality=i.data_quality,
                )
            )
    return EvChargingSessionResponse(
        id=record.id,
        charger_id=record.charger_id,
        started_at=record.started_at,
        ended_at=record.ended_at,
        status=record.status,
        total_energy_kwh=record.total_energy_kwh,
        energy_sources=_sources_from_session(record),
        actual_cost_sek=record.actual_cost_sek,
        reference_cost_sek=record.reference_cost_sek,
        savings_sek=record.savings_sek,
        smart_charging_savings_sek=record.smart_charging_savings_sek,
        solar_contribution_sek=record.solar_contribution_sek,
        renewable_share_pct=record.renewable_share_pct,
        grid_share_pct=record.grid_share_pct,
        average_cost_sek_per_kwh=round(avg_cost, 4) if avg_cost is not None else None,
        energy_quality=record.energy_quality,
        cost_quality=record.cost_quality,
        attribution_quality=record.attribution_quality,
        savings_baseline=record.savings_baseline,
        calculation_version=record.calculation_version,
        reconciliation_delta_kwh=record.reconciliation_delta_kwh,
        intervals=interval_responses,
    )


async def _get_charger_or_404(repo: EvChargerRepository, slug: str, charger_id: int):
    site = await repo.get_site_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    charger = await repo.get_by_id(charger_id)
    if charger is None or charger.site_id != site.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EV charger not found")
    return site, charger


@router.get(
    "/sites/{slug}/ev-chargers/{charger_id}/sessions",
    response_model=list[EvChargingSessionResponse],
)
async def list_ev_sessions(
    slug: str,
    charger_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> list[EvChargingSessionResponse]:
    repo = EvChargingSessionRepository(session)
    charger_repo = EvChargerRepository(session)
    await _get_charger_or_404(charger_repo, slug, charger_id)
    records = await repo.list_for_charger(charger_id, limit=limit, offset=offset)
    return [_session_response(r) for r in records]


@router.get(
    "/sites/{slug}/ev-chargers/{charger_id}/sessions/current",
    response_model=EvChargingSessionResponse | None,
)
async def get_current_ev_session(
    slug: str,
    charger_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> EvChargingSessionResponse | None:
    repo = EvChargingSessionRepository(session)
    charger_repo = EvChargerRepository(session)
    await _get_charger_or_404(charger_repo, slug, charger_id)
    record = await repo.get_active_for_charger(charger_id)
    if record is None:
        return None
    intervals = await EvChargingIntervalRepository(session).list_for_session(record.id)
    return _session_response(record, intervals=intervals)


@router.get(
    "/sites/{slug}/ev-chargers/{charger_id}/sessions/{session_id}",
    response_model=EvChargingSessionResponse,
)
async def get_ev_session(
    slug: str,
    charger_id: int,
    session_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> EvChargingSessionResponse:
    repo = EvChargingSessionRepository(session)
    charger_repo = EvChargerRepository(session)
    await _get_charger_or_404(charger_repo, slug, charger_id)
    record = await repo.get_by_id(session_id)
    if record is None or record.charger_id != charger_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    intervals = await EvChargingIntervalRepository(session).list_for_session(session_id)
    return _session_response(record, intervals=intervals)


@router.get(
    "/sites/{slug}/ev-chargers/{charger_id}/stats",
    response_model=EvChargingStatsResponse,
)
async def get_ev_stats(
    slug: str,
    charger_id: int,
    period: str = Query(default="month"),
    from_time: datetime | None = Query(default=None, alias="from"),
    to_time: datetime | None = Query(default=None, alias="to"),
    session: AsyncSession = Depends(get_db_session),
) -> EvChargingStatsResponse:
    if period not in {"session", "day", "week", "month", "year", "all"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid period"
        )

    charger_repo = EvChargerRepository(session)
    await _get_charger_or_404(charger_repo, slug, charger_id)

    repo = EvChargingSessionRepository(session)
    stats = await EVStatisticsService(repo).stats(
        charger_id,
        period=period,  # type: ignore[arg-type]
        from_time=from_time,
        to_time=to_time or datetime.now(UTC),
    )
    return EvChargingStatsResponse(
        period=stats.period,
        period_from=stats.period_from,
        period_to=stats.period_to,
        total_energy_kwh=stats.total_energy_kwh,
        actual_cost_sek=stats.actual_cost_sek,
        reference_cost_sek=stats.reference_cost_sek,
        savings_sek=stats.savings_sek,
        average_cost_sek_per_kwh=stats.average_cost_sek_per_kwh,
        energy_sources=EvEnergySourcesResponse(
            solar_direct_kwh=stats.solar_direct_kwh,
            solar_battery_kwh=stats.solar_battery_kwh,
            grid_battery_kwh=stats.grid_battery_kwh,
            grid_direct_kwh=stats.grid_direct_kwh,
        ),
        renewable_share_percent=stats.renewable_share_percent,
        grid_share_percent=stats.grid_share_percent,
        smart_charging_savings_sek=stats.smart_charging_savings_sek,
        solar_contribution_sek=stats.solar_contribution_sek,
        session_count=stats.session_count,
    )
