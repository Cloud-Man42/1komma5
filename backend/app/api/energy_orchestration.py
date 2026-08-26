"""Site energy orchestration API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db_session
from app.schemas import (
    EnergyOrchestrationLoadResponse,
    EnergyOrchestrationPrioritiesUpdateRequest,
    EnergyOrchestrationResponse,
)
from energy_core.db.consumer_repo import ConsumerRepository
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.flexible_load_plan_repo import FlexibleLoadPlanRepository
from energy_core.db.repositories import SiteRepository
from energy_core.db.spa_control_repo import SpaControlConfigRepository
from energy_core.site_energy.orchestrator_service import SiteEnergyOrchestratorService
from energy_core.config import get_settings

router = APIRouter(tags=["energy-orchestration"])


def _load_type(load_id: str) -> str:
    if load_id == "spa_cleaning":
        return "spa"
    if load_id.startswith("ev_charger_"):
        return "ev"
    return "other"


@router.get("/sites/{slug}/energy/orchestration", response_model=EnergyOrchestrationResponse)
async def get_energy_orchestration(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
) -> EnergyOrchestrationResponse:
    site_repo = SiteRepository(session)
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")

    orchestrator = SiteEnergyOrchestratorService(get_settings())
    specs = await orchestrator.build_specs_for_site(session, site)

    plan_repo = FlexibleLoadPlanRepository(session)
    plans = {plan.load_id: plan for plan in await plan_repo.list_latest_for_site(site.id)}

    loads: list[EnergyOrchestrationLoadResponse] = []
    for spec in sorted(specs, key=lambda item: item.load.priority, reverse=True):
        plan = plans.get(spec.load.load_id)
        loads.append(
            EnergyOrchestrationLoadResponse(
                load_id=spec.load.load_id,
                name=spec.load.name,
                load_type=_load_type(spec.load.load_id),
                priority=spec.load.priority,
                strategy=spec.strategy.value,
                window_start=plan.window_start if plan else None,
                window_end=plan.window_end if plan else None,
                expected_energy_kwh=plan.expected_energy_kwh if plan else None,
                expected_cost_sek=plan.expected_cost_sek if plan else None,
                expected_energy_source=plan.expected_energy_source if plan else None,
                reason_sv=plan.reason_sv if plan else None,
                explanation_sv=plan.explanation_sv if plan else None,
                dry_run=plan.dry_run if plan else True,
            )
        )

    return EnergyOrchestrationResponse(site_slug=slug, loads=loads)


@router.put("/sites/{slug}/energy/orchestration/priorities", response_model=EnergyOrchestrationResponse)
async def update_energy_orchestration_priorities(
    slug: str,
    payload: EnergyOrchestrationPrioritiesUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> EnergyOrchestrationResponse:
    site_repo = SiteRepository(session)
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")

    if not payload.loads:
        raise HTTPException(status_code=422, detail="At least one load priority is required")

    consumer_repo = ConsumerRepository(session)
    spa_row = await consumer_repo.get_spa_by_site_slug(slug)
    charger_repo = EvChargerRepository(session)
    chargers = {charger.id: charger for charger in await charger_repo.list_for_site(site.id)}

    for item in payload.loads:
        if item.priority < 0 or item.priority > 100:
            raise HTTPException(status_code=422, detail=f"Invalid priority for {item.load_id}")

        if item.load_id == "spa_cleaning":
            if spa_row is None:
                raise HTTPException(status_code=404, detail="Spa not configured for site")
            control_repo = SpaControlConfigRepository(session)
            await control_repo.get_or_create(spa_row[0].id)
            updated = await control_repo.update(spa_row[0].id, load_priority=item.priority)
            if updated is None:
                raise HTTPException(status_code=404, detail="Spa control config not found")
            continue

        if item.load_id.startswith("ev_charger_"):
            try:
                charger_id = int(item.load_id.removeprefix("ev_charger_"))
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=f"Invalid load id {item.load_id}") from exc
            if charger_id not in chargers:
                raise HTTPException(status_code=404, detail=f"EV charger {charger_id} not found")
            await charger_repo.update(charger_id, load_priority=item.priority)
            continue

        raise HTTPException(status_code=422, detail=f"Unknown load id {item.load_id}")

    await session.commit()
    return await get_energy_orchestration(slug, session)
