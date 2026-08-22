"""HTTP client for MyArcticSpa REST API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from energy_core.integrations.arctic_spa.config import mask_api_key
from energy_core.integrations.arctic_spa.models import ArcticSpaStatus

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10.0
MAX_RETRIES = 3


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
        return {"X-API-KEY": self._api_key, "Accept": "application/json"}

    async def get_status(self) -> ArcticSpaStatus:
        payload = await self._request("GET", "/v2/spa/status")
        if not isinstance(payload, dict):
            raise ArcticSpaApiError("Invalid status response")
        return ArcticSpaStatus.from_api(payload)

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
            except ArcticSpaApiError:
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
