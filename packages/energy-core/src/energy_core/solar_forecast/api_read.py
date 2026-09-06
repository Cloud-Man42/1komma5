"""Shim — use energy_core.platform.forecasting.read_path."""

from energy_core.platform.forecasting.read_path import (
    load_solar_forecast_snapshot,
    resolve_forecast_for_read,
)

__all__ = ["load_solar_forecast_snapshot", "resolve_forecast_for_read"]
