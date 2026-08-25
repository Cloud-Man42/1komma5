"""Authentication, rate limiting and metrics for the Apple Widget API."""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Annotated

from app.deps import get_app_settings, get_db_session
from energy_core.auth.device_tokens import extract_lookup_prefix, verify_token
from energy_core.config import Settings
from energy_core.db.apple_device_repo import AppleDeviceRecord, AppleDeviceRepository
from energy_core.db.models import AppleDeviceModel
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)


@dataclass
class WidgetMetrics:
    requests_total: int = 0
    errors_total: int = 0
    latency_ms_total: float = 0.0
    latency_samples: int = 0
    snapshot_age_seconds_total: float = 0.0
    snapshot_age_samples: int = 0

    def record_request(
        self,
        *,
        status_code: int,
        duration_ms: float,
        snapshot_age: int | None,
    ) -> None:
        self.requests_total += 1
        if status_code >= 400:
            self.errors_total += 1
        self.latency_ms_total += duration_ms
        self.latency_samples += 1
        if snapshot_age is not None:
            self.snapshot_age_seconds_total += snapshot_age
            self.snapshot_age_samples += 1

    def to_dict(self, active_devices: int) -> dict[str, float | int]:
        avg_latency = (
            round(self.latency_ms_total / self.latency_samples, 2)
            if self.latency_samples
            else 0.0
        )
        avg_age = (
            round(self.snapshot_age_seconds_total / self.snapshot_age_samples, 2)
            if self.snapshot_age_samples
            else 0.0
        )
        return {
            "widget_api_requests_total": self.requests_total,
            "widget_api_errors_total": self.errors_total,
            "widget_api_latency_ms": avg_latency,
            "widget_snapshot_age_seconds": avg_age,
            "widget_active_devices": active_devices,
        }


WIDGET_METRICS = WidgetMetrics()


class WidgetRateLimiter:
    def __init__(self) -> None:
        self._windows: dict[int, deque[float]] = defaultdict(deque)

    def check(self, device_id: int, *, limit_per_minute: int) -> int | None:
        now = time.monotonic()
        window = self._windows[device_id]
        cutoff = now - 60.0
        while window and window[0] <= cutoff:
            window.popleft()
        if len(window) >= limit_per_minute:
            retry_after = max(1, int(60 - (now - window[0])))
            return retry_after
        window.append(now)
        return None


WIDGET_RATE_LIMITER = WidgetRateLimiter()


@dataclass(frozen=True, slots=True)
class AuthenticatedWidgetDevice:
    record: AppleDeviceRecord
    model: AppleDeviceModel


def _parse_scopes(scopes: str) -> set[str]:
    return {part.strip() for part in scopes.split(",") if part.strip()}


async def require_widget_device(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> AuthenticatedWidgetDevice:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()
    prefix = extract_lookup_prefix(token)
    if prefix is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )

    repo = AppleDeviceRepository(session)
    row = await repo.get_by_prefix(prefix)
    if row is None or not verify_token(token, row.token_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if row.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )

    scopes = _parse_scopes(row.scopes)
    if "widget.read" not in scopes:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    retry_after = WIDGET_RATE_LIMITER.check(
        row.id,
        limit_per_minute=settings.widget_rate_limit_per_minute,
    )
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )

    record = repo._to_record(row)
    request.state.widget_device_id = record.id
    return AuthenticatedWidgetDevice(record=record, model=row)


def log_widget_request(
    *,
    device_id: int,
    site_id: str | None,
    endpoint: str,
    status_code: int,
    duration_ms: float,
    snapshot_age: int | None,
) -> None:
    logger.info(
        "widget_api deviceId=%s siteId=%s endpoint=%s statusCode=%s durationMs=%.1f snapshotAge=%s",
        device_id,
        site_id or "-",
        endpoint,
        status_code,
        duration_ms,
        snapshot_age if snapshot_age is not None else "-",
    )
    WIDGET_METRICS.record_request(
        status_code=status_code,
        duration_ms=duration_ms,
        snapshot_age=snapshot_age,
    )
