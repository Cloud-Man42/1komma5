"""Heartbeat cloud EMS control provider — EV PATCH writes via Heartbeat API."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.heartbeat_discovery_repo import HeartbeatDiscoveryRepository
from energy_core.db.models import SiteModel
from energy_core.energy_control.types import ControlOutcome, ControlResult, ControlTarget, OptimizationAction
from energy_core.energy_optimizer.types import EnergyAction
from energy_core.heartbeat.write_test.client import HeartbeatWriteClient
from energy_core.heartbeat_client_factory import create_heartbeat_client

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


class HeartbeatControlProvider:
    provider_name = "heartbeat"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._discovery = HeartbeatDiscoveryRepository(session)

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
                reason="Battery/site EMS writes are not implemented for Heartbeat provider.",
                reason_sv="Batteri-/anläggningsstyrning via Heartbeat är inte implementerad ännu.",
            )

        charging_mode = _action_to_charging_mode(action)
        if charging_mode is None:
            return self._result(
                action,
                target,
                dry_run,
                ControlOutcome.SKIPPED,
                reason=f"No Heartbeat mapping for action {action.value}.",
                reason_sv=f"Ingen Heartbeat-mappning för åtgärden {action.value}.",
            )

        if not site.external_system_id:
            return self._result(
                action,
                target,
                dry_run,
                ControlOutcome.REJECTED,
                reason="Site has no Heartbeat system ID.",
                reason_sv="Anläggningen saknar Heartbeat system-ID.",
            )

        ctx = context or {}
        ev_id = ctx.get("heartbeat_ev_id")
        if ev_id is None:
            mappings = await self._discovery.list_mappings(site.id)
            if mappings:
                ev_id = mappings[0].heartbeat_ev_id
        if ev_id is None:
            from energy_core.db.ev_charger_repo import EvChargerRepository

            chargers = await EvChargerRepository(self._session).list_for_site(site.id)
            for charger in chargers:
                if charger.heartbeat_ev_id:
                    ev_id = charger.heartbeat_ev_id
                    break
        if not ev_id:
            return self._result(
                action,
                target,
                dry_run,
                ControlOutcome.REJECTED,
                reason="No Heartbeat EV mapping available.",
                reason_sv="Ingen Heartbeat EV-mappning tillgänglig.",
            )

        payload: dict[str, Any] = {"chargeSettings": {"chargingMode": charging_mode}}
        preview_payload = {
            "method": "PATCH",
            "path": f"/v1/systems/{site.external_system_id}/devices/evs/{ev_id}",
            "payload": payload,
            "heartbeat_ev_id": ev_id,
        }

        if dry_run:
            return self._result(
                action,
                target,
                True,
                ControlOutcome.PREVIEW,
                reason=f"Would set chargingMode={charging_mode} on EV {ev_id}.",
                reason_sv=f"Skulle sätta chargingMode={charging_mode} på EV {ev_id}.",
                payload=preview_payload,
            )

        settings = await self._discovery.get_or_create_bridge_settings(site.id)
        if not settings.write_enabled:
            return self._result(
                action,
                target,
                False,
                ControlOutcome.REJECTED,
                reason="Heartbeat write_enabled is false in bridge settings.",
                reason_sv="Heartbeat-skrivning är avstängd (write_enabled).",
                payload=preview_payload,
            )

        mappings = await self._discovery.list_mappings(site.id)
        if mappings and mappings[0].confidence_pct < settings.confidence_threshold_pct:
            return self._result(
                action,
                target,
                False,
                ControlOutcome.REJECTED,
                reason="EV mapping confidence below bridge threshold.",
                reason_sv="EV-mappningens confidence är under tröskeln.",
                payload=preview_payload,
            )

        client = await create_heartbeat_client(self._session)
        if client is None:
            return self._result(
                action,
                target,
                False,
                ControlOutcome.FAILED,
                reason="Heartbeat client not configured.",
                reason_sv="Heartbeat-klienten är inte konfigurerad.",
                payload=preview_payload,
            )

        write_client = HeartbeatWriteClient(client)
        status, body = await write_client.patch_ev(site.external_system_id, str(ev_id), payload)
        if status >= 400:
            return self._result(
                action,
                target,
                False,
                ControlOutcome.FAILED,
                reason=f"Heartbeat PATCH failed with HTTP {status}.",
                reason_sv=f"Heartbeat PATCH misslyckades med HTTP {status}.",
                payload={"http_status": status, "response": body, **preview_payload},
            )

        return self._result(
            action,
            target,
            False,
            ControlOutcome.APPLIED,
            reason=f"Applied chargingMode={charging_mode} on EV {ev_id}.",
            reason_sv=f"Satte chargingMode={charging_mode} på EV {ev_id}.",
            payload={"http_status": status, "response": body, **preview_payload},
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
