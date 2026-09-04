"""ChargeFinder charging station provider."""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Callable

from dataclasses import replace

from energy_core.integrations.charging_stations.chargefinder.circuit_breaker import ChargeFinderCircuitBreaker
from energy_core.integrations.charging_stations.chargefinder.http_client import ChargeFinderHttpLookupClient
from energy_core.integrations.charging_stations.chargefinder.parser import (
    _parse_pricing_from_status,
    parse_station,
    parse_stations,
)
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

    async def _enrich_missing_pricing(
        self,
        candidates: list[ChargingStationCandidate],
        *,
        vehicle_lat: float,
        vehicle_lon: float,
        max_enrich: int = 3,
    ) -> list[ChargingStationCandidate]:
        if self._mode not in {ChargeFinderMode.WEB, ChargeFinderMode.API}:
            return candidates
        enriched: list[ChargingStationCandidate] = []
        detail_fetches = 0
        for candidate in candidates:
            if candidate.price_model not in {None, "UNKNOWN", "FREE"} or detail_fetches >= max_enrich:
                enriched.append(candidate)
                continue
            try:
                raw, _latency_ms, _status = await self._lookup_client.fetch_station(
                    slug=candidate.provider_station_id,
                )
            except ChargeFinderProviderError:
                enriched.append(candidate)
                continue
            except Exception:
                enriched.append(candidate)
                continue
            if raw is None:
                enriched.append(candidate)
                continue
            detail_fetches += 1
            reparsed = parse_station(raw, vehicle_lat=vehicle_lat, vehicle_lon=vehicle_lon)
            price_model = reparsed.price_model if reparsed else candidate.price_model
            price_value = reparsed.price_value_sek_kwh if reparsed else candidate.price_value_sek_kwh
            connector_type = reparsed.connector_type if reparsed else candidate.connector_type
            max_power_kw = reparsed.max_power_kw if reparsed else candidate.max_power_kw
            charging_type = reparsed.charging_type if reparsed else candidate.charging_type

            if price_model in {None, "UNKNOWN", "FREE"}:
                price_model, price_value = await self._pricing_from_status(
                    raw,
                    fallback_model=price_model,
                    fallback_value=price_value,
                )

            if price_model not in {None, "UNKNOWN"}:
                enriched.append(
                    replace(
                        candidate,
                        connector_type=connector_type or candidate.connector_type,
                        max_power_kw=max_power_kw or candidate.max_power_kw,
                        charging_type=charging_type or candidate.charging_type,
                        price_model=price_model,
                        price_value_sek_kwh=price_value,
                    )
                )
            else:
                enriched.append(candidate)
        return enriched

    async def _pricing_from_status(
        self,
        raw: dict,
        *,
        fallback_model: str | None,
        fallback_value: float | None,
    ) -> tuple[str, float | None]:
        realtime_id = raw.get("realtimeId")
        if not realtime_id:
            return fallback_model or "UNKNOWN", fallback_value
        try:
            status_items, _latency_ms, _status = await self._lookup_client.fetch_status(
                realtime_id=str(realtime_id),
            )
        except ChargeFinderProviderError:
            return fallback_model or "UNKNOWN", fallback_value
        except Exception:
            return fallback_model or "UNKNOWN", fallback_value
        status_model, status_value = _parse_pricing_from_status(status_items)
        if status_model != "UNKNOWN":
            return status_model, status_value
        return fallback_model or "UNKNOWN", fallback_value

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
            candidates = await self._enrich_missing_pricing(
                candidates,
                vehicle_lat=latitude,
                vehicle_lon=longitude,
            )
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
