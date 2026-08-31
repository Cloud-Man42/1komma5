"""Tests for Mercedes integration health service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from energy_core.vehicles.health import IntegrationHealthStatus, MercedesIntegrationHealthService


def test_vehicle_sleeping_when_api_ok_but_vehicle_stale():
    now = datetime.now(UTC)
    health = MercedesIntegrationHealthService().evaluate(
        enabled=True,
        connection_state="CONNECTED",
        last_success_at=now,
        last_failure_at=None,
        last_vehicle_update=now - timedelta(minutes=10),
        last_token_refresh_at=now,
        consecutive_failures=0,
        last_error_code=None,
        last_latency_ms=120,
        blocked_since=None,
        backoff_until=None,
        token_configured=True,
    )
    assert health.status == IntegrationHealthStatus.VEHICLE_SLEEPING


def test_api_unavailable_on_repeated_failures():
    now = datetime.now(UTC)
    health = MercedesIntegrationHealthService().evaluate(
        enabled=True,
        connection_state="BACKOFF",
        last_success_at=now - timedelta(minutes=20),
        last_failure_at=now,
        last_vehicle_update=now - timedelta(minutes=20),
        last_token_refresh_at=now - timedelta(hours=1),
        consecutive_failures=5,
        last_error_code="MERCEDES_API_UNAVAILABLE",
        last_latency_ms=None,
        blocked_since=None,
        backoff_until=now + timedelta(minutes=5),
        token_configured=True,
    )
    assert health.status in {
        IntegrationHealthStatus.MERCEDES_BACKEND_UNAVAILABLE,
        IntegrationHealthStatus.OFFLINE,
    }
