"""Arctic Spa service layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from energy_core.integrations.arctic_spa.client import ArcticSpaApiError, ArcticSpaClient
from energy_core.integrations.arctic_spa.config import ArcticSpaConfiguration, mask_api_key
from energy_core.integrations.arctic_spa.models import ArcticSpaStatus


@dataclass(frozen=True, slots=True)
class SpaConnectionTestResult:
    success: bool
    spa_found: bool
    spa_online: bool
    message: str
    last_update: datetime | None = None
    masked_api_key: str = ""


class ArcticSpaService:
    def __init__(self, config: ArcticSpaConfiguration) -> None:
        self._config = config

    def build_client(self) -> ArcticSpaClient | None:
        if not self._config.api_key:
            return None
        return ArcticSpaClient(
            base_url=self._config.api_base_url,
            api_key=self._config.api_key,
        )

    async def fetch_status(self) -> ArcticSpaStatus:
        client = self.build_client()
        if client is None:
            raise ArcticSpaApiError("API key not configured")
        return await client.get_status()

    async def test_connection(self) -> SpaConnectionTestResult:
        masked = mask_api_key(self._config.api_key)
        if not self._config.api_key:
            return SpaConnectionTestResult(
                success=False,
                spa_found=False,
                spa_online=False,
                message="API-nyckel saknas",
                masked_api_key=masked,
            )
        try:
            status = await self.fetch_status()
            now = datetime.now(UTC)
            return SpaConnectionTestResult(
                success=True,
                spa_found=True,
                spa_online=status.connected,
                message="Anslutning lyckades" if status.connected else "Spa hittades men är offline",
                last_update=now,
                masked_api_key=masked,
            )
        except ArcticSpaApiError as exc:
            return SpaConnectionTestResult(
                success=False,
                spa_found=False,
                spa_online=False,
                message=str(exc),
                masked_api_key=masked,
            )
