"""Charge Amps meter readings (shim — canonical home: integrations.chargeamps.meter_adapter)."""

from __future__ import annotations

from energy_core.contracts.devices.meter import (
    IMeterReader,
    MeterSnapshot,
    integrate_power_kwh,
    session_energy_from_meter,
)
from energy_core.integrations.chargeamps.meter_adapter import (
    DEFAULT_CONNECTOR_ID,
    DEFAULT_NOMINAL_VOLTAGE_V,
    ChargeAmpsMeterAdapter,
)

# Backward-compatible alias used by legacy code.
MeterReader = IMeterReader

__all__ = [
    "ChargeAmpsMeterAdapter",
    "DEFAULT_CONNECTOR_ID",
    "DEFAULT_NOMINAL_VOLTAGE_V",
    "IMeterReader",
    "MeterReader",
    "MeterSnapshot",
    "integrate_power_kwh",
    "session_energy_from_meter",
]
