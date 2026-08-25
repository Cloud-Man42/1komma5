"""Simulation command sink — logs Halo commands without physical execution."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.heartbeat_discovery_repo import HeartbeatDiscoveryRepository
from energy_core.heartbeat.discovery.models import HaloCommand


class SimulationCommandSink:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = HeartbeatDiscoveryRepository(session)

    async def apply(
        self,
        site_id: int,
        charger_id: int | None,
        command: HaloCommand,
    ) -> HaloCommand:
        await self._repo.save_command(
            site_id,
            charger_id=charger_id,
            action=command.action,
            current_a=command.current_a,
            reason=f"SIMULATION: {command.reason}",
            simulated=True,
            applied=False,
        )
        return HaloCommand(
            action=command.action,
            current_a=command.current_a,
            reason=f"SIMULATION: NO COMMAND SENT — {command.reason}",
            simulated=True,
        )
