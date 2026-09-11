"""Tests for telemetry provider facade."""

from energy_core.integrations.heartbeat.telemetry import (
    SungrowTelemetrySnapshot as HeartbeatSnapshot,
    map_heartbeat_to_sungrow as heartbeat_map,
)
from energy_core.providers.telemetry import SungrowTelemetrySnapshot, map_heartbeat_to_sungrow


def test_telemetry_provider_reexports_heartbeat_facade() -> None:
    assert SungrowTelemetrySnapshot is HeartbeatSnapshot
    assert map_heartbeat_to_sungrow is heartbeat_map
