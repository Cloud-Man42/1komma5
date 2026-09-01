"""Charging station resolution orchestrator."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from energy_core.integrations.charging_stations.abstractions import IChargingStationProvider
from energy_core.integrations.charging_stations.models import (
    ResolvedChargingLocation,
    StationResolutionStatus,
)
from energy_core.vehicles.charging_intelligence.knowledge_base import ChargingLocationKnowledgeBase
from energy_core.vehicles.charging_intelligence.location import (
    AWAY_LOCATION_NAME,
    ConfidenceBand,
    HaloCorrelationHint,
    IdentificationMethod,
)
from energy_core.vehicles.charging_intelligence.station_match import resolve_from_scores, score_candidates

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class VehicleResolutionContext:
    mercedes_plugged: bool | None = None
    mercedes_charging: bool | None = None
    mercedes_power_kw: float | None = None
    halo_charger_active: bool | None = None


class ChargingStationResolver:
    def __init__(
        self,
        provider: IChargingStationProvider,
        *,
        cache_repo=None,
        status_repo=None,
        cache_ttl_seconds: float = 86400.0,
        default_radius_m: int = 150,
    ) -> None:
        self._provider = provider
        self._cache_repo = cache_repo
        self._status_repo = status_repo
        self._cache_ttl_seconds = cache_ttl_seconds
        self._default_radius_m = default_radius_m

    @property
    def provider_enabled(self) -> bool:
        return self._provider.enabled

    async def resolve(
        self,
        lat: float | None,
        lon: float | None,
        *,
        knowledge_base: ChargingLocationKnowledgeBase,
        halo: HaloCorrelationHint | None = None,
        vehicle_state: VehicleResolutionContext | None = None,
        radius_m: int | None = None,
        previous_station_ids: set[str] | None = None,
        vehicle_id: int | None = None,
        session_id: int | None = None,
    ) -> ResolvedChargingLocation:
        radius = radius_m or self._default_radius_m
        vehicle_state = vehicle_state or VehicleResolutionContext()

        if lat is None or lon is None:
            away = knowledge_base.location_resolver.resolve(
                latitude=None,
                longitude=None,
                halo=halo,
                mercedes_plugged=vehicle_state.mercedes_plugged,
                mercedes_charging=vehicle_state.mercedes_charging,
                mercedes_power_kw=vehicle_state.mercedes_power_kw,
                halo_charger_active=vehicle_state.halo_charger_active,
            )
            return _from_location_match(away, status=StationResolutionStatus.UNKNOWN)

        known = knowledge_base.find_known_location(lat, lon)
        if known is not None and knowledge_base.is_home(known.location):
            if vehicle_state.mercedes_charging and vehicle_state.halo_charger_active:
                station_label = known.location.expected_operator or "Charge Amps Halo"
                name = f"{station_label} – {known.location.name}"
                return ResolvedChargingLocation(
                    location_name=name,
                    station_name=known.location.name,
                    operator_name=known.location.expected_operator,
                    charging_type=known.location.expected_charging_type or "AC",
                    connector_type="Type 2",
                    max_power_kw=11.0,
                    distance_meters=known.distance_m,
                    confidence=99,
                    confidence_band=ConfidenceBand.VERY_HIGH.value,
                    identification_method=IdentificationMethod.VEHICLE_AND_CHARGER_CORRELATION.value,
                    source="DIRECT_CHARGER",
                    station_resolution_status=StationResolutionStatus.OK,
                )

        geofence_name = known.location.name if known else AWAY_LOCATION_NAME
        expected_operator = known.location.expected_operator if known else None
        expected_type = known.location.expected_charging_type if known else None

        confirmed = await knowledge_base.find_confirmed_station_near(lat, lon, radius_m=float(radius))
        confirmed_ids = {c.provider_station_id for c in confirmed}

        if self._cache_repo is not None:
            cached = await self._cache_repo.get(latitude=lat, longitude=lon, radius_m=radius)
            if cached is not None:
                if self._status_repo is not None:
                    await self._status_repo.record_cache_hit()
                logger.info(
                    "provider=CHARGEFINDER vehicle_id=%s session_id=%s lat=%s lon=%s cache=hit",
                    vehicle_id,
                    session_id,
                    lat,
                    lon,
                )
                return cached
            if self._status_repo is not None:
                await self._status_repo.record_cache_miss()

        if not self._provider.enabled:
            if known is not None:
                return _geofence_only(known.location.name, expected_operator, expected_type)
            return _unknown_away()

        candidates = await self._provider.find_stations(
            latitude=lat,
            longitude=lon,
            radius_m=radius,
        )
        scored = score_candidates(
            candidates,
            expected_operator=expected_operator,
            expected_charging_type=expected_type,
            vehicle_charging_power_kw=vehicle_state.mercedes_power_kw,
            user_confirmed_ids=confirmed_ids,
            previous_station_ids=previous_station_ids,
            geofence_match=known is not None,
        )
        method = IdentificationMethod.CHARGEFINDER.value
        if known is not None:
            method = IdentificationMethod.CHARGEFINDER_AND_GEOFENCE.value
            geofence_name = known.location.name
        resolved = resolve_from_scores(
            scored,
            location_name=geofence_name,
            identification_method=method,
            source="CHARGEFINDER",
            geofence_match=known is not None,
        )

        if resolved.station_resolution_status == StationResolutionStatus.UNKNOWN and known is not None:
            resolved = _geofence_only(known.location.name, expected_operator, expected_type)

        if self._cache_repo is not None and resolved.station_resolution_status != StationResolutionStatus.MULTIPLE_CANDIDATES:
            await self._cache_repo.put(
                latitude=lat,
                longitude=lon,
                radius_m=radius,
                resolved=resolved,
                ttl_seconds=self._cache_ttl_seconds,
            )

        logger.info(
            "provider=CHARGEFINDER vehicle_id=%s session_id=%s lat=%s lon=%s radius=%s "
            "candidate_count=%s selected_station=%s distance=%s confidence=%s",
            vehicle_id,
            session_id,
            lat,
            lon,
            radius,
            len(candidates),
            resolved.selected_station.provider_station_id if resolved.selected_station else None,
            resolved.distance_meters,
            resolved.confidence,
        )
        return resolved


def _from_location_match(match, *, status: StationResolutionStatus) -> ResolvedChargingLocation:
    return ResolvedChargingLocation(
        location_name=match.location_name,
        station_name=match.location_name,
        operator_name=match.charger_operator,
        charging_type=None,
        connector_type=None,
        max_power_kw=None,
        distance_meters=None,
        confidence=match.confidence_score,
        confidence_band=match.confidence_band.value,
        identification_method=match.identification_method.value,
        source="LOCATION",
        station_resolution_status=status,
    )


def _geofence_only(name: str, operator: str | None, charging_type: str | None) -> ResolvedChargingLocation:
    return ResolvedChargingLocation(
        location_name=name,
        station_name=name,
        operator_name=operator,
        charging_type=charging_type,
        connector_type=None,
        max_power_kw=None,
        distance_meters=None,
        confidence=70,
        confidence_band=ConfidenceBand.MEDIUM.value,
        identification_method=IdentificationMethod.GEOFENCE.value,
        source="LOCAL",
        station_resolution_status=StationResolutionStatus.DEGRADED,
    )


def _unknown_away() -> ResolvedChargingLocation:
    return ResolvedChargingLocation(
        location_name=AWAY_LOCATION_NAME,
        station_name=None,
        operator_name=None,
        charging_type=None,
        connector_type=None,
        max_power_kw=None,
        distance_meters=None,
        confidence=0,
        confidence_band=ConfidenceBand.UNKNOWN.value,
        identification_method=IdentificationMethod.UNKNOWN.value,
        source="NONE",
        station_resolution_status=StationResolutionStatus.UNKNOWN,
    )
