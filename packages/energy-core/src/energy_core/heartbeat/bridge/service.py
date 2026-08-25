"""Heartbeat EV bridge orchestration service."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.heartbeat_discovery_repo import HeartbeatDiscoveryRepository
from energy_core.heartbeat.bridge.emic_context import enrich_discovery_with_emic_vehicles
from energy_core.heartbeat.discovery.models import BridgeLifecycleState, HeartbeatEvDiscoveryResult
from energy_core.heartbeat.discovery.service import HeartbeatEvDiscoveryService
from energy_core.heartbeat_client_factory import create_heartbeat_client


class HeartbeatEvBridgeService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._discovery_repo = HeartbeatDiscoveryRepository(session)
        self._charger_repo = EvChargerRepository(session)
        self._discovery = HeartbeatEvDiscoveryService()

    async def run_discovery(self, site_slug: str) -> tuple[HeartbeatEvDiscoveryResult, int]:
        site = await self._charger_repo.get_site_by_slug(site_slug)
        if site is None:
            raise ValueError("Site not found")
        if not site.external_system_id:
            raise ValueError("Anläggningen saknar HeartBeat system-ID.")

        settings = await self._discovery_repo.get_or_create_bridge_settings(site.id)
        if not settings.discovery_enabled:
            raise ValueError("Discovery is disabled for this site")

        chargers = await self._charger_repo.list_for_site(site.id)
        halo_found = any(c.chargeamp_charger_id for c in chargers)
        halo_online = any(c.last_halo_connected for c in chargers)

        client = await create_heartbeat_client(self._session)
        result = await self._discovery.run(
            client=client,  # type: ignore[arg-type]
            site_slug=site.slug,
            site_name=site.name,
            system_id=site.external_system_id,
            halo_found=halo_found,
            halo_online=halo_online,
        )
        result = await enrich_discovery_with_emic_vehicles(self._session, site.id, result)

        physical_charger_id = chargers[0].id if len(chargers) == 1 else None
        run_id = await self._discovery_repo.save_discovery_run(site.id, result)
        if result.resolved_ev_id.confidence_pct >= settings.confidence_threshold_pct:
            await self._discovery_repo.upsert_mapping_from_discovery(
                site.id,
                result,
                physical_charger_id=physical_charger_id,
            )
        await self._session.commit()
        return result, run_id

    async def bridge_status(self, site_slug: str) -> dict[str, Any]:
        site = await self._charger_repo.get_site_by_slug(site_slug)
        if site is None:
            raise ValueError("Site not found")

        settings = await self._discovery_repo.get_or_create_bridge_settings(site.id)
        mappings = await self._discovery_repo.list_mappings(site.id)
        runs = await self._discovery_repo.list_runs(site.id, limit=1)
        chargers = await self._charger_repo.list_for_site(site.id)

        latest = runs[0] if runs else None
        mapping = mappings[0] if mappings else None

        return {
            "heartbeat_connection": "ONLINE" if site.external_system_id else "NOT_CONFIGURED",
            "ev_profile": "FOUND" if mapping else ("FOUND" if latest and latest.resolved_ev_id else "NOT FOUND"),
            "ev_id": latest.resolved_ev_id if latest else (mapping.heartbeat_ev_id if mapping else None),
            "confidence_pct": latest.confidence_pct if latest else (mapping.confidence_pct if mapping else None),
            "physical_hb_wallbox": "UNKNOWN",
            "charge_amps_halo": "FOUND" if any(c.chargeamp_charger_id for c in chargers) else "NOT FOUND",
            "halo_online": any(c.last_halo_connected for c in chargers),
            "virtual_bridge": "READY" if mapping and mapping.enabled else "NOT READY",
            "setup_classification": latest.conclusion_class if latest else None,
            "bridge_lifecycle": latest.bridge_lifecycle if latest else BridgeLifecycleState.DISABLED.value,
            "simulation_mode": settings.simulation_mode,
            "physical_control": "ENABLED" if settings.physical_control_enabled else "DISABLED",
            "write_enabled": settings.write_enabled,
            "settings": asdict(settings),
            "mappings": [asdict(m) for m in mappings],
        }
