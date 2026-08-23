from datetime import datetime
from typing import Protocol

from energy_core.domain import RawEnergyReading, SiteSnapshot


class HeartbeatProvider(Protocol):
    async def list_sites(self) -> list[SiteSnapshot]: ...

    async def fetch_readings(
        self, recorded_at: datetime | None = None
    ) -> list[RawEnergyReading]: ...
