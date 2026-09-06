"""Shim — use energy_core.platform.forecasting.read_path."""

from energy_core.platform.forecasting.read_path import (
    load_solar_forecast_snapshot,
    load_solar_site_config,
    resolve_forecast_for_read,
    resolve_forecast_with_refresh,
    solar_site_config_issue,
)

__all__ = [
    "load_solar_forecast_snapshot",
    "load_solar_site_config",
    "resolve_forecast_for_read",
    "resolve_forecast_with_refresh",
    "solar_site_config_issue",
]
