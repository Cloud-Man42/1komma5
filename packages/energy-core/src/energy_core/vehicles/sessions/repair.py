"""Repair completed vehicle charge sessions with missing station or energy."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.chargefinder_integration_status_repo import ChargeFinderIntegrationStatusRepository
from energy_core.db.charging_location_repo import ChargingLocationRepository
from energy_core.db.charging_station_lookup_cache_repo import ChargingStationLookupCacheRepository
from energy_core.db.charging_station_repo import ChargingStationRepository
from energy_core.db.vehicle_charge_session_repo import VehicleChargeSessionRecord, VehicleChargeSessionRepository
from energy_core.integrations.charging_stations.chargefinder.provider import ChargeFinderChargingStationProvider
from energy_core.vehicles.charging_intelligence.knowledge_base import ChargingLocationKnowledgeBase
from energy_core.vehicles.charging_intelligence.station_resolver import ChargingStationResolver
from energy_core.vehicles.sessions.finalization import is_unknown_location, repair_completed_session_fields

logger = logging.getLogger(__name__)


async def repair_completed_sessions(
    db: AsyncSession,
    *,
    site_id: int,
    vehicle_id: int,
    settings=None,
    limit: int = 20,
) -> int:
    repo = VehicleChargeSessionRepository(db)
    records = await repo.list_for_vehicle(vehicle_id)
    candidates = [
        record
        for record in records
        if record.status == "COMPLETED"
        and (
            is_unknown_location(record.location_name)
            or (record.halo_energy_kwh or 0) <= 0
        )
    ][:limit]
    if not candidates:
        return 0

    location_repo = ChargingLocationRepository(db)
    locations = await location_repo.list_for_site(site_id)
    knowledge_base = ChargingLocationKnowledgeBase(db, site_id=site_id, locations=locations)
    status_repo = ChargeFinderIntegrationStatusRepository(db)
    provider = (
        ChargeFinderChargingStationProvider.from_settings(settings)
        if settings is not None
        else ChargeFinderChargingStationProvider.disabled()
    )
    resolver = ChargingStationResolver(
        provider,
        cache_repo=ChargingStationLookupCacheRepository(db),
        status_repo=status_repo,
        cache_ttl_seconds=getattr(settings, "chargefinder_cache_ttl_seconds", 604800.0) if settings else 604800.0,
        default_radius_m=getattr(settings, "chargefinder_search_radius_m", 150) if settings else 150,
    )

    repaired = 0
    for record in candidates:
        station_resolution = None
        if record.latitude is not None and record.longitude is not None:
            station_resolution = await resolver.resolve(
                record.latitude,
                record.longitude,
                knowledge_base=knowledge_base,
                vehicle_id=vehicle_id,
                session_id=record.id,
            )
        patch = repair_completed_session_fields(record, station_resolution=station_resolution)
        if not patch:
            continue
        await repo.patch_session(record.id, **patch)
        repaired += 1
        logger.info(
            "Repaired vehicle charge session session_id=%s vehicle_id=%s fields=%s",
            record.id,
            vehicle_id,
            sorted(patch.keys()),
        )
    if repaired:
        await db.flush()
    return repaired
