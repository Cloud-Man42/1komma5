"""Isolated Charge Amps External API v5 HTTP client."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime
from typing import Any

import httpx

from energy_core.chargers.errors import ChargerApiError

logger = logging.getLogger(__name__)

CHARGEAMPS_API_BASE = "https://eapi.charge.space/api/v5"
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_CONNECTOR_ID = 1
MIN_STATUS_POLL_INTERVAL_SECONDS = 15.0
MIN_WRITE_INTERVAL_SECONDS = 5.0
MAX_RETRIES = 3

_SENSITIVE_PATTERNS = (
    re.compile(r"(api[_-]?key|authorization|password|token|email)", re.IGNORECASE),
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"(apiKey|api_key|token|password)\s*[=:]\s*\S+", re.IGNORECASE),
)


def sanitize_error_message(message: str) -> str:
    sanitized = message
    value_patterns = (
        re.compile(r"(apiKey|api_key|token|password)\s*[=:]\s*\S+", re.IGNORECASE),
        re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    )
    for pattern in value_patterns:
        sanitized = pattern.sub("[redacted]", sanitized)
    for pattern in _SENSITIVE_PATTERNS:
        sanitized = pattern.sub("[redacted]", sanitized)
    return sanitized


class ChargeAmpsClient:
    """HTTP client for Charge Amps External API v5."""

    def __init__(
        self,
        *,
        charger_id: str,
        api_key: str,
        email: str,
        password: str,
        connector_id: int = DEFAULT_CONNECTOR_ID,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.charger_id = charger_id
        self._connector_id = connector_id
        self._api_key = api_key
        self._email = email
        self._password = password
        self._timeout = timeout_seconds
        self._token: str | None = None
        self._status_cache: dict[str, Any] | None = None
        self._settings_cache: dict[str, Any] | None = None
        self._last_status_poll_at: datetime | None = None
        self._last_write_at: datetime | None = None

    async def get_chargepoint_status(self, *, force: bool = False) -> dict[str, Any]:
        if not force and self._status_cache is not None and self._last_status_poll_at is not None:
            age = (datetime.now(UTC) - self._last_status_poll_at).total_seconds()
            if age < MIN_STATUS_POLL_INTERVAL_SECONDS:
                return self._status_cache
        data = await self._request("GET", f"/chargepoints/{self.charger_id}/status")
        self._status_cache = data
        self._last_status_poll_at = datetime.now(UTC)
        return data

    async def get_connector_settings(self, *, force: bool = False) -> dict[str, Any]:
        if not force and self._settings_cache is not None and self._last_status_poll_at is not None:
            age = (datetime.now(UTC) - self._last_status_poll_at).total_seconds()
            if age < MIN_STATUS_POLL_INTERVAL_SECONDS:
                return self._settings_cache
        data = await self._request(
            "GET",
            f"/chargepoints/{self.charger_id}/connectors/{self._connector_id}/settings",
        )
        data.setdefault("chargePointId", self.charger_id)
        data.setdefault("connectorId", self._connector_id)
        self._settings_cache = data
        return data

    async def update_connector_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        await self._throttle_write()
        result = await self._request(
            "PUT",
            f"/chargepoints/{self.charger_id}/connectors/{self._connector_id}/settings",
            json_body=settings,
        )
        self._settings_cache = dict(settings)
        self._invalidate_status_cache()
        return result

    async def remote_stop(self) -> dict[str, Any]:
        await self._throttle_write()
        result = await self._request(
            "PUT",
            f"/chargepoints/{self.charger_id}/connectors/{self._connector_id}/remotestop",
            json_body={},
        )
        self._invalidate_status_cache()
        return result

    def invalidate_cache(self) -> None:
        self._invalidate_status_cache()
        self._settings_cache = None

    def _invalidate_status_cache(self) -> None:
        self._status_cache = None

    async def _throttle_write(self) -> None:
        if self._last_write_at is None:
            return
        elapsed = (datetime.now(UTC) - self._last_write_at).total_seconds()
        if elapsed < MIN_WRITE_INTERVAL_SECONDS:
            await asyncio.sleep(MIN_WRITE_INTERVAL_SECONDS - elapsed)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        last_error: ChargerApiError | None = None
        for attempt in range(MAX_RETRIES):
            try:
                token = await self._ensure_token()
                url = f"{CHARGEAMPS_API_BASE}{path}"
                headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.request(method, url, headers=headers, json=json_body)
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", "2"))
                    await asyncio.sleep(retry_after)
                    last_error = ChargerApiError("RATE_LIMITED", "Charge Amps rate limited", 429)
                    continue
                if response.status_code in {401, 403}:
                    self._token = None
                    raise ChargerApiError(
                        "AUTH_ERROR", "Charge Amps authentication failed", response.status_code
                    )
                if response.status_code >= 500:
                    last_error = ChargerApiError(
                        "CHARGER_OFFLINE",
                        "Charge Amps service unavailable",
                        response.status_code,
                    )
                    await asyncio.sleep(2**attempt)
                    continue
                response.raise_for_status()
                if method != "GET":
                    self._last_write_at = datetime.now(UTC)
                if response.status_code == 204 or not response.content:
                    return {}
                data = response.json()
                if not isinstance(data, dict):
                    raise ChargerApiError(
                        "INVALID_RESPONSE", "Unexpected Charge Amps response shape"
                    )
                return data
            except httpx.TimeoutException as exc:
                last_error = ChargerApiError("TIMEOUT", sanitize_error_message(str(exc)))
                await asyncio.sleep(2**attempt)
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status in {400, 409, 422}:
                    raise ChargerApiError(
                        "COMMAND_REJECTED",
                        sanitize_error_message(f"Charge Amps rejected command ({status})"),
                        status,
                    ) from exc
                last_error = ChargerApiError("UNKNOWN", sanitize_error_message(str(exc)), status)
                await asyncio.sleep(2**attempt)
            except ChargerApiError:
                raise
            except httpx.HTTPError as exc:
                last_error = ChargerApiError("UNKNOWN", sanitize_error_message(str(exc)))
                await asyncio.sleep(2**attempt)
        if last_error is not None:
            logger.warning(
                "chargeamps request failed method=%s path=%s code=%s",
                method,
                path,
                last_error.code,
            )
            raise last_error
        raise ChargerApiError("UNKNOWN", "Charge Amps request failed")

    async def _ensure_token(self) -> str:
        if self._token:
            return self._token
        if not self._api_key:
            raise ChargerApiError("AUTH_ERROR", "Charge Amps API key missing")
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{CHARGEAMPS_API_BASE}/auth/login",
                    headers={"apiKey": self._api_key, "Accept": "application/json"},
                    json={"email": self._email, "password": self._password},
                )
            if response.status_code in {401, 403}:
                raise ChargerApiError(
                    "AUTH_ERROR", "Charge Amps login failed", response.status_code
                )
            response.raise_for_status()
            data = response.json()
            token = data.get("token") if isinstance(data, dict) else None
            if not token:
                raise ChargerApiError("AUTH_ERROR", "Charge Amps login returned no token")
            self._token = str(token)
            return self._token
        except httpx.TimeoutException as exc:
            raise ChargerApiError("TIMEOUT", sanitize_error_message(str(exc))) from exc
        except ChargerApiError:
            raise
        except httpx.HTTPStatusError as exc:
            raise ChargerApiError(
                "AUTH_ERROR",
                sanitize_error_message("Charge Amps login failed"),
                exc.response.status_code,
            ) from exc
