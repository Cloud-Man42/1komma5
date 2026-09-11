"""Inverter telemetry wiring outside feature modules."""

from __future__ import annotations

from energy_core.integrations.heartbeat.telemetry import SungrowTelemetrySnapshot, map_heartbeat_to_sungrow

__all__ = ["SungrowTelemetrySnapshot", "map_heartbeat_to_sungrow"]
