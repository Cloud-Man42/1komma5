"""HTTP lookup client for ChargeFinder web API."""

from __future__ import annotations

import logging
import time
from typing import Any, Protocol

import httpx

from energy_core.integrations.charging_stations.chargefinder.circuit_breaker import ChargeFinderCircuitBreaker
from energy_core.integrations.charging_stations.chargefinder.crypto import decrypt_response, is_encrypted
from energy_core.integrations.charging_stations.chargefinder.key_extractor import extract_aes_key_hex
from energy_core.integrations.charging_stations.exceptions import (
    ChargeFinderBlockedError,
    ChargeFinderCaptchaError,
    ChargeFinderMalformedResponseError,
    ChargeFinderTimeoutError,
)
from energy_core.integrations.charging_stations.geohash import bounds_key

logger = logging.getLogger(__name__)

API_BASE = "https://api.chargefinder.com"
ALLOWED_HOSTS = frozenset({"api.chargefinder.com", "chargefinder.com"})


class IChargeFinderLookupClient(Protocol):
    async def search_near(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_m: int,
    ) -> tuple[list[dict[str, Any]], int, int | None]: ...


class ChargeFinderHttpLookupClient:
    def __init__(
        self,
        *,
        timeout_seconds: float = 15.0,
        circuit_breaker: ChargeFinderCircuitBreaker | None = None,
        cooldown_seconds: float = 900.0,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._circuit = circuit_breaker or ChargeFinderCircuitBreaker()
        self._cooldown_seconds = cooldown_seconds

    @property
    def circuit_breaker(self) -> ChargeFinderCircuitBreaker:
        return self._circuit

    async def search_near(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_m: int,
    ) -> tuple[list[dict[str, Any]], int, int | None]:
        if self._circuit.is_open():
            raise ChargeFinderBlockedError("ChargeFinder circuit breaker open")

        started = time.perf_counter()
        status_code: int | None = None
        try:
            geohash = bounds_key(latitude, longitude, float(radius_m))
            url = f"{API_BASE}/stations/{geohash}"
            headers = {
                "origin": "https://chargefinder.com",
                "referer": "https://chargefinder.com/",
                "accept": "application/json",
            }
            async with httpx.AsyncClient(timeout=self._timeout_seconds, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                status_code = response.status_code
                if response.status_code in {403, 429}:
                    self._circuit.record_http_block(
                        status_code=response.status_code,
                        cooldown_seconds=self._cooldown_seconds,
                    )
                    raise ChargeFinderBlockedError(f"ChargeFinder HTTP {response.status_code}")
                response.raise_for_status()
                body = response.json()
                if _looks_like_captcha(body):
                    self._circuit.record_captcha_detected(cooldown_seconds=self._cooldown_seconds)
                    raise ChargeFinderCaptchaError("ChargeFinder CAPTCHA/challenge detected")
                if is_encrypted(body):
                    key_hex = extract_aes_key_hex(timeout_seconds=self._timeout_seconds)
                    body = decrypt_response(key_hex.encode("ascii"), body)
                if not isinstance(body, list):
                    raise ChargeFinderMalformedResponseError("Expected station list")
                self._circuit.record_success()
                latency_ms = int((time.perf_counter() - started) * 1000)
                return body, latency_ms, status_code
        except httpx.TimeoutException as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            logger.warning(
                "provider=CHARGEFINDER lookup=timeout lat=%s lon=%s radius=%s response_ms=%s",
                latitude,
                longitude,
                radius_m,
                latency_ms,
            )
            raise ChargeFinderTimeoutError(str(exc)) from exc
        except (ChargeFinderBlockedError, ChargeFinderCaptchaError):
            latency_ms = int((time.perf_counter() - started) * 1000)
            raise
        except Exception as exc:
            self._circuit.record_parser_failure(max_failures=3, cooldown_seconds=self._cooldown_seconds)
            latency_ms = int((time.perf_counter() - started) * 1000)
            logger.warning(
                "provider=CHARGEFINDER lookup=failure lat=%s lon=%s radius=%s response_ms=%s error=%s",
                latitude,
                longitude,
                radius_m,
                latency_ms,
                exc,
            )
            if isinstance(exc, ChargeFinderMalformedResponseError):
                raise
            raise ChargeFinderMalformedResponseError(str(exc)) from exc


def _looks_like_captcha(body: Any) -> bool:
    if not isinstance(body, dict):
        return False
    text = str(body).lower()
    return any(token in text for token in ("captcha", "challenge", "cloudflare"))
