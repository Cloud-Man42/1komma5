"""Arctic Spa error surface."""

from __future__ import annotations

from energy_core.integrations.arctic_spa.client import ArcticSpaApiError

__all__ = ["ArcticSpaApiError", "SpaControlError"]

SpaControlError = ArcticSpaApiError
