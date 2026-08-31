"""Mercedes integration health derivation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from energy_core.vehicles.abstractions.models import VehicleConnectionState
from energy_core.vehicles.mercedes.constants import STALE_TELEMETRY_SECONDS


class IntegrationHealthStatus(StrEnum):
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    MERCEDES_BACKEND_UNAVAILABLE = "MERCEDES_BACKEND_UNAVAILABLE"
    VEHICLE_SLEEPING = "VEHICLE_SLEEPING"
    DATA_STALE = "DATA_STALE"


@dataclass(frozen=True, slots=True)
class IntegrationHealthSnapshot:
    status: IntegrationHealthStatus
    last_success_at: datetime | None
    last_failure_at: datetime | None
    last_vehicle_update: datetime | None
    last_token_refresh_at: datetime | None
    consecutive_failures: int
    last_error_code: str | None
    last_latency_ms: int | None
    vehicle_data_age_seconds: float | None
    api_data_age_seconds: float | None


class MercedesIntegrationHealthService:
    """Derives integration health from connection row and latest vehicle telemetry."""

    def evaluate(
        self,
        *,
        enabled: bool,
        connection_state: str,
        last_success_at: datetime | None,
        last_failure_at: datetime | None,
        last_vehicle_update: datetime | None,
        last_token_refresh_at: datetime | None,
        consecutive_failures: int,
        last_error_code: str | None,
        last_latency_ms: int | None,
        blocked_since: datetime | None,
        backoff_until: datetime | None,
        token_configured: bool,
    ) -> IntegrationHealthSnapshot:
        now = datetime.now(UTC)
        vehicle_age = _age_seconds(now, last_vehicle_update)
        api_age = _age_seconds(now, last_success_at)

        if not enabled:
            return IntegrationHealthSnapshot(
                status=IntegrationHealthStatus.OFFLINE,
                last_success_at=last_success_at,
                last_failure_at=last_failure_at,
                last_vehicle_update=last_vehicle_update,
                last_token_refresh_at=last_token_refresh_at,
                consecutive_failures=consecutive_failures,
                last_error_code=last_error_code,
                last_latency_ms=last_latency_ms,
                vehicle_data_age_seconds=vehicle_age,
                api_data_age_seconds=api_age,
            )

        if not token_configured:
            return IntegrationHealthSnapshot(
                status=IntegrationHealthStatus.AUTHENTICATION_REQUIRED,
                last_success_at=last_success_at,
                last_failure_at=last_failure_at,
                last_vehicle_update=last_vehicle_update,
                last_token_refresh_at=last_token_refresh_at,
                consecutive_failures=consecutive_failures,
                last_error_code=last_error_code,
                last_latency_ms=last_latency_ms,
                vehicle_data_age_seconds=vehicle_age,
                api_data_age_seconds=api_age,
            )

        status = IntegrationHealthStatus.CONNECTED

        if last_error_code in {"AUTH_FAILED", "TOKEN_REFRESH_FAILED"}:
            status = IntegrationHealthStatus.AUTHENTICATION_REQUIRED
        elif blocked_since is not None or last_error_code == "RATE_LIMITED":
            status = IntegrationHealthStatus.MERCEDES_BACKEND_UNAVAILABLE
        elif consecutive_failures >= 3 and (api_age is None or api_age > STALE_TELEMETRY_SECONDS):
            status = IntegrationHealthStatus.MERCEDES_BACKEND_UNAVAILABLE
        elif connection_state in {
            VehicleConnectionState.DISCONNECTED.value,
            VehicleConnectionState.BACKOFF.value,
        } and (api_age is None or api_age > STALE_TELEMETRY_SECONDS):
            status = IntegrationHealthStatus.OFFLINE
        elif connection_state == VehicleConnectionState.DEGRADED.value:
            status = IntegrationHealthStatus.DEGRADED
        elif last_success_at is not None and (api_age is None or api_age <= STALE_TELEMETRY_SECONDS):
            if vehicle_age is not None and vehicle_age > STALE_TELEMETRY_SECONDS:
                status = IntegrationHealthStatus.VEHICLE_SLEEPING
            elif vehicle_age is not None and vehicle_age > STALE_TELEMETRY_SECONDS / 2:
                status = IntegrationHealthStatus.DATA_STALE

        if backoff_until is not None and backoff_until > now and status == IntegrationHealthStatus.CONNECTED:
            status = IntegrationHealthStatus.DEGRADED

        return IntegrationHealthSnapshot(
            status=status,
            last_success_at=last_success_at,
            last_failure_at=last_failure_at,
            last_vehicle_update=last_vehicle_update,
            last_token_refresh_at=last_token_refresh_at,
            consecutive_failures=consecutive_failures,
            last_error_code=last_error_code,
            last_latency_ms=last_latency_ms,
            vehicle_data_age_seconds=vehicle_age,
            api_data_age_seconds=api_age,
        )


def _age_seconds(now: datetime, timestamp: datetime | None) -> float | None:
    if timestamp is None:
        return None
    ts = timestamp if timestamp.tzinfo is not None else timestamp.replace(tzinfo=UTC)
    return max(0.0, (now - ts).total_seconds())
