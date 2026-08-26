"""Arctic Spa control service implementation."""

from __future__ import annotations

import logging

from energy_core.integrations.arctic_spa.client import ArcticSpaApiError, ArcticSpaClient
from energy_core.integrations.arctic_spa.config import ArcticSpaConfiguration
from energy_core.integrations.arctic_spa.models import ArcticSpaStatus, celsius_to_fahrenheit_int

logger = logging.getLogger(__name__)


class ArcticSpaControlService:
    """Write-capable spa control backed by MyArcticSpa REST API."""

    def __init__(self, config: ArcticSpaConfiguration) -> None:
        self._config = config
        self._client: ArcticSpaClient | None = None
        if config.api_key:
            self._client = ArcticSpaClient(
                base_url=config.api_base_url,
                api_key=config.api_key,
            )

    def _require_client(self) -> ArcticSpaClient:
        if self._client is None:
            raise ArcticSpaApiError("API key not configured")
        return self._client

    async def get_status(self) -> ArcticSpaStatus:
        return await self._require_client().get_status()

    async def set_target_temperature_c(self, temperature_c: float) -> None:
        setpoint_f = celsius_to_fahrenheit_int(temperature_c)
        await self._require_client().set_temperature_f(setpoint_f)
        logger.info("Spa setpoint set to %s F (from %.1f C)", setpoint_f, temperature_c)

    async def set_pump_state(self, pump: int, state: str) -> None:
        await self._require_client().set_pump(pump, state)

    async def start_filtering(self) -> None:
        await self._require_client().set_filter(state="on")

    async def stop_filtering(self) -> None:
        await self._require_client().set_filter(state="off")

    async def ensure_safety_floor(
        self,
        *,
        frequency_per_day: float,
        duration_hours: float,
    ) -> None:
        """Never lower spa internal schedule below configured safety floor."""
        await self._require_client().set_filter(
            frequency=max(1, int(round(frequency_per_day))),
            duration=max(1, int(round(duration_hours))),
        )
