"""Charge Amps control provider — EV writes via Halo API and charging_mode."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.chargers.framework.factory import ChargerAdapterFactory
from energy_core.chargers.framework.legacy_bridge import LegacyControlBridge
from energy_core.charging.anti_flapping import AntiFlappingConfig, AntiFlappingState
from energy_core.charging.command_controller import ChargingCommandController, CommandApplyResult
from energy_core.charging.models import ChargingDecision
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.models import EvChargerModel, SiteModel
from energy_core.energy_control.types import ControlOutcome, ControlResult, ControlTarget, OptimizationAction
from energy_core.energy_optimizer.types import EnergyAction

_BATTERY_ACTIONS = frozenset(
    {
        EnergyAction.STORE_IN_BATTERY,
        EnergyAction.DISCHARGE_BATTERY,
        EnergyAction.EXPORT_TO_GRID,
    }
)

_ACTION_TO_CHARGING_MODE = {
    EnergyAction.USE_NOW: "QUICK_CHARGE",
    EnergyAction.WAIT: "PAUSED",
}


def _action_to_charging_mode(action: OptimizationAction) -> str | None:
    return _ACTION_TO_CHARGING_MODE.get(action)


def _select_charger(chargers: list[EvChargerModel], *, charger_id: int | None) -> EvChargerModel | None:
    if charger_id is not None:
        for charger in chargers:
            if charger.id == charger_id:
                return charger
        return None
    for charger in chargers:
        if charger.bridge_enabled:
            return charger
    return None


def _decision_for_action(action: OptimizationAction, charger: EvChargerModel) -> ChargingDecision:
    if action == EnergyAction.USE_NOW:
        current = float(charger.max_current_a or 16.0)
        return ChargingDecision(
            requested_current_a=current,
            applied_current_a=current,
            requested_power_w=None,
            action="set_current",
            reason="energy_control USE_NOW",
            policy_mode="QUICK_CHARGE",
        )
    return ChargingDecision(
        requested_current_a=0.0,
        applied_current_a=0.0,
        requested_power_w=None,
        action="stop",
        reason="energy_control WAIT",
        policy_mode="PAUSED",
    )


class ChargeAmpsControlProvider:
    provider_name = "chargeamps"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._chargers = EvChargerRepository(session)

    async def _get_site(self, site_id: int) -> SiteModel | None:
        return await self._session.scalar(select(SiteModel).where(SiteModel.id == site_id))

    async def apply_action(
        self,
        *,
        site_id: int,
        action: OptimizationAction,
        target: ControlTarget,
        dry_run: bool,
        context: dict | None = None,
    ) -> ControlResult:
        site = await self._get_site(site_id)
        if site is None:
            return self._result(
                action,
                target,
                dry_run,
                ControlOutcome.FAILED,
                reason="Site not found.",
                reason_sv="Anläggningen hittades inte.",
            )

        if action in _BATTERY_ACTIONS or (
            target in {ControlTarget.BATTERY, ControlTarget.SITE} and action != EnergyAction.WAIT
        ):
            return self._result(
                action,
                target,
                dry_run,
                ControlOutcome.SKIPPED,
                reason="Battery/site control is not implemented for Charge Amps provider.",
                reason_sv="Batteri-/anläggningsstyrning via Charge Amps är inte implementerad.",
            )

        charging_mode = _action_to_charging_mode(action)
        if charging_mode is None:
            return self._result(
                action,
                target,
                dry_run,
                ControlOutcome.SKIPPED,
                reason=f"No Charge Amps mapping for action {action.value}.",
                reason_sv=f"Ingen Charge Amps-mappning för åtgärden {action.value}.",
            )

        ctx = context or {}
        charger_id = ctx.get("charger_id")
        if charger_id is not None and not isinstance(charger_id, int):
            try:
                charger_id = int(charger_id)
            except (TypeError, ValueError):
                charger_id = None

        chargers = await self._chargers.list_for_site(site.id)
        charger = _select_charger(chargers, charger_id=charger_id)
        if charger is None:
            return self._result(
                action,
                target,
                dry_run,
                ControlOutcome.REJECTED,
                reason="No bridge-enabled Charge Amps charger found.",
                reason_sv="Ingen bridge-aktiverad Charge Amps-laddare hittades.",
            )

        preview_payload: dict[str, Any] = {
            "charger_id": charger.id,
            "charger_name": charger.name,
            "charging_mode": charging_mode,
            "bridge_enabled": bool(charger.bridge_enabled),
        }

        if dry_run:
            return self._result(
                action,
                target,
                True,
                ControlOutcome.PREVIEW,
                reason=f"Would set charging_mode={charging_mode} on charger {charger.id}.",
                reason_sv=f"Skulle sätta charging_mode={charging_mode} på laddare {charger.id}.",
                payload=preview_payload,
            )

        if not charger.bridge_enabled:
            return self._result(
                action,
                target,
                False,
                ControlOutcome.REJECTED,
                reason="Charge Amps bridge is disabled on charger.",
                reason_sv="Charge Amps-bryggan är avstängd på laddaren.",
                payload=preview_payload,
            )

        await self._chargers.update(charger, charging_mode=charging_mode)
        decision = _decision_for_action(action, charger)
        adapter = LegacyControlBridge(ChargerAdapterFactory.from_charger_model(charger))
        controller = ChargingCommandController(
            adapter,
            anti_flapping=AntiFlappingState(),
            anti_config=AntiFlappingConfig(),
        )
        now = datetime.now(tz=UTC)

        try:
            apply_result: CommandApplyResult = await controller.apply(decision, now=now)
        except Exception as exc:
            return self._result(
                action,
                target,
                False,
                ControlOutcome.FAILED,
                reason=f"Charge Amps apply failed: {exc}",
                reason_sv=f"Charge Amps-applicering misslyckades: {exc}",
                payload={**preview_payload, "error": str(exc)},
            )

        if apply_result.error_code:
            return self._result(
                action,
                target,
                False,
                ControlOutcome.FAILED,
                reason=f"Charge Amps command failed: {apply_result.error_code}",
                reason_sv=f"Charge Amps-kommando misslyckades: {apply_result.error_code}",
                payload={
                    **preview_payload,
                    "error_code": apply_result.error_code,
                    "applied": apply_result.applied,
                    "applied_current_a": apply_result.applied_current_a,
                },
            )

        return self._result(
            action,
            target,
            False,
            ControlOutcome.APPLIED,
            reason=f"Applied charging_mode={charging_mode} on charger {charger.id}.",
            reason_sv=f"Satte charging_mode={charging_mode} på laddare {charger.id}.",
            payload={
                **preview_payload,
                "applied": apply_result.applied,
                "applied_current_a": apply_result.applied_current_a,
                "action": decision.action,
            },
        )

    def _result(
        self,
        action: OptimizationAction,
        target: ControlTarget,
        dry_run: bool,
        outcome: ControlOutcome,
        *,
        reason: str,
        reason_sv: str,
        payload: dict[str, Any] | None = None,
    ) -> ControlResult:
        return ControlResult(
            action=action,
            target=target,
            outcome=outcome,
            dry_run=dry_run,
            reason=reason,
            reason_sv=reason_sv,
            provider=self.provider_name,
            payload=payload or {},
        )
