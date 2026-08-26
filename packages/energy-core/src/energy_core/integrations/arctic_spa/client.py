"""HTTP client for MyArcticSpa REST API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from energy_core.integrations.arctic_spa.config import mask_api_key
from energy_core.integrations.arctic_spa.models import ArcticSpaStatus, celsius_to_fahrenheit_int

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10.0
MAX_RETRIES = 3
RETRYABLE_STATUS = frozenset({429, 503})


class ArcticSpaApiError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ArcticSpaClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"X-API-KEY": self._api_key, "Accept": "application/json", "Content-Type": "application/json"}

    async def get_status(self) -> ArcticSpaStatus:
        payload = await self._request("GET", "/v2/spa/status")
        if not isinstance(payload, dict):
            raise ArcticSpaApiError("Invalid status response")
        return ArcticSpaStatus.from_api(payload)

    async def set_filter(
        self,
        *,
        state: str | None = None,
        frequency: int | None = None,
        duration: int | None = None,
        suspension: bool | None = None,
    ) -> None:
        body: dict[str, Any] = {}
        if state is not None:
            body["state"] = state
        if frequency is not None:
            body["frequency"] = frequency
        if duration is not None:
            body["duration"] = duration
        if suspension is not None:
            body["suspension"] = suspension
        if not body:
            raise ArcticSpaApiError("set_filter requires at least one parameter")
        await self._request("PUT", "/v2/spa/filter", json_body=body)

    async def set_temperature_f(self, setpoint_f: int) -> None:
        await self._request("PUT", "/v2/spa/temperature", json_body={"setpointF": setpoint_f})

    async def set_temperature_c(self, temperature_c: float) -> None:
        await self.set_temperature_f(celsius_to_fahrenheit_int(temperature_c))

    async def set_pump(self, pump: int | str, state: str) -> None:
        pump_id = str(pump)
        await self._request("PUT", f"/v2/spa/pumps/{pump_id}", json_body={"state": state})

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        retries: int = MAX_RETRIES,
    ) -> Any:
        url = f"{self._base_url}{path}"
        last_exc: Exception | None = None
        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.request(
                        method,
                        url,
                        headers=self._headers(),
                        json=json_body,
                    )
                if response.status_code in RETRYABLE_STATUS and attempt < retries - 1:
                    delay = min(30.0, 2.0 ** attempt)
                    logger.warning(
                        "Arctic Spa retryable status=%s attempt=%s delay=%s key=%s",
                        response.status_code,
                        attempt + 1,
                        delay,
                        mask_api_key(self._api_key),
                    )
                    await asyncio.sleep(delay)
                    continue
                if response.status_code == 429:
                    limit = response.headers.get("x-ratelimit-limit", "?")
                    raise ArcticSpaApiError(f"Rate limited (limit/min={limit})", status_code=429)
                if response.status_code == 401:
                    raise ArcticSpaApiError("Unauthorized — check API key", status_code=401)
                if response.status_code >= 500:
                    raise ArcticSpaApiError(f"Server error {response.status_code}", status_code=response.status_code)
                if response.status_code >= 400:
                    raise ArcticSpaApiError(
                        f"Request failed {response.status_code}: {response.text[:200]}",
                        status_code=response.status_code,
                    )
                if response.status_code == 204 or not response.content:
                    return {}
                return response.json()
            except ArcticSpaApiError as exc:
                if exc.status_code in RETRYABLE_STATUS and attempt < retries - 1:
                    await asyncio.sleep(min(30.0, 2.0 ** attempt))
                    continue
                raise
            except httpx.TimeoutException as exc:
                last_exc = exc
                logger.warning(
                    "Arctic Spa timeout attempt=%s key=%s",
                    attempt + 1,
                    mask_api_key(self._api_key),
                )
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "Arctic Spa request error attempt=%s key=%s err=%s",
                    attempt + 1,
                    mask_api_key(self._api_key),
                    type(exc).__name__,
                )
        raise ArcticSpaApiError(f"Request failed after retries: {last_exc}")
