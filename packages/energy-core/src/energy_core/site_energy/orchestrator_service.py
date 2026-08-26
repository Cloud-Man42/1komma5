"""Site-level flexible load orchestration."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings
from energy_core.db.consumer_repo import ConsumerRepository
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.flexible_load_plan_repo import FlexibleLoadPlanRepository
from energy_core.db.repositories import SiteRepository
from energy_core.flexible_load.ev_load import build_ev_orchestrated_load
from energy_core.flexible_load.orchestrator import EnergyOrchestrator, OrchestratedLoadSpec
from energy_core.spa_energy.service import SmartSpaEnergyService

logger = logging.getLogger(__name__)


class SiteEnergyOrchestratorService:
    """Plan all flexible loads on a site with shared surplus allocation."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._spa_service = SmartSpaEnergyService(settings)
        self._orchestrator = EnergyOrchestrator()

    async def run_cycle(self, session: AsyncSession) -> int:
        site_repo = SiteRepository(session)
        sites = await site_repo.list_all()
        planned = 0
        for site in sites:
            try:
                if await self._run_site(session, site):
                    planned += 1
            except Exception:
                logger.exception("Site energy orchestration failed for %s", site.slug)
        return planned

    async def run_for_site_slug(self, session: AsyncSession, slug: str) -> bool:
        site_repo = SiteRepository(session)
        site = await site_repo.get_by_slug(slug)
        if site is None:
            return False
        return await self._run_site(session, site)

    async def build_specs_for_site(self, session: AsyncSession, site) -> tuple[OrchestratedLoadSpec, ...]:
        specs: list[OrchestratedLoadSpec] = []

        consumer_repo = ConsumerRepository(session)
        spa_row = await consumer_repo.get_spa_by_site_slug(site.slug)
        if spa_row is not None:
            consumer, device_config, _site = spa_row
            spa_spec = await self._spa_service.build_orchestrated_spec(
                session,
                consumer,
                device_config,
                site,
            )
            if spa_spec is not None:
                specs.append(spa_spec)

        charger_repo = EvChargerRepository(session)
        now = datetime.now(UTC)
        for charger in await charger_repo.list_for_site(site.id):
            ev_spec = build_ev_orchestrated_load(charger, site, now=now)
            if ev_spec is not None:
                specs.append(ev_spec)

        return tuple(specs)

    async def _run_site(self, session: AsyncSession, site) -> bool:
        specs = await self.build_specs_for_site(session, site)
        if not specs:
            return False

        now = datetime.now(UTC)
        timezone = site.timezone
        consumer_repo = ConsumerRepository(session)
        spa_row = await consumer_repo.get_spa_by_site_slug(site.slug)
        if spa_row is not None:
            timezone = spa_row[0].timezone

        horizon = await self._spa_service.build_horizon(session, site, timezone, now)
        if not horizon:
            return False

        results = self._orchestrator.plan_all(specs, horizon, now=now)
        plan_repo = FlexibleLoadPlanRepository(session)

        spa_handled = False
        for result in results:
            consumer_id = None
            if result.load_id == "spa_cleaning" and spa_row is not None:
                consumer_id = spa_row[0].id
            elif result.load_id.startswith("ev_charger_"):
                try:
                    charger_id = int(result.load_id.removeprefix("ev_charger_"))
                except ValueError:
                    charger_id = None
                if charger_id is not None:
                    consumer_id = None

            dry_run = True
            if spa_row is not None and result.load_id == "spa_cleaning":
                from energy_core.db.spa_control_repo import SpaControlConfigRepository

                control = await SpaControlConfigRepository(session).get_or_create(spa_row[0].id)
                dry_run = control.dry_run or control.shadow_mode

            await plan_repo.save_plan(
                site_id=site.id,
                consumer_id=consumer_id,
                plan=result.plan,
                dry_run=dry_run,
            )

            if result.load_id == "spa_cleaning" and spa_row is not None:
                spa_handled = True
                await self._spa_service.apply_orchestrated_plan(
                    session,
                    consumer=spa_row[0],
                    device_config=spa_row[1],
                    site=site,
                    plan=result.plan,
                    now=now,
                )

        return spa_handled or len(results) > 0
