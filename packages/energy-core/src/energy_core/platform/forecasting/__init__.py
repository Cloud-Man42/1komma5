"""Unified solar forecast platform surface."""

from energy_core.platform.forecasting.factory import (
    build_active_forecast_coordinator,
    build_solar_forecast_coordinator,
    build_solar_geometry_service,
    build_solar_intelligence_coordinator,
    resolve_country_code,
)
from energy_core.platform.forecasting.refresh import (
    load_solar_forecast_snapshot,
    resolve_forecast_for_read,
    resolve_forecast_with_refresh,
)
from energy_core.platform.forecasting.site_config import (
    SolarSiteConfigIssue,
    load_solar_site_config,
    solar_site_config_issue,
)

__all__ = [
    "SolarSiteConfigIssue",
    "build_active_forecast_coordinator",
    "build_solar_forecast_coordinator",
    "build_solar_geometry_service",
    "build_solar_intelligence_coordinator",
    "load_solar_forecast_snapshot",
    "load_solar_site_config",
    "resolve_country_code",
    "resolve_forecast_for_read",
    "resolve_forecast_with_refresh",
    "solar_site_config_issue",
]
