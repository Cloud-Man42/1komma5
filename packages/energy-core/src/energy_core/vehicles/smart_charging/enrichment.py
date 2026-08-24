"""Apply vehicle context to EnergyState and ChargingConfig."""

from __future__ import annotations

from dataclasses import replace

from energy_core.charging.config import ChargingConfig
from energy_core.db.models import EvChargerModel
from energy_core.energy.state import EnergyState
from energy_core.vehicles.smart_charging.models import VehicleChargingContext


def apply_vehicle_charging_context(
    charger: EvChargerModel,
    energy: EnergyState,
    config: ChargingConfig,
    context: VehicleChargingContext | None,
) -> tuple[EnergyState, ChargingConfig]:
    if context is None or not context.active:
        return energy, config

    target_soc = context.target_soc_fraction
    if target_soc is None and charger.target_soc_pct is not None:
        target_soc = charger.target_soc_pct / 100.0
    elif target_soc is None:
        target_soc = energy.target_soc

    departure_time = context.departure_time or charger.departure_time or energy.departure_time
    deadline_at = context.deadline_at or charger.deadline_at or energy.deadline_at

    ev_soc = None
    if context.requirement.current_soc_percent is not None:
        ev_soc = context.requirement.current_soc_percent / 100.0

    enriched_energy = replace(
        energy,
        target_soc=target_soc,
        departure_time=departure_time,
        deadline_at=deadline_at,
        ev_soc=ev_soc,
        vehicle_required_energy_kwh=context.requirement.required_energy_kwh,
        vehicle_energy_quality=context.requirement.quality,
        vehicle_linked=True,
        vehicle_display_name=context.display_name,
    )
    enriched_config = replace(
        config,
        departure_time=departure_time,
        deadline_at=deadline_at,
    )
    return enriched_energy, enriched_config
