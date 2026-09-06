"""Unified solar forecast platform surface."""

from energy_core.platform.forecasting.factory import (
    build_solar_forecast_coordinator,
    build_solar_geometry_service,
    build_solar_intelligence_coordinator,
    resolve_country_code,
)
from energy_core.platform.forecasting.read_path import (
    load_solar_forecast_snapshot,
    resolve_forecast_for_read,
    resolve_forecast_with_refresh,
)

__all__ = [
    "build_solar_forecast_coordinator",
    "build_solar_geometry_service",
    "build_solar_intelligence_coordinator",
    "load_solar_forecast_snapshot",
    "resolve_country_code",
    "resolve_forecast_for_read",
    "resolve_forecast_with_refresh",
]
