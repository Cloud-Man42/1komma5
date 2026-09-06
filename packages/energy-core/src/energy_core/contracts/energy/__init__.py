"""Energy domain contract re-exports."""

from energy_core.contracts.energy.battery import IBatteryTelemetry
from energy_core.contracts.energy.inverter import IInverterTelemetry

__all__ = ["IBatteryTelemetry", "IInverterTelemetry"]
