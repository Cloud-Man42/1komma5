"""Heartbeat audit API routes."""

from __future__ import annotations

from app.deps import get_db_session, get_site_repository
from app.schemas import (
    HeartbeatAuditDailyResponse,
    HeartbeatAuditMonthlyResponse,
    HeartbeatAuditPeriodSnapshotResponse,
    HeartbeatAuditRollupResponse,
)
from energy_core.db.repositories import SiteRepository
from energy_core.heartbeat_audit.service import HeartbeatAuditService
from energy_core.price_engine.engine import EmicPriceEngine
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["heartbeat-audit"])


def _rollup_response(rollup) -> HeartbeatAuditRollupResponse:
    return HeartbeatAuditRollupResponse(
        actual_energy_cost_sek=rollup.actual_energy_cost_sek,
        baseline_cost_without_optimization_sek=rollup.baseline_cost_without_optimization_sek,
        heartbeat_saving_sek=rollup.heartbeat_saving_sek,
        emic_theoretical_optimal_cost_sek=rollup.emic_theoretical_optimal_cost_sek,
        additional_optimization_potential_sek=rollup.additional_optimization_potential_sek,
        heartbeat_efficiency_pct=rollup.heartbeat_efficiency_pct,
        imported_kwh=rollup.imported_kwh,
        exported_kwh=rollup.exported_kwh,
    )


def _snapshot_response(snapshot) -> HeartbeatAuditPeriodSnapshotResponse:
    return HeartbeatAuditPeriodSnapshotResponse(
        period_start=snapshot.period_start,
        period_end=snapshot.period_end,
        import_price_sek_kwh=snapshot.import_price_sek_kwh,
        export_price_sek_kwh=snapshot.export_price_sek_kwh,
        grid_import_w=snapshot.grid_import_w,
        grid_export_w=snapshot.grid_export_w,
        battery_soc_pct=snapshot.battery_soc_pct,
        ev_power_w=snapshot.ev_power_w,
        heartbeat_mode=snapshot.heartbeat_mode,
        ai_decision=snapshot.ai_decision,
        heartbeat_reason=snapshot.heartbeat_reason,
        emic_strategy_state=snapshot.emic_strategy_state,
        emic_recommended_action=snapshot.emic_recommended_action,
    )


async def _engine(session: AsyncSession) -> EmicPriceEngine:
    from energy_core.config import get_settings

    settings = get_settings()
    return EmicPriceEngine(session, is_sqlite=settings.is_sqlite)


@router.get("/sites/{slug}/heartbeat-audit/today", response_model=HeartbeatAuditDailyResponse)
async def get_heartbeat_audit_today(
    slug: str,
    site_repo: SiteRepository = Depends(get_site_repository),
    session: AsyncSession = Depends(get_db_session),
) -> HeartbeatAuditDailyResponse:
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site '{slug}' not found")

    from energy_core.config import get_settings

    settings = get_settings()
    engine = await _engine(session)
    mode = await engine.get_status(site.id)

    service = HeartbeatAuditService(session, is_sqlite=settings.is_sqlite)
    rollup, snapshots = await service.today(
        site_id=site.id,
        site_slug=slug,
        timezone=site.timezone,
        fallback_purchase_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
        export_compensation_sek_kwh=site.export_compensation_sek_kwh,
        optimization_mode=mode,
    )
    if rollup is None:
        raise HTTPException(status_code=503, detail="Insufficient audit data for today")

    return HeartbeatAuditDailyResponse(
        slug=slug,
        timezone=site.timezone,
        day=rollup.day,
        rollup=_rollup_response(rollup),
        solar_self_consumed_kwh=rollup.solar_self_consumed_kwh,
        battery_self_consumed_kwh=rollup.battery_self_consumed_kwh,
        period_count=rollup.period_count,
        periods=[_snapshot_response(s) for s in snapshots],
    )


@router.get("/sites/{slug}/heartbeat-audit/month", response_model=HeartbeatAuditMonthlyResponse)
async def get_heartbeat_audit_month(
    slug: str,
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    site_repo: SiteRepository = Depends(get_site_repository),
    session: AsyncSession = Depends(get_db_session),
) -> HeartbeatAuditMonthlyResponse:
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site '{slug}' not found")

    from energy_core.config import get_settings

    settings = get_settings()
    service = HeartbeatAuditService(session, is_sqlite=settings.is_sqlite)
    rollup, daily = await service.month(
        site_id=site.id,
        site_slug=slug,
        timezone=site.timezone,
        fallback_purchase_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
        export_compensation_sek_kwh=site.export_compensation_sek_kwh,
        month=month,
    )
    if rollup is None:
        raise HTTPException(status_code=503, detail="Insufficient audit data for month")

    return HeartbeatAuditMonthlyResponse(
        slug=slug,
        timezone=site.timezone,
        month=rollup.month,
        rollup=_rollup_response(rollup),
        days_with_data=rollup.days_with_data,
        daily=[
            HeartbeatAuditDailyResponse(
                slug=slug,
                timezone=site.timezone,
                day=d.day,
                rollup=_rollup_response(d),
                solar_self_consumed_kwh=d.solar_self_consumed_kwh,
                battery_self_consumed_kwh=d.battery_self_consumed_kwh,
                period_count=d.period_count,
                periods=[],
            )
            for d in daily
        ],
    )
