"""ChargeFinder charging station provider."""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Callable

from energy_core.integrations.charging_stations.chargefinder.circuit_breaker import ChargeFinderCircuitBreaker
from energy_core.integrations.charging_stations.chargefinder.http_client import ChargeFinderHttpLookupClient
from energy_core.integrations.charging_stations.chargefinder.parser import parse_stations
from energy_core.integrations.charging_stations.exceptions import (
    ChargeFinderBlockedError,
    ChargeFinderProviderError,
)
from energy_core.integrations.charging_stations.models import ChargingStationCandidate

logger = logging.getLogger(__name__)


class ChargeFinderMode(StrEnum):
    API = "API"
    WEB = "WEB"
    BROWSER = "BROWSER"
    MANUAL = "MANUAL"
    DISABLED = "DISABLED"


class ChargeFinderChargingStationProvider:
    def __init__(
        self,
        *,
        mode: ChargeFinderMode,
        lookup_client: ChargeFinderHttpLookupClient | None = None,
        on_lookup_complete: Callable[[bool, int, str | None, str], None] | None = None,
    ) -> None:
        self._mode = mode
        self._lookup_client = lookup_client or ChargeFinderHttpLookupClient()
        self._on_lookup_complete = on_lookup_complete

    @property
    def enabled(self) -> bool:
        return self._mode not in {ChargeFinderMode.DISABLED, ChargeFinderMode.MANUAL}

    @property
    def mode(self) -> ChargeFinderMode:
        return self._mode

    @property
    def circuit_breaker(self) -> ChargeFinderCircuitBreaker:
        return self._lookup_client.circuit_breaker

    @classmethod
    def from_settings(cls, settings, on_lookup_complete=None) -> ChargeFinderChargingStationProvider:
        mode_raw = getattr(settings, "chargefinder_mode", ChargeFinderMode.WEB.value)
        try:
            mode = ChargeFinderMode(str(mode_raw).upper())
        except ValueError:
            mode = ChargeFinderMode.WEB
        if not getattr(settings, "chargefinder_enabled", True):
            mode = ChargeFinderMode.DISABLED
        client = ChargeFinderHttpLookupClient(
            timeout_seconds=getattr(settings, "chargefinder_timeout_seconds", 15.0),
            cooldown_seconds=getattr(settings, "chargefinder_cooldown_seconds", 900.0),
        )
        return cls(mode=mode, lookup_client=client, on_lookup_complete=on_lookup_complete)

    @classmethod
    def disabled(cls) -> ChargeFinderChargingStationProvider:
        return cls(mode=ChargeFinderMode.DISABLED)

    async def find_stations(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_m: int,
        limit: int = 10,
    ) -> list[ChargingStationCandidate]:
        if not self.enabled:
            return []
        if self._mode == ChargeFinderMode.MANUAL:
            return []

        success = False
        error: str | None = None
        latency_ms = 0
        lookup_mode = self._mode.value
        try:
            if self._mode in {ChargeFinderMode.WEB, ChargeFinderMode.API}:
                raw, latency_ms, _status = await self._lookup_client.search_near(
                    latitude=latitude,
                    longitude=longitude,
                    radius_m=radius_m,
                )
            else:
                return []

            candidates = parse_stations(
                raw,
                vehicle_lat=latitude,
                vehicle_lon=longitude,
                radius_m=float(radius_m),
            )[:limit]
            success = True
            logger.info(
                "provider=CHARGEFINDER lookup_mode=%s lat=%s lon=%s radius=%s candidate_count=%s response_ms=%s",
                lookup_mode,
                latitude,
                longitude,
                radius_m,
                len(candidates),
                latency_ms,
            )
            return candidates
        except ChargeFinderBlockedError as exc:
            error = str(exc)
            logger.warning("provider=CHARGEFINDER blocked lat=%s lon=%s error=%s", latitude, longitude, error)
            return []
        except ChargeFinderProviderError as exc:
            error = str(exc)
            logger.warning("provider=CHARGEFINDER failure lat=%s lon=%s error=%s", latitude, longitude, error)
            return []
        except Exception as exc:
            error = str(exc)
            logger.warning("provider=CHARGEFINDER unexpected failure lat=%s lon=%s error=%s", latitude, longitude, error)
            return []
        finally:
            if self._on_lookup_complete is not None:
                self._on_lookup_complete(success, latency_ms, error, lookup_mode)
