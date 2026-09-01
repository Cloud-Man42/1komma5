"""Orchestrate vehicle charge sessions in the collector loop."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, replace

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.chargers.meter_adapter import ChargeAmpsMeterAdapter
from energy_core.db.chargefinder_integration_status_repo import ChargeFinderIntegrationStatusRepository
from energy_core.db.charging_location_repo import ChargingLocationRepository
from energy_core.db.charging_station_lookup_cache_repo import ChargingStationLookupCacheRepository
from energy_core.db.charging_station_repo import ChargingStationRepository
from energy_core.db.models import SiteModel
from energy_core.db.vehicle_repo import VehicleProviderRepository, VehicleRepository
from energy_core.ev_accounting.models import SiteEnergySample
from energy_core.heartbeat.live_overview import parse_live_overview
from energy_core.integrations.charging_stations.chargefinder.provider import ChargeFinderChargingStationProvider
from energy_core.integrations.charging_stations.chargefinder_metrics import get_chargefinder_metrics
from energy_core.integrations.charging_stations.models import StationResolutionStatus
from energy_core.secrets import CredentialCipher
from energy_core.vehicles.charging_intelligence.knowledge_base import ChargingLocationKnowledgeBase
from energy_core.vehicles.charging_intelligence.location import HaloCorrelationHint
from energy_core.vehicles.charging_intelligence.service import ChargingSessionService
from energy_core.vehicles.charging_intelligence.station_resolver import (
    ChargingStationResolver,
    VehicleResolutionContext,
)
from energy_core.vehicles.correlation.repo import VehicleHaloCorrelationRepository
from energy_core.vehicles.sessions.sampler import VehicleChargeSessionSampler
from energy_core.vehicles.sessions.session_service import VehicleChargeSessionService

logger = logging.getLogger(__name__)


@dataclass
class _VehicleLookupState:
    was_charging: bool = False
    lookup_done_for_session: bool = False
    uncertain_retry_done: bool = False
    last_resolution: object | None = None


class VehicleChargeSessionCoordinator:
    def __init__(self, settings=None, station_resolver: ChargingStationResolver | None = None) -> None:
        self._session_service = VehicleChargeSessionService()
        self._sampler = VehicleChargeSessionSampler(self._session_service)
        self._csi = ChargingSessionService()
        self._settings = settings
        self._station_resolver = station_resolver
        self._metrics = get_chargefinder_metrics()
        self._lookup_state: dict[int, _VehicleLookupState] = {}

    @property
    def session_service(self) -> VehicleChargeSessionService:
        return self._session_service

    @property
    def csi_service(self) -> ChargingSessionService:
        return self._csi

    def _build_resolver(self, db: AsyncSession) -> ChargingStationResolver:
        if self._station_resolver is not None:
            return self._station_resolver

        settings = self._settings
        status_repo = ChargeFinderIntegrationStatusRepository(db)

        def on_lookup_complete(success: bool, latency_ms: int, error: str | None, lookup_mode: str) -> None:
            self._metrics.record_lookup(
                success=success,
                latency_ms=latency_ms,
                blocked=error is not None and "blocked" in (error or "").lower(),
                parser_failure=error is not None and "parse" in (error or "").lower(),
            )

        provider = (
            ChargeFinderChargingStationProvider.from_settings(settings, on_lookup_complete=on_lookup_complete)
            if settings is not None
            else ChargeFinderChargingStationProvider.disabled()
        )
        return ChargingStationResolver(
            provider,
            cache_repo=ChargingStationLookupCacheRepository(db),
            status_repo=status_repo,
            cache_ttl_seconds=getattr(settings, "chargefinder_cache_ttl_seconds", 604800.0) if settings else 604800.0,
            default_radius_m=getattr(settings, "chargefinder_search_radius_m", 150) if settings else 150,
        )

    async def setup(self, session: AsyncSession) -> None:
        await self._session_service.resume_active_sessions(session, self._csi)

    async def process_site(
        self,
        db: AsyncSession,
        *,
        site: SiteModel,
        live_overview: dict | None,
        is_sqlite: bool,
    ) -> int:
        provider_repo = VehicleProviderRepository(db)
        connection = await provider_repo.get_for_site(site.id)
        if connection is None or not connection.enabled:
            return 0

        location_repo = ChargingLocationRepository(db)
        await location_repo.seed_home_from_site_config(site)
        locations = await location_repo.list_for_site(site.id)
        self._csi.set_locations(locations)
        knowledge_base = ChargingLocationKnowledgeBase(db, site_id=site.id, locations=locations)
        resolver = self._build_resolver(db)
        station_repo = ChargingStationRepository(db)

        vehicle_repo = VehicleRepository(db, is_sqlite=is_sqlite)
        correlation_repo = VehicleHaloCorrelationRepository(db)
        vehicles = await vehicle_repo.list_for_site(site.id)
        if not vehicles:
            return 0

        energy_sample = self._energy_sample_from_overview(live_overview, site)
        processed = 0
        for vehicle_record in vehicles:
            vehicle = await vehicle_repo.get(vehicle_record.id)
            if vehicle is None:
                continue

            charger = await correlation_repo.resolve_charger(vehicle)
            latest = await vehicle_repo.get_latest_state(vehicle.id)
            correlation = await correlation_repo.get(vehicle.id)
            identification_confidence = correlation.confidence if correlation else None

            station_resolution = await self._resolve_station_if_needed(
                db,
                resolver=resolver,
                knowledge_base=knowledge_base,
                station_repo=station_repo,
                latest=latest,
                correlation=correlation,
                vehicle_id=vehicle.id,
            )

            meter = None
            if charger is not None and charger.chargeamp_charger_id:
                try:
                    meter = await self._meter_snapshot(charger)
                except Exception:
                    logger.exception("Vehicle charge meter failed vehicle_id=%s", vehicle.id)
            try:
                processed += await self._process_vehicle(
                    db,
                    vehicle=vehicle,
                    charger=charger,
                    site=site,
                    latest=latest,
                    meter=meter,
                    energy_sample=energy_sample,
                    identification_confidence=identification_confidence,
                    halo_correlation=correlation,
                    station_resolution=station_resolution,
                    is_sqlite=is_sqlite,
                )
            except Exception:
                logger.exception("Vehicle charge session failed vehicle_id=%s", vehicle.id)
        return processed

    async def _process_vehicle(
        self,
        db: AsyncSession,
        *,
        vehicle,
        charger,
        site: SiteModel,
        latest,
        meter,
        energy_sample: SiteEnergySample,
        identification_confidence: float | None,
        halo_correlation=None,
        station_resolution=None,
        is_sqlite: bool,
    ) -> int:
        if meter is None:
            await self._session_service.process_vehicle_without_charger(
                db,
                vehicle=vehicle,
                site=site,
                latest=latest,
                csi=self._csi,
                identification_confidence=identification_confidence,
                halo_correlation=halo_correlation,
                station_resolution=station_resolution,
            )
            return 1

        is_charging = bool(latest and latest.is_charging)
        await self._session_service.process_vehicle(
            db,
            vehicle=vehicle,
            charger=charger,
            site=site,
            latest=latest,
            meter=meter,
            identification_confidence=identification_confidence,
            csi=self._csi,
            halo_correlation=halo_correlation,
            station_resolution=station_resolution,
        )
        await self._sampler.sample_active_session(
            db,
            vehicle=vehicle,
            charger=charger,
            site=site,
            meter=meter,
            energy_sample=energy_sample,
            is_sqlite=is_sqlite,
            is_charging=is_charging,
        )
        return 1

    async def _meter_snapshot(self, charger):
        api_key = CredentialCipher().decrypt(charger.chargeamps_api_key) or os.getenv("CHARGEAMPS_API_KEY", "")
        meter_adapter = ChargeAmpsMeterAdapter.build(
            charger.chargeamp_charger_id,
            api_key=api_key,
            phases=charger.phases,
            nominal_voltage_v=charger.nominal_voltage_v,
        )
        return await meter_adapter.get_snapshot()

    def _energy_sample_from_overview(self, live_overview: dict | None, site: SiteModel) -> SiteEnergySample:
        duration_hours = 60.0 / 3600.0
        if not live_overview:
            return SiteEnergySample(
                pv_power_w=0,
                house_consumption_w=0,
                grid_import_w=0,
                grid_export_w=0,
                battery_charge_w=0,
                battery_discharge_w=0,
                ev_power_w=0,
                electricity_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
                duration_hours=duration_hours,
            )
        parsed = parse_live_overview(live_overview)
        return SiteEnergySample(
            pv_power_w=parsed.get("pv_power_w") or 0.0,
            house_consumption_w=parsed.get("home_consumption_w") or 0.0,
            grid_import_w=parsed.get("grid_import_w") or 0.0,
            grid_export_w=parsed.get("grid_export_w") or 0.0,
            battery_charge_w=parsed.get("battery_charge_power_w") or 0.0,
            battery_discharge_w=parsed.get("battery_discharge_power_w") or 0.0,
            ev_power_w=parsed.get("ev_actual_power_w") or 0.0,
            electricity_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
            duration_hours=duration_hours,
        )

    def _should_lookup(self, vehicle_id: int, *, is_charging: bool, last_resolution) -> bool:
        state = self._lookup_state.setdefault(vehicle_id, _VehicleLookupState())
        session_started = is_charging and not state.was_charging
        state.was_charging = is_charging

        if not is_charging:
            state.lookup_done_for_session = False
            state.uncertain_retry_done = False
            return False

        if session_started:
            state.lookup_done_for_session = False
            state.uncertain_retry_done = False
            return True

        if not state.lookup_done_for_session:
            return True

        if (
            not state.uncertain_retry_done
            and last_resolution is not None
            and getattr(last_resolution, "station_resolution_status", None)
            in {StationResolutionStatus.UNKNOWN, StationResolutionStatus.MULTIPLE_CANDIDATES}
        ):
            state.uncertain_retry_done = True
            return True

        return False

    async def _resolve_station_if_needed(
        self,
        db: AsyncSession,
        *,
        resolver: ChargingStationResolver,
        knowledge_base: ChargingLocationKnowledgeBase,
        station_repo: ChargingStationRepository,
        latest,
        correlation,
        vehicle_id: int,
    ):
        if latest is None or latest.latitude is None or latest.longitude is None:
            return None

        is_charging = bool(latest.is_charging)
        state = self._lookup_state.setdefault(vehicle_id, _VehicleLookupState())
        if not self._should_lookup(vehicle_id, is_charging=is_charging, last_resolution=state.last_resolution):
            return state.last_resolution

        halo = None
        if correlation is not None:
            halo = HaloCorrelationHint(
                status=getattr(correlation, "status", None),
                plugged_agreement=getattr(correlation, "plugged_agreement", None),
            )

        halo_active = True if latest.is_charging else None
        resolved = await resolver.resolve(
            latest.latitude,
            latest.longitude,
            knowledge_base=knowledge_base,
            halo=halo,
            vehicle_state=VehicleResolutionContext(
                mercedes_plugged=latest.is_plugged_in,
                mercedes_charging=latest.is_charging,
                mercedes_power_kw=latest.charging_power_kw,
                halo_charger_active=halo_active,
            ),
            vehicle_id=vehicle_id,
        )

        self._metrics.record_resolution(resolved.station_resolution_status.value)
        if resolved.selected_station is not None:
            record = await station_repo.upsert_from_candidate(resolved.selected_station)
            resolved = replace(resolved, charging_station_id=record.id)
            await station_repo.record_usage(record.id)

        if resolver.provider_enabled and resolved.source == "CHARGEFINDER":
            status_repo = ChargeFinderIntegrationStatusRepository(db)
            if resolved.station_resolution_status.value not in {"UNKNOWN"}:
                await status_repo.record_success(latency_ms=0, lookup_mode="WEB")

        state.lookup_done_for_session = True
        state.last_resolution = resolved
        await db.flush()
        return resolved
