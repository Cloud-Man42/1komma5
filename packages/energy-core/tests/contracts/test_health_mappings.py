"""Unified health status mapping tests."""

from energy_core.contracts.health import (
    HealthStatus,
    aggregate_health_status,
    from_chargefinder_status,
    from_energy_provider_status,
    from_solar_intelligence_status,
    from_spa_health,
    from_vehicle_integration_status,
    from_vehicle_summary_health,
    to_energy_provider_status,
    to_vehicle_integration_status,
)


def test_vehicle_integration_status_mapping() -> None:
    assert from_vehicle_integration_status("CONNECTED") == HealthStatus.HEALTHY
    assert from_vehicle_integration_status("DATA_STALE") == HealthStatus.DEGRADED
    assert from_vehicle_integration_status("OFFLINE") == HealthStatus.UNAVAILABLE


def test_energy_provider_status_mapping() -> None:
    assert from_energy_provider_status("ok") == HealthStatus.HEALTHY
    assert from_energy_provider_status("stale") == HealthStatus.DEGRADED
    assert from_energy_provider_status("error") == HealthStatus.UNAVAILABLE


def test_solar_intelligence_status_mapping() -> None:
    assert from_solar_intelligence_status("HEALTHY") == HealthStatus.HEALTHY
    assert from_solar_intelligence_status("UNKNOWN") == HealthStatus.UNAVAILABLE


def test_chargefinder_status_mapping() -> None:
    assert from_chargefinder_status("AVAILABLE") == HealthStatus.HEALTHY
    assert from_chargefinder_status("DISABLED") == HealthStatus.DISABLED


def test_reverse_mappings_preserve_api_compatibility() -> None:
    assert to_vehicle_integration_status(HealthStatus.HEALTHY) == "CONNECTED"
    assert to_energy_provider_status(HealthStatus.DEGRADED) == "degraded"


def test_unknown_status_defaults_to_unavailable() -> None:
    assert from_vehicle_integration_status("NOT_A_STATUS") == HealthStatus.UNAVAILABLE


def test_vehicle_summary_health_mapping() -> None:
    assert from_vehicle_summary_health("HEALTHY") == HealthStatus.HEALTHY
    assert from_vehicle_summary_health("UNHEALTHY") == HealthStatus.UNAVAILABLE


def test_spa_health_mapping() -> None:
    assert (
        from_spa_health(
            integration_enabled=False,
            api_status="OK",
            spa_status="ONLINE",
            integration_degraded=False,
        )
        == HealthStatus.DISABLED
    )
    assert (
        from_spa_health(
            integration_enabled=True,
            api_status="OK",
            spa_status="ONLINE",
            integration_degraded=False,
        )
        == HealthStatus.HEALTHY
    )
    assert (
        from_spa_health(
            integration_enabled=True,
            api_status="OK",
            spa_status="OFFLINE",
            integration_degraded=False,
        )
        == HealthStatus.DEGRADED
    )


def test_aggregate_health_status() -> None:
    assert aggregate_health_status((HealthStatus.HEALTHY, HealthStatus.HEALTHY)) == HealthStatus.HEALTHY
    assert aggregate_health_status((HealthStatus.HEALTHY, HealthStatus.UNAVAILABLE)) == HealthStatus.DEGRADED
    assert aggregate_health_status(()) == HealthStatus.UNAVAILABLE
