"""Arctic Spa integration factory."""

from __future__ import annotations

from energy_core.integrations.arctic_spa.config import ArcticSpaConfiguration, SpaPowerProfiles, mask_api_key
from energy_core.integrations.arctic_spa.control_service import ArcticSpaControlService
from energy_core.integrations.arctic_spa.polling import ArcticSpaPollingService
from energy_core.integrations.arctic_spa.service import ArcticSpaService


def build_arctic_spa_control_service(config: ArcticSpaConfiguration) -> ArcticSpaControlService:
    return ArcticSpaControlService(config)


def build_arctic_spa_service(config: ArcticSpaConfiguration) -> ArcticSpaService:
    return ArcticSpaService(config)


def build_arctic_spa_polling_service() -> ArcticSpaPollingService:
    return ArcticSpaPollingService()


__all__ = [
    "ArcticSpaConfiguration",
    "SpaPowerProfiles",
    "build_arctic_spa_control_service",
    "build_arctic_spa_polling_service",
    "build_arctic_spa_service",
    "mask_api_key",
]
