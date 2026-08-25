"""Virtual charger decision engine — translates Heartbeat intent to Halo commands."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.heartbeat_discovery_repo import HeartbeatDiscoveryRepository
from energy_core.heartbeat.bridge.constraints import BridgeConstraintResolver, BridgeConstraints, intent_to_halo_command
from energy_core.heartbeat.bridge.intent import HeartbeatIntentParser
from energy_core.heartbeat.discovery.models import BridgeLifecycleState, HaloCommand, HeartbeatIntent
from energy_core.heartbeat.bridge.simulation import SimulationCommandSink


class VirtualChargerDecisionEngine:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = HeartbeatDiscoveryRepository(session)
        self._parser = HeartbeatIntentParser()
        self._resolver = BridgeConstraintResolver()
        self._simulation = SimulationCommandSink(session)

    async def evaluate(
        self,
        site_id: int,
        *,
        charger_id: int | None,
        heartbeat_ev_id: str | None,
        ev_profile: dict[str, Any] | None,
        ems_settings: dict[str, Any] | None,
        optimizations: list[dict[str, Any]] | None,
        constraints: BridgeConstraints,
        confidence: float = 100.0,
    ) -> tuple[HeartbeatIntent, HaloCommand, dict[str, Any]]:
        settings = await self._repo.get_or_create_bridge_settings(site_id)
        intent = self._parser.parse(
            ev_profile=ev_profile,
            ems_settings=ems_settings,
            optimizations=optimizations,
            confidence=confidence,
        )
        resolved = self._resolver.resolve(
            intent,
            constraints,
            battery_priority_mode=settings.battery_priority_mode,
        )
        command = intent_to_halo_command(intent, resolved)

        bridge_state = BridgeLifecycleState.SIMULATION.value if settings.simulation_mode else BridgeLifecycleState.READY.value
        decision_payload = {
            "intent": asdict(intent),
            "resolved": asdict(resolved),
            "command": asdict(command),
        }

        await self._repo.save_decision(
            site_id,
            charger_id=charger_id,
            heartbeat_ev_id=heartbeat_ev_id,
            bridge_state=bridge_state,
            heartbeat_mode=intent.charging_mode,
            ai_decision=intent.raw_decision_type,
            decision=decision_payload,
            reason=resolved.reason,
        )

        if settings.simulation_mode or not settings.physical_control_enabled:
            command = await self._simulation.apply(site_id, charger_id, command)
        elif settings.virtual_bridge_enabled and settings.physical_control_enabled:
            from energy_core.chargers.framework.factory import ChargerAdapterFactory
            from energy_core.chargers.framework.legacy_bridge import LegacyControlBridge

            if charger_id is not None:
                from energy_core.db.ev_charger_repo import EvChargerRepository

                charger_repo = EvChargerRepository(self._session)
                charger = await charger_repo.get_by_id(charger_id)
                if charger is not None:
                    adapter = LegacyControlBridge(ChargerAdapterFactory.from_charger_model(charger))
                    if command.action == "set_current" and command.current_a:
                        await adapter.set_max_current(command.current_a)
                    elif command.action == "stop":
                        await adapter.stop_charging()
                    elif command.action == "start" and command.current_a:
                        await adapter.start_charging()
                        await adapter.set_max_current(command.current_a)
            command = HaloCommand(
                action=command.action,
                current_a=command.current_a,
                reason=command.reason,
                simulated=False,
            )
            await self._repo.save_command(
                site_id,
                charger_id=charger_id,
                action=command.action,
                current_a=command.current_a,
                reason=command.reason,
                simulated=False,
                applied=True,
            )
        elif settings.virtual_bridge_enabled:
            command = HaloCommand(
                action=command.action,
                current_a=command.current_a,
                reason=command.reason,
                simulated=False,
            )
            await self._repo.save_command(
                site_id,
                charger_id=charger_id,
                action=command.action,
                current_a=command.current_a,
                reason=command.reason,
                simulated=False,
                applied=True,
            )

        return intent, command, decision_payload

    async def record_failsafe(
        self,
        site_id: int,
        *,
        charger_id: int | None,
        heartbeat_ev_id: str | None,
        reason: str,
    ) -> None:
        await self._repo.save_decision(
            site_id,
            charger_id=charger_id,
            heartbeat_ev_id=heartbeat_ev_id,
            bridge_state=BridgeLifecycleState.FAILSAFE.value,
            heartbeat_mode=None,
            ai_decision=None,
            decision={"failsafe": True, "reason": reason},
            reason=reason,
        )
