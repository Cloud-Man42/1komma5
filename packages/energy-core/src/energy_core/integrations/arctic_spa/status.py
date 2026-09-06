"""Arctic Spa status models exposed through the integration boundary."""

from __future__ import annotations

from energy_core.integrations.arctic_spa.models import ArcticSpaStatus, celsius_to_fahrenheit_int, fahrenheit_to_celsius

__all__ = [
    "ArcticSpaStatus",
    "SpaStatus",
    "celsius_to_fahrenheit_int",
    "fahrenheit_to_celsius",
]

SpaStatus = ArcticSpaStatus
