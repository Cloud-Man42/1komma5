"""HeartBeat telemetry mapping for inverter/EMS features."""

from __future__ import annotations

from energy_core.sungrow.heartbeat_provider import map_heartbeat_to_sungrow
from energy_core.sungrow.types import SungrowTelemetrySnapshot

__all__ = ["SungrowTelemetrySnapshot", "map_heartbeat_to_sungrow"]
