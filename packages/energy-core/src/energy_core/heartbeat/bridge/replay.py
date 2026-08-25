"""Replay Heartbeat events through virtual charger decision engine."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.heartbeat_discovery_repo import HeartbeatDiscoveryRepository
from energy_core.heartbeat.bridge.constraints import BridgeConstraints
from energy_core.heartbeat.bridge.decision_engine import VirtualChargerDecisionEngine
from energy_core.heartbeat_client_factory import create_heartbeat_client


class VirtualChargerReplayService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = HeartbeatDiscoveryRepository(session)
        self._charger_repo = EvChargerRepository(session)
        self._engine = VirtualChargerDecisionEngine(session)

    async def run(self, site_slug: str, *, hours: int = 24) -> tuple[dict[str, Any], str]:
        site = await self._charger_repo.get_site_by_slug(site_slug)
        if site is None:
            raise ValueError("Site not found")

        settings = await self._repo.get_or_create_bridge_settings(site.id)
        if not settings.replay_enabled:
            raise ValueError("Replay is disabled for this site")
        if not site.external_system_id:
            raise ValueError("Site has no Heartbeat system ID")

        client = await create_heartbeat_client(self._session)
        if client is None:
            raise ValueError("Heartbeat client not available")

        started = datetime.now(UTC)
        now = datetime.now(UTC)
        optimizations = await client.fetch_optimizations(
            site.external_system_id,
            from_iso=(now - timedelta(hours=hours)).isoformat(),
            to_iso=now.isoformat(),
        )
        evs = await client.list_evs(site.external_system_id)
        ems = await client.fetch_ems_settings(site.external_system_id)
        ev_profile = evs[0] if evs else None

        chargers = await self._charger_repo.list_for_site(site.id)
        charger = chargers[0] if chargers else None
        max_power = (charger.max_power_w if charger and charger.max_power_w else 11000.0)

        would_start = 0
        would_pause = 0
        cycles: list[dict[str, Any]] = []
        events = optimizations or [{"source": "ems_baseline"}]

        for item in events:
            batch = [item] if item.get("source") != "ems_baseline" else []
            intent, command, _payload = await self._engine.evaluate(
                site.id,
                charger_id=charger.id if charger else None,
                heartbeat_ev_id=str(ev_profile.get("id")) if ev_profile else None,
                ev_profile=ev_profile,
                ems_settings=ems,
                optimizations=batch,
                constraints=BridgeConstraints(
                    heartbeat_requested_power_w=max_power,
                    solar_available_power_w=max_power * 0.5,
                    smart_charging_allowed_power_w=max_power,
                    load_balancer_allowed_power_w=max_power,
                    halo_hardware_limit_w=max_power,
                    vehicle_limit_w=max_power,
                    site_limit_w=max_power,
                ),
            )
            if command.action in {"set_current", "start"} and command.current_a and command.current_a > 0:
                would_start += 1
            if command.action in {"stop", "pause"}:
                would_pause += 1
            cycles.append(
                {
                    "ai_decision": intent.raw_decision_type,
                    "mode": intent.charging_mode,
                    "command": command.action,
                    "current_a": command.current_a,
                    "simulated": command.simulated,
                }
            )

        report = {
            "hours": hours,
            "optimization_events": len(optimizations),
            "ems_baseline_included": len(optimizations) == 0,
            "would_start_count": would_start,
            "would_pause_count": would_pause,
            "start_stop_cycles": would_start,
            "cycles": cycles[:100],
        }
        report_text = (
            f"Replay {hours}h: {len(optimizations)} Heartbeat AI events"
            + (" + EMS baseline" if not optimizations else "")
            + f", would start {would_start}, would pause {would_pause}, "
            f"start/stop cycles: {would_start}"
        )
        run_id = await self._repo.save_replay_run(
            site.id,
            hours,
            report,
            report_text,
            started,
            datetime.now(UTC),
        )
        report["run_id"] = run_id
        await self._session.commit()
        return report, report_text
