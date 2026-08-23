"""Real Heartbeat provider — uses stored connection settings and live-overview API."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx

from energy_core.domain import RawEnergyReading, SiteSnapshot
from energy_core.heartbeat.readings import live_overview_to_raw_reading
from energy_core.heartbeat_client import HeartbeatClient, HeartbeatCredentials
from energy_core.heartbeat_connection import HeartbeatConnectionType

logger = logging.getLogger(__name__)


TokenRefreshCallback = Callable[[], Awaitable[str]]


@dataclass(frozen=True, slots=True)
class SiteRuntimeInfo:
    name: str

    timezone: str


@dataclass(frozen=True, slots=True)
class HeartbeatRuntimeConfig:
    connection_type: str

    api_url: str | None

    username: str

    password: str

    api_token: str

    site_system_ids: dict[str, str]

    site_info: dict[str, SiteRuntimeInfo] = field(default_factory=dict)

    refresh_token: TokenRefreshCallback | None = None


class OneKommaFiveHeartbeatProvider:
    """HeartBeat provider using configured API URL and credentials."""

    def __init__(self, runtime: HeartbeatRuntimeConfig) -> None:

        self._runtime = runtime

    def _build_client(self) -> HeartbeatClient | None:

        if not self._runtime.api_url:
            return None

        return HeartbeatClient(
            HeartbeatCredentials(
                api_url=self._runtime.api_url,
                api_token=self._runtime.api_token,
                username=self._runtime.username,
                password=self._runtime.password,
            ),
            refresh_token=self._runtime.refresh_token,
        )

    async def list_sites(self) -> list[SiteSnapshot]:

        snapshots: list[SiteSnapshot] = []

        for slug, system_id in self._runtime.site_system_ids.items():
            info = self._runtime.site_info.get(slug)

            snapshots.append(
                SiteSnapshot(
                    slug=slug,
                    name=info.name if info else slug,
                    timezone=info.timezone if info else "UTC",
                    external_system_id=system_id,
                )
            )

        return snapshots

    async def fetch_readings(self, recorded_at: datetime | None = None) -> list[RawEnergyReading]:

        if self._runtime.connection_type == HeartbeatConnectionType.MOCK.value:
            return []

        if not self._runtime.api_url:
            logger.warning("HeartBeat API URL is not configured")

            return []

        if not self._runtime.site_system_ids:
            logger.warning("No HeartBeat system IDs configured for sites")

            return []

        if not self._runtime.api_token and not (self._runtime.username and self._runtime.password):
            logger.warning("HeartBeat credentials missing (token or username/password)")

            return []

        client = self._build_client()

        if client is None:
            return []

        readings: list[RawEnergyReading] = []

        for site_slug, system_id in self._runtime.site_system_ids.items():
            try:
                overview = await client.fetch_live_overview(system_id)

            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "HeartBeat live-overview failed for %s (%s): HTTP %s",
                    site_slug,
                    system_id,
                    exc.response.status_code,
                )

                continue

            except httpx.HTTPError as exc:
                logger.warning(
                    "HeartBeat live-overview request failed for %s (%s): %s",
                    site_slug,
                    system_id,
                    exc,
                )

                continue

            if not overview:
                logger.warning("HeartBeat live-overview returned empty payload for %s", site_slug)

                continue

            reading = live_overview_to_raw_reading(site_slug, overview)

            if recorded_at is not None:
                ts = recorded_at

                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=UTC)

                reading = RawEnergyReading(
                    site_slug=reading.site_slug,
                    recorded_at=ts,
                    solar_production_w=reading.solar_production_w,
                    consumption_w=reading.consumption_w,
                    grid_import_w=reading.grid_import_w,
                    grid_export_w=reading.grid_export_w,
                    battery_soc_pct=reading.battery_soc_pct,
                    battery_power_w=reading.battery_power_w,
                )

            readings.append(reading)

            logger.debug(
                "HeartBeat reading for %s: pv=%.0fW consumption=%.0fW battery=%.0f%%",
                site_slug,
                reading.solar_production_w,
                reading.consumption_w,
                reading.battery_soc_pct,
            )

        return readings
