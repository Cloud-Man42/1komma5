"""Charging Session Intelligence orchestrator."""



from __future__ import annotations



from dataclasses import dataclass

from datetime import UTC, datetime



from energy_core.chargers.meter_adapter import MeterSnapshot

from energy_core.db.models import EvChargerModel, SiteModel, VehicleModel, VehicleStateLatestModel

from energy_core.integrations.charging_stations.models import ResolvedChargingLocation, StationResolutionStatus

from energy_core.vehicles.charging_intelligence.classification import classify_charging_type

from energy_core.vehicles.charging_intelligence.correlation import ChargingCorrelationEngine, CorrelationSignals

from energy_core.vehicles.charging_intelligence.cost import resolve_session_cost

from energy_core.vehicles.charging_intelligence.energy import resolve_session_energy

from energy_core.vehicles.charging_intelligence.location import (

    ChargingLocationDefinition,

    ChargingLocationResolver,

    HaloCorrelationHint,

    IdentificationMethod,

    LocationClassification,

)

from energy_core.vehicles.charging_intelligence.state_machine import VehicleChargingStateMachine

from energy_core.vehicles.sessions.constants import estimate_battery_delta_kwh





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

    connector_type: str | None = None

    station_name: str | None = None

    station_provider: str | None = None

    station_provider_id: str | None = None

    distance_from_vehicle_m: float | None = None

    station_confidence: int | None = None

    station_resolution_status: str | None = None

    station_candidates_json: list[dict] | None = None

    charging_station_id: int | None = None

    price_model: str | None = None

    price_value_sek_kwh: float | None = None





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

        session_start_soc: float | None = None,

        halo: HaloCorrelationHint | None = None,

        halo_charger_active: bool | None = None,

        station_resolution: ResolvedChargingLocation | None = None,

    ) -> ChargingSessionContext:

        now = datetime.now(UTC)

        latitude = getattr(latest, "latitude", None) if latest else None

        longitude = getattr(latest, "longitude", None) if latest else None

        mercedes_power_kw = latest.charging_power_kw if latest else None

        location = self._location_resolver.resolve(

            latitude=latitude,

            longitude=longitude,

            halo=halo,

            mercedes_plugged=latest.is_plugged_in if latest else None,

            mercedes_charging=latest.is_charging if latest else None,

            mercedes_power_kw=mercedes_power_kw,

            halo_charger_active=halo_charger_active,

        )



        location_name = location.location_name

        charger_operator = location.charger_operator

        location_id = location.location.id if location.location else None

        home_charging = location.home_charging

        identification_method = location.identification_method

        detection_confidence = location.confidence_band

        location_expected_type = location.location.expected_charging_type if location.location else None

        price_model = location.location.price_model if location.location else None

        price_value = location.location.price_value if location.location else None

        connector_type = None

        station_name = None

        station_provider = None

        station_provider_id = None

        distance_from_vehicle_m = None

        station_confidence = None

        station_resolution_status = None

        station_candidates_json = None

        charging_station_id = None



        if station_resolution is not None:

            location_name = station_resolution.location_name or location_name

            charger_operator = station_resolution.operator_name or charger_operator

            try:
                identification_method = IdentificationMethod(station_resolution.identification_method)
            except ValueError:
                identification_method = IdentificationMethod.UNKNOWN

            detection_confidence = station_resolution.confidence_band

            connector_type = station_resolution.connector_type

            station_name = station_resolution.station_name

            distance_from_vehicle_m = station_resolution.distance_meters

            station_confidence = station_resolution.confidence

            station_resolution_status = station_resolution.station_resolution_status.value

            charging_station_id = station_resolution.charging_station_id

            if station_resolution.selected_station is not None:

                station_provider = station_resolution.selected_station.provider.value

                station_provider_id = station_resolution.selected_station.provider_station_id

            if station_resolution.price_model not in {None, "UNKNOWN"}:

                price_model = station_resolution.price_model

                price_value = station_resolution.price_value_sek_kwh

            if station_resolution.charging_type:

                location_expected_type = station_resolution.charging_type

            if station_resolution.candidates:

                station_candidates_json = [

                    {"score": c.score, "label": c.label, "provider_station_id": c.candidate.provider_station_id}

                    for c in station_resolution.candidates

                ]

            if location.location is not None:

                home_charging = location.location.classification in {

                    LocationClassification.HOME,

                    LocationClassification.HOME_SECONDARY,

                }

            elif station_resolution.station_resolution_status != StationResolutionStatus.UNKNOWN:

                home_charging = False



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

            location_expected_type=location_expected_type,

        )

        soc_delta = estimate_battery_delta_kwh(previous_soc, soc)

        session_energy_kwh = estimate_battery_delta_kwh(session_start_soc, soc)

        energy = resolve_session_energy(

            charger_meter_kwh=None,

            mercedes_energy_kwh=None,

            integrated_power_kwh=None,

            soc_estimate_kwh=session_energy_kwh if session_energy_kwh is not None else soc_delta,

        )

        price_from_chargefinder = bool(

            station_resolution is not None

            and station_resolution.price_model not in {None, "UNKNOWN"}

            and station_resolution.price_value_sek_kwh is not None

        )

        cost = resolve_session_cost(

            home_charging=home_charging,

            actual_cost_sek=None,

            price_model=price_model,

            price_value=price_value,

            energy_kwh=energy.energy_kwh,

            price_from_chargefinder=price_from_chargefinder,

        )

        sm = self.state_machine(vehicle.id)

        sm.apply(

            is_plugged_in=latest.is_plugged_in if latest else None,

            is_charging=latest.is_charging if latest else None,

            trigger="telemetry",

        )

        vehicle_data_quality = "STALE"

        if latest and latest.last_vehicle_update:

            age = (now - latest.last_vehicle_update).total_seconds()

            vehicle_data_quality = "LIVE" if age <= 120 else "STALE" if age <= 900 else "UNAVAILABLE"

        resolved_detection = (

            detection_confidence.value

            if isinstance(detection_confidence, type(location.confidence_band))

            and location.confidence_score > correlation.score

            else (

                detection_confidence

                if isinstance(detection_confidence, str)

                else detection_confidence.value

            )

        )

        if isinstance(detection_confidence, str):

            if correlation.score > (station_confidence or location.confidence_score):

                resolved_detection = correlation.confidence_band.value

        resolved_method = (

            identification_method.value

            if identification_method != IdentificationMethod.UNKNOWN

            else correlation.identification_method

        )

        return ChargingSessionContext(

            location_id=location_id,

            location_name=location_name,

            charger_operator=charger_operator,

            charging_type=charging_type.value,

            detection_confidence=resolved_detection,

            identification_method=resolved_method,

            home_charging=home_charging,

            energy_source=energy.energy_source.value,

            estimated_energy_kwh=energy.estimated_energy_kwh,

            charging_cost_sek=cost.cost_sek,

            cost_source=cost.cost_source.value,

            price_model=price_model,

            price_value_sek_kwh=price_value if price_model in {"PER_KWH", "FREE"} else None,

            charging_state=sm.state.value,

            vehicle_data_quality=vehicle_data_quality,

            connector_type=connector_type,

            station_name=station_name,

            station_provider=station_provider,

            station_provider_id=station_provider_id,

            distance_from_vehicle_m=distance_from_vehicle_m,

            station_confidence=station_confidence,

            station_resolution_status=station_resolution_status,

            station_candidates_json=station_candidates_json,

            charging_station_id=charging_station_id,

        )

