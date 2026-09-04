"""Energy control orchestration."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import SiteModel
from energy_core.db.price_period_repo import PriceEngineStateRepository
from energy_core.energy_control.gate import (
    mode_allows_automatic_apply,
    mode_allows_manual_apply,
    mode_allows_preview,
    reject_outcome_for_mode,
)
from energy_core.energy_control.mapper import action_from_strategy
from energy_core.energy_control.provider_factory import resolve_control_provider
from energy_core.energy_control.provider import IEnergyControlProvider
from energy_core.energy_control.repo import ControlActionRepository
from energy_core.energy_control.types import (
    ControlActionRecord,
    ControlOutcome,
    ControlResult,
    ControlStatus,
    ControlTarget,
    OptimizationAction,
)
from energy_core.price_engine.strategy import EnergyStrategySnapshot
from energy_core.price_engine.types import OptimizationMode


class EnergyControlService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        provider: IEnergyControlProvider | None = None,
    ) -> None:
        self._session = session
        self._repo = ControlActionRepository(session)
        self._state_repo = PriceEngineStateRepository(session)
        self._provider = provider or resolve_control_provider(session=session)

    async def status(self, site: SiteModel) -> ControlStatus:
        mode = OptimizationMode(site.optimization_mode)
        last = await self._repo.latest(site.id)
        return ControlStatus(
            site_id=site.id,
            optimization_mode=mode,
            control_enabled=bool(site.energy_control_enabled),
            writes_allowed=mode_allows_manual_apply(mode, control_enabled=bool(site.energy_control_enabled)),
            automatic_allowed=mode_allows_automatic_apply(mode, control_enabled=bool(site.energy_control_enabled)),
            provider=self._provider.provider_name,
            last_action=last,
        )

    async def update_settings(
        self,
        site: SiteModel,
        *,
        optimization_mode: OptimizationMode | None = None,
        control_enabled: bool | None = None,
    ) -> ControlStatus:
        if optimization_mode is not None:
            site.optimization_mode = optimization_mode.value
            await self._state_repo.upsert(site_id=site.id, optimization_mode=optimization_mode)
        if control_enabled is not None:
            site.energy_control_enabled = control_enabled
        await self._session.flush()
        return await self.status(site)

    async def preview(
        self,
        site: SiteModel,
        action: OptimizationAction,
        *,
        target: ControlTarget = ControlTarget.SITE,
        context: dict | None = None,
    ) -> ControlResult:
        mode = OptimizationMode(site.optimization_mode)
        if not mode_allows_preview(mode):
            result = ControlResult(
                action=action,
                target=target,
                outcome=ControlOutcome.SKIPPED,
                dry_run=True,
                reason="Preview not available in MONITOR_ONLY mode.",
                reason_sv="Förhandsvisning är inte tillgänglig i MONITOR_ONLY-läge.",
                provider=self._provider.provider_name,
            )
            await self._repo.append(site_id=site.id, optimization_mode=mode, result=result)
            return result

        result = await self._provider.apply_action(
            site_id=site.id,
            action=action,
            target=target,
            dry_run=True,
            context=context,
        )
        await self._repo.append(site_id=site.id, optimization_mode=mode, result=result)
        return result

    async def apply(
        self,
        site: SiteModel,
        action: OptimizationAction,
        *,
        target: ControlTarget = ControlTarget.SITE,
        context: dict | None = None,
    ) -> ControlResult:
        mode = OptimizationMode(site.optimization_mode)
        if not mode_allows_manual_apply(mode, control_enabled=bool(site.energy_control_enabled)):
            outcome = reject_outcome_for_mode(mode, control_enabled=bool(site.energy_control_enabled), automatic=False)
            result = ControlResult(
                action=action,
                target=target,
                outcome=outcome,
                dry_run=True,
                reason="Manual apply rejected by optimization mode or control flag.",
                reason_sv="Manuell applicering avvisades av optimeringsläge eller kontrollflagga.",
                provider=self._provider.provider_name,
            )
            await self._repo.append(site_id=site.id, optimization_mode=mode, result=result)
            return result

        result = await self._provider.apply_action(
            site_id=site.id,
            action=action,
            target=target,
            dry_run=False,
            context=context,
        )
        await self._repo.append(site_id=site.id, optimization_mode=mode, result=result)
        return result

    async def sync_from_strategy(
        self,
        site: SiteModel,
        snapshot: EnergyStrategySnapshot,
    ) -> ControlResult | None:
        action = action_from_strategy(snapshot)
        if action is None:
            return None

        mode = OptimizationMode(site.optimization_mode)
        if mode == OptimizationMode.MONITOR_ONLY:
            return None

        if mode == OptimizationMode.RECOMMEND:
            return await self.preview(
                site,
                action,
                context={"strategy_state": snapshot.strategy_state.value, "source": "collector"},
            )

        if not mode_allows_automatic_apply(mode, control_enabled=bool(site.energy_control_enabled)):
            return None

        return await self.apply(
            site,
            action,
            context={"strategy_state": snapshot.strategy_state.value, "source": "collector"},
        )

    async def recent(self, site_id: int, *, limit: int = 20) -> tuple[ControlActionRecord, ...]:
        return await self._repo.list_recent(site_id, limit=limit)
