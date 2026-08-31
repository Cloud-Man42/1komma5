"""Central Mercedes REST client with retries, classification and metrics."""

from __future__ import annotations

import logging
import time
from typing import Any, Awaitable, Callable

import httpx

from energy_core.vehicles.mercedes.api_events import MercedesApiEventBuffer
from energy_core.vehicles.mercedes.auth.token_store import MercedesTokenStore
from energy_core.vehicles.mercedes.errors import MercedesApiError, MercedesErrorCode, classify_exception, classify_http_status
from energy_core.vehicles.mercedes.transport.backoff import MercedesBackoffPolicy

logger = logging.getLogger(__name__)

MAX_RETRIES = 5


class MercedesApiClient:
    """Wraps Mercedes REST calls with token refresh, retries and event recording."""

    def __init__(
        self,
        *,
        token_store: MercedesTokenStore,
        request_headers: Callable[[], dict[str, str]],
        base_url: str,
        timeout: float = 30.0,
        event_buffer: MercedesApiEventBuffer | None = None,
        on_success: Callable[[], Awaitable[None]] | None = None,
        on_failure: Callable[[MercedesApiError], Awaitable[None]] | None = None,
    ) -> None:
        self._token_store = token_store
        self._request_headers = request_headers
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._events = event_buffer or MercedesApiEventBuffer()
        self._backoff = MercedesBackoffPolicy()
        self._on_success = on_success
        self._on_failure = on_failure
        self.last_latency_ms: int | None = None
        self.last_error_code: str | None = None

    @property
    def events(self) -> MercedesApiEventBuffer:
        return self._events

    async def get_json(self, endpoint: str) -> Any:
        return await self._request("GET", endpoint, expect_json=True)

    async def get_bytes(self, endpoint: str, *, extra_headers: dict[str, str] | None = None) -> bytes:
        return await self._request("GET", endpoint, expect_json=False, extra_headers=extra_headers)

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        expect_json: bool,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        url = endpoint if endpoint.startswith("http") else f"{self._base_url}{endpoint}"
        retry_count = 0
        refreshed = False
        while retry_count <= MAX_RETRIES:
            started = time.perf_counter()
            http_status: int | None = None
            try:
                access_token = await self._token_store.get_valid_access_token()
                headers = dict(self._request_headers())
                headers["Authorization"] = f"Bearer {access_token}"
                if extra_headers:
                    headers.update(extra_headers)
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.request(method, url, headers=headers)
                http_status = response.status_code
                duration_ms = int((time.perf_counter() - started) * 1000)
                self.last_latency_ms = duration_ms

                if response.status_code == 401 and not refreshed:
                    refreshed = True
                    await self._token_store.force_refresh()
                    retry_count += 1
                    continue

                if response.status_code == 429:
                    retry_after = _retry_after_seconds(response)
                    error = classify_http_status(429, endpoint=endpoint)
                    self._record_event(method, endpoint, http_status, duration_ms, error.code.value, retry_count)
                    self.last_error_code = error.code.value
                    if self._on_failure:
                        await self._on_failure(error)
                    if retry_count >= MAX_RETRIES:
                        raise error
                    await _sleep_backoff(self._backoff.on_rate_limited(), retry_after)
                    retry_count += 1
                    continue

                if response.status_code >= 400:
                    error = classify_http_status(response.status_code, endpoint=endpoint)
                    self._record_event(method, endpoint, http_status, duration_ms, error.code.value, retry_count)
                    self.last_error_code = error.code.value
                    if self._on_failure:
                        await self._on_failure(error)
                    if error.retryable and retry_count < MAX_RETRIES:
                        retry_count += 1
                        await _sleep_backoff(self._backoff.on_failure())
                        continue
                    raise error

                self._record_event(method, endpoint, http_status, duration_ms, None, retry_count)
                self.last_error_code = None
                self._backoff.on_success()
                if self._on_success:
                    await self._on_success()
                if expect_json:
                    try:
                        return response.json()
                    except ValueError as exc:
                        raise MercedesApiError(
                            code=MercedesErrorCode.INVALID_RESPONSE,
                            message=f"Invalid JSON from {endpoint}",
                            http_status=http_status,
                            retryable=False,
                        ) from exc
                return response.content

            except MercedesApiError:
                raise
            except Exception as exc:
                duration_ms = int((time.perf_counter() - started) * 1000)
                error = classify_exception(exc, endpoint=endpoint)
                self._record_event(method, endpoint, http_status, duration_ms, error.code.value, retry_count)
                self.last_error_code = error.code.value
                if self._on_failure:
                    await self._on_failure(error)
                if not error.retryable or retry_count >= MAX_RETRIES:
                    raise error
                retry_count += 1
                await _sleep_backoff(self._backoff.on_failure())

        raise MercedesApiError(
            code=MercedesErrorCode.MERCEDES_API_UNAVAILABLE,
            message=f"Mercedes request failed after retries: {endpoint}",
            retryable=False,
        )

    def _record_event(
        self,
        method: str,
        endpoint: str,
        http_status: int | None,
        duration_ms: int,
        error_code: str | None,
        retry_count: int,
    ) -> None:
        self._events.record(
            endpoint=endpoint,
            method=method,
            http_status=http_status,
            duration_ms=duration_ms,
            error_code=error_code,
            retry_count=retry_count,
        )


def _retry_after_seconds(response: httpx.Response) -> float | None:
    header = response.headers.get("Retry-After")
    if header is None:
        return None
    try:
        return float(header)
    except ValueError:
        return None


async def _sleep_backoff(decision, override_seconds: float | None = None) -> None:
    import asyncio

    delay = override_seconds if override_seconds is not None else decision.delay_seconds
    await asyncio.sleep(delay)
