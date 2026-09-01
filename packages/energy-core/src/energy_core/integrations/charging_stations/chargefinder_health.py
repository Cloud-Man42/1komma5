"""ChargeFinder integration health derivation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from energy_core.db.chargefinder_integration_status_repo import ChargeFinderIntegrationStatusRecord
from energy_core.integrations.charging_stations.chargefinder.provider import ChargeFinderMode


class ChargeFinderHealthStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"
    UNAVAILABLE = "UNAVAILABLE"
    DISABLED = "DISABLED"


@dataclass(frozen=True, slots=True)
class ChargeFinderHealthSnapshot:
    status: ChargeFinderHealthStatus
    mode: str
    enabled: bool
    last_success_at: datetime | None
    last_failure_at: datetime | None
    last_lookup_at: datetime | None
    last_latency_ms: int | None
    consecutive_failures: int
    last_error: str | None
    cache_hits: int
    cache_misses: int
    parser_failures: int
    blocked_until: datetime | None
    browser_status: str | None
    parsing_version: str


class ChargeFinderIntegrationHealthService:
    def evaluate(
        self,
        *,
        enabled: bool,
        mode: ChargeFinderMode,
        status: ChargeFinderIntegrationStatusRecord,
    ) -> ChargeFinderHealthSnapshot:
        if not enabled or mode == ChargeFinderMode.DISABLED:
            return _snapshot(
                ChargeFinderHealthStatus.DISABLED,
                enabled=False,
                mode=mode.value,
                status=status,
            )

        now = datetime.now(UTC)
        if status.blocked_until is not None and now < _aware(status.blocked_until):
            return _snapshot(
                ChargeFinderHealthStatus.BLOCKED,
                enabled=True,
                mode=mode.value,
                status=status,
            )

        if mode == ChargeFinderMode.MANUAL:
            return _snapshot(
                ChargeFinderHealthStatus.DEGRADED,
                enabled=True,
                mode=mode.value,
                status=status,
            )

        health = ChargeFinderHealthStatus.AVAILABLE
        if status.consecutive_failures >= 3:
            health = ChargeFinderHealthStatus.UNAVAILABLE
        elif status.consecutive_failures >= 1 or status.parser_failures >= 2:
            health = ChargeFinderHealthStatus.DEGRADED
        elif status.last_success_at is None and status.last_failure_at is not None:
            health = ChargeFinderHealthStatus.UNAVAILABLE
        elif status.last_success_at is not None:
            age = (now - _aware(status.last_success_at)).total_seconds()
            if age > 86400:
                health = ChargeFinderHealthStatus.DEGRADED

        return _snapshot(health, enabled=True, mode=mode.value, status=status)


def _snapshot(
    status_value: ChargeFinderHealthStatus,
    *,
    enabled: bool,
    mode: str,
    status: ChargeFinderIntegrationStatusRecord,
) -> ChargeFinderHealthSnapshot:
    return ChargeFinderHealthSnapshot(
        status=status_value,
        mode=mode,
        enabled=enabled,
        last_success_at=status.last_success_at,
        last_failure_at=status.last_failure_at,
        last_lookup_at=status.last_lookup_at,
        last_latency_ms=status.last_latency_ms,
        consecutive_failures=status.consecutive_failures,
        last_error=status.last_error,
        cache_hits=status.cache_hits,
        cache_misses=status.cache_misses,
        parser_failures=status.parser_failures,
        blocked_until=status.blocked_until,
        browser_status=status.browser_status,
        parsing_version=status.parsing_version,
    )


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
