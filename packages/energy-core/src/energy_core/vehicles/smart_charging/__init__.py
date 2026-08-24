"""Vehicle-aware inputs for SmartLaddning."""

from energy_core.vehicles.smart_charging.enrichment import apply_vehicle_charging_context
from energy_core.vehicles.smart_charging.models import VehicleChargingContext, VehicleEnergyRequirement
from energy_core.vehicles.smart_charging.requirement import compute_energy_requirement
from energy_core.vehicles.smart_charging.resolver import resolve_vehicle_charging_context

__all__ = [
    "VehicleChargingContext",
    "VehicleEnergyRequirement",
    "apply_vehicle_charging_context",
    "compute_energy_requirement",
    "resolve_vehicle_charging_context",
]
