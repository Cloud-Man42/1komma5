"""Horizon optimizer API (Phase 14)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_app_settings, get_db_session
from app.schemas import BatteryOpportunityResponse, HorizonLoadRecommendationResponse, HorizonOptimizerResponse
from energy_core.cache.service import get_cache_service, horizon_optimizer_cache_key
from energy_core.config import Settings
from energy_core.db.repositories import SiteRepository
from energy_core.energy_optimizer.advisor import build_battery_opportunity_advice
from energy_core.performance.context import get_performance_context
from energy_core.site_energy.orchestrator_service import SiteEnergyOrchestratorService

router = APIRouter(tags=["horizon-optimizer"])


def _battery_response(slug: str, timezone: str, advice) -> BatteryOpportunityResponse:
    return BatteryOpportunityResponse(
        slug=slug,
        timezone=timezone,
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


async def _build_horizon_optimizer_response(
    session: AsyncSession,
    site,
    settings: Settings,
) -> HorizonOptimizerResponse:
    from energy_core.price_engine.strategy_service import build_current_strategy_for_slug

    orchestrator = SiteEnergyOrchestratorService(settings)
    snapshot = await orchestrator.plan_horizon_readonly(session, site)

    strategy = await build_current_strategy_for_slug(session, site.slug, is_sqlite=settings.is_sqlite)
    battery = None
    if strategy is not None:
        battery = _battery_response(site.slug, site.timezone, build_battery_opportunity_advice(strategy))

    return HorizonOptimizerResponse(
        slug=site.slug,
        timezone=site.timezone,
        available=snapshot.available,
        monitor_only=snapshot.monitor_only,
        unavailable_reason_sv=snapshot.unavailable_reason_sv,
        horizon_hours=snapshot.horizon_hours,
        horizon_blocks=snapshot.horizon_blocks,
        generated_at=snapshot.generated_at,
        total_planned_savings_sek=snapshot.total_planned_savings_sek,
        headline_sv=snapshot.headline_sv,
        summary_sv=snapshot.summary_sv,
        loads=[
            HorizonLoadRecommendationResponse(
                load_id=load.load_id,
                name=load.name,
                load_type=load.load_type,
                priority=load.priority,
                strategy=load.strategy,
                window_start=load.window_start,
                window_end=load.window_end,
                expected_energy_kwh=load.expected_energy_kwh,
                expected_cost_sek=load.expected_cost_sek,
                expected_energy_source=load.expected_energy_source,
                savings_sek=load.savings_sek,
                reason_sv=load.reason_sv,
                explanation_sv=load.explanation_sv,
            )
            for load in snapshot.loads
        ],
        battery=battery,
    )


@router.get("/sites/{slug}/horizon-optimizer", response_model=HorizonOptimizerResponse)
async def get_horizon_optimizer(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> HorizonOptimizerResponse:
    site_repo = SiteRepository(session)
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site '{slug}' not found")

    cache = get_cache_service(settings)
    cache_key = horizon_optimizer_cache_key(site.id)
    ttl_seconds = settings.horizon_optimizer_redis_cache_ttl_seconds

    async def factory() -> dict[str, Any]:
        response = await _build_horizon_optimizer_response(session, site, settings)
        return response.model_dump(mode="json")

    ctx = get_performance_context()
    cached = await cache.get(cache_key)
    if cached is not None:
        if ctx is not None:
            ctx.cache_hit = True
        return HorizonOptimizerResponse.model_validate(cached)

    payload = await cache.get_or_set(cache_key, factory, ttl_seconds=ttl_seconds)
    return HorizonOptimizerResponse.model_validate(payload)
