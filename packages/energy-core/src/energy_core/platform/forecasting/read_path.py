"""Backward-compatible re-exports — prefer site_config and refresh modules."""

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
    "load_solar_forecast_snapshot",
    "load_solar_site_config",
    "resolve_forecast_for_read",
    "resolve_forecast_with_refresh",
    "solar_site_config_issue",
]
