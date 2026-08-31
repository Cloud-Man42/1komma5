"""Mercedes API error classification."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import httpx


class MercedesErrorCode(StrEnum):
    AUTH_FAILED = "AUTH_FAILED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_REFRESH_FAILED = "TOKEN_REFRESH_FAILED"
    VEHICLE_OFFLINE = "VEHICLE_OFFLINE"
    VEHICLE_ASLEEP = "VEHICLE_ASLEEP"
    RATE_LIMITED = "RATE_LIMITED"
    MERCEDES_API_UNAVAILABLE = "MERCEDES_API_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    DATA_STALE = "DATA_STALE"
    LOCATION_UNAVAILABLE = "LOCATION_UNAVAILABLE"
    CHARGING_DATA_UNAVAILABLE = "CHARGING_DATA_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class MercedesApiError(Exception):
    code: MercedesErrorCode
    message: str
    http_status: int | None = None
    retryable: bool = True
    counts_toward_offline: bool = False

    def __str__(self) -> str:
        return self.message


def classify_exception(exc: Exception, *, endpoint: str = "") -> MercedesApiError:
    if isinstance(exc, MercedesApiError):
        return exc
    if isinstance(exc, httpx.TimeoutException):
        return MercedesApiError(
            code=MercedesErrorCode.TIMEOUT,
            message=f"Mercedes API timeout for {endpoint or 'request'}",
            retryable=True,
            counts_toward_offline=False,
        )
    if isinstance(exc, httpx.ConnectError):
        return MercedesApiError(
            code=MercedesErrorCode.NETWORK_ERROR,
            message=str(exc) or "Network error contacting Mercedes API",
            retryable=True,
            counts_toward_offline=False,
        )
    if isinstance(exc, httpx.HTTPStatusError):
        return classify_http_status(exc.response.status_code, endpoint=endpoint, detail=str(exc))
    return MercedesApiError(
        code=MercedesErrorCode.MERCEDES_API_UNAVAILABLE,
        message=str(exc) or "Mercedes API request failed",
        retryable=True,
        counts_toward_offline=False,
    )


def classify_http_status(status_code: int, *, endpoint: str = "", detail: str = "") -> MercedesApiError:
    message = detail or f"Mercedes API returned HTTP {status_code} for {endpoint or 'request'}"
    if status_code == 401:
        return MercedesApiError(
            code=MercedesErrorCode.TOKEN_EXPIRED,
            message=message,
            http_status=status_code,
            retryable=True,
            counts_toward_offline=False,
        )
    if status_code == 403:
        return MercedesApiError(
            code=MercedesErrorCode.AUTH_FAILED,
            message=message,
            http_status=status_code,
            retryable=False,
            counts_toward_offline=True,
        )
    if status_code == 429:
        return MercedesApiError(
            code=MercedesErrorCode.RATE_LIMITED,
            message=message,
            http_status=status_code,
            retryable=True,
            counts_toward_offline=False,
        )
    if status_code >= 500:
        return MercedesApiError(
            code=MercedesErrorCode.MERCEDES_API_UNAVAILABLE,
            message=message,
            http_status=status_code,
            retryable=True,
            counts_toward_offline=False,
        )
    return MercedesApiError(
        code=MercedesErrorCode.INVALID_RESPONSE,
        message=message,
        http_status=status_code,
        retryable=False,
        counts_toward_offline=False,
    )
