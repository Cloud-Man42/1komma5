"""Charging Session Intelligence orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from energy_core.chargers.meter_adapter import MeterSnapshot
from energy_core.db.models import EvChargerModel, SiteModel, VehicleModel, VehicleStateLatestModel
from energy_core.vehicles.charging_intelligence.classification import classify_charging_type
from energy_core.vehicles.charging_intelligence.correlation import ChargingCorrelationEngine, CorrelationSignals
from energy_core.vehicles.charging_intelligence.cost import resolve_session_cost
from energy_core.vehicles.charging_intelligence.energy import resolve_session_energy
from energy_core.vehicles.charging_intelligence.location import (
    ChargingLocationDefinition,
    ChargingLocationResolver,
)
from energy_core.vehicles.charging_intelligence.state_machine import VehicleChargingStateMachine
from energy_core.vehicles.sessions.constants import SOC_TO_KWH_FACTOR, estimate_battery_delta_kwh


@dataclass(frozen=True, slots=True)
class ChargingSessionContext:
    location_id: int | None
    location_name: str | None
    charger_operator: str | None
    charging_type: str
    detection_confidence: str
    identification_method: str
    home_charging: bool | None
    energy_source: str
    estimated_energy_kwh: float | None
    charging_cost_sek: float | None
    cost_source: str
    charging_state: str
    vehicle_data_quality: str


class ChargingSessionService:
    def __init__(self, locations: list[ChargingLocationDefinition] | None = None) -> None:
        self._location_resolver = ChargingLocationResolver(locations or [])
        self._correlation = ChargingCorrelationEngine()
        self._state_machines: dict[int, VehicleChargingStateMachine] = {}

    def set_locations(self, locations: list[ChargingLocationDefinition]) -> None:
        self._location_resolver = ChargingLocationResolver(locations)

    def state_machine(self, vehicle_id: int) -> VehicleChargingStateMachine:
        return self._state_machines.setdefault(vehicle_id, VehicleChargingStateMachine())

    def build_context(
        self,
        *,
        vehicle: VehicleModel,
        site: SiteModel,
        latest: VehicleStateLatestModel | None,
        charger: EvChargerModel | None,
        meter: MeterSnapshot | None,
        previous_soc: float | None,
    ) -> ChargingSessionContext:
        now = datetime.now(UTC)
        latitude = getattr(latest, "latitude", None) if latest else None
        longitude = getattr(latest, "longitude", None) if latest else None
        location = self._location_resolver.resolve(latitude=latitude, longitude=longitude)
        soc = latest.state_of_charge_percent if latest else None
        soc_increasing = soc is not None and previous_soc is not None and soc > previous_soc
        correlation = self._correlation.score(
            CorrelationSignals(
                geofence_match=location.location is not None,
                charger_active=bool(meter and (meter.is_charging or meter.vehicle_connected)),
                mercedes_charging=bool(latest and latest.is_charging),
                soc_increasing=soc_increasing,
                house_load_matches=False,
                timestamps_match=True,
            ),
            location=location,
        )
        charging_type = classify_charging_type(
            charger_type_hint=getattr(charger, "display_name", None) or getattr(charger, "model", None),
            charging_power_kw=latest.charging_power_kw if latest else None,
            location_expected_type=location.location.expected_charging_type if location.location else None,
        )
        soc_delta = estimate_battery_delta_kwh(previous_soc, soc)
        energy = resolve_session_energy(
            charger_meter_kwh=None,
            mercedes_energy_kwh=None,
            integrated_power_kwh=None,
            soc_estimate_kwh=soc_delta,
        )
        cost = resolve_session_cost(
            home_charging=location.home_charging,
            actual_cost_sek=None,
            price_model=location.location.price_model if location.location else None,
            price_value=location.location.price_value if location.location else None,
            energy_kwh=energy.energy_kwh,
        )
        sm = self.state_machine(vehicle.id)
        transition = sm.apply(
            is_plugged_in=latest.is_plugged_in if latest else None,
            is_charging=latest.is_charging if latest else None,
            trigger="telemetry",
        )
        vehicle_data_quality = "STALE"
        if latest and latest.last_vehicle_update:
            age = (now - latest.last_vehicle_update).total_seconds()
            vehicle_data_quality = "LIVE" if age <= 120 else "STALE" if age <= 900 else "UNAVAILABLE"
        return ChargingSessionContext(
            location_id=location.location.id if location.location else None,
            location_name=location.location_name,
            charger_operator=location.charger_operator,
            charging_type=charging_type.value,
            detection_confidence=correlation.confidence_band.value,
            identification_method=correlation.identification_method,
            home_charging=location.home_charging,
            energy_source=energy.energy_source.value,
            estimated_energy_kwh=energy.estimated_energy_kwh,
            charging_cost_sek=cost.cost_sek,
            cost_source=cost.cost_source.value,
            charging_state=sm.state.value,
            vehicle_data_quality=vehicle_data_quality,
        )
