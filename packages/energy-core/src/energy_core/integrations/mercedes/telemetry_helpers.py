"""Mercedes telemetry helpers exposed through the integration boundary."""

from __future__ import annotations

from energy_core.vehicles.mercedes.soc_estimation import apply_range_based_soc_correction
from energy_core.vehicles.mercedes.telemetry_plausibility import (
    has_plausible_vehicle_telemetry,
    sanitize_vehicle_state,
)

__all__ = [
    "apply_range_based_soc_correction",
    "has_plausible_vehicle_telemetry",
    "sanitize_vehicle_state",
]
