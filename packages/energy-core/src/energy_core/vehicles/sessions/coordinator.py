"""Orchestrate vehicle charge sessions in the collector loop."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.chargers.meter_adapter import ChargeAmpsMeterAdapter
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.models import SiteModel
from energy_core.db.repositories import MarketPriceRepository
from energy_core.db.vehicle_repo import VehicleProviderRepository, VehicleRepository
from energy_core.ev_accounting.models import SiteEnergySample
from energy_core.heartbeat.live_overview import parse_live_overview
from energy_core.vehicles.correlation.repo import VehicleHaloCorrelationRepository
from energy_core.vehicles.sessions.sampler import VehicleChargeSessionSampler
from energy_core.vehicles.sessions.session_service import VehicleChargeSessionService

logger = logging.getLogger(__name__)


class VehicleChargeSessionCoordinator:
    def __init__(self) -> None:
        self._session_service = VehicleChargeSessionService()
        self._sampler = VehicleChargeSessionSampler(self._session_service)

    @property
    def session_service(self) -> VehicleChargeSessionService:
        return self._session_service

    async def setup(self, session: AsyncSession) -> None:
        await self._session_service.resume_active_sessions(session)

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

        vehicle_repo = VehicleRepository(db, is_sqlite=is_sqlite)
        correlation_repo = VehicleHaloCorrelationRepository(db)
        charger_repo = EvChargerRepository(db)
        vehicles = await vehicle_repo.list_for_site(site.id)
        if not vehicles:
            return 0

        energy_sample = self._energy_sample_from_overview(live_overview, site, db, is_sqlite)
        processed = 0
        for vehicle_record in vehicles:
            vehicle = await vehicle_repo.get(vehicle_record.id)
            if vehicle is None:
                continue
            charger = await correlation_repo.resolve_charger(vehicle)
            if charger is None or not charger.chargeamp_charger_id:
                continue
            latest = await vehicle_repo.get_latest_state(vehicle.id)
            correlation = await correlation_repo.get(vehicle.id)
            identification_confidence = correlation.confidence if correlation else None
            try:
                processed += await self._process_vehicle(
                    db,
                    vehicle=vehicle,
                    charger=charger,
                    site=site,
                    latest=latest,
                    energy_sample=energy_sample,
                    identification_confidence=identification_confidence,
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
        energy_sample: SiteEnergySample,
        identification_confidence: float | None,
        is_sqlite: bool,
    ) -> int:
        api_key = charger.chargeamps_api_key or os.getenv("CHARGEAMPS_API_KEY", "")
        meter_adapter = ChargeAmpsMeterAdapter.build(
            charger.chargeamp_charger_id,
            api_key=api_key,
            phases=charger.phases,
            nominal_voltage_v=charger.nominal_voltage_v,
        )
        meter = await meter_adapter.get_snapshot()
        is_charging = bool(latest and latest.is_charging)
        await self._session_service.process_vehicle(
            db,
            vehicle=vehicle,
            charger=charger,
            site=site,
            latest=latest,
            meter=meter,
            identification_confidence=identification_confidence,
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

    def _energy_sample_from_overview(
        self,
        live_overview: dict | None,
        site: SiteModel,
        db: AsyncSession,
        is_sqlite: bool,
    ) -> SiteEnergySample:
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
