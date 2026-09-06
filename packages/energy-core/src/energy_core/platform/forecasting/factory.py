"""Unified solar forecast stack factory."""

from __future__ import annotations

from energy_core.config import Settings
from energy_core.solar_forecast.coordinator import SolarForecastCoordinator
from energy_core.solar_intelligence.geometry import SolarGeometryService
from energy_core.solar_intelligence.provider_factory import resolve_country_code
from energy_core.solar_intelligence.service import SolarIntelligenceCoordinator


def build_solar_forecast_coordinator(settings: Settings) -> SolarForecastCoordinator:
    return SolarForecastCoordinator(settings)


def build_solar_intelligence_coordinator(settings: Settings) -> SolarIntelligenceCoordinator:
    return SolarIntelligenceCoordinator(settings)


def build_active_forecast_coordinator(
    settings: Settings,
    *,
    solar_intelligence_enabled: bool,
) -> SolarForecastCoordinator | SolarIntelligenceCoordinator:
    if solar_intelligence_enabled:
        return build_solar_intelligence_coordinator(settings)
    return build_solar_forecast_coordinator(settings)


def build_solar_geometry_service(
    *,
    latitude: float,
    longitude: float,
    timezone: str,
) -> SolarGeometryService:
    return SolarGeometryService(
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
    )


__all__ = [
    "SolarForecastCoordinator",
    "SolarGeometryService",
    "SolarIntelligenceCoordinator",
    "build_active_forecast_coordinator",
    "build_solar_forecast_coordinator",
    "build_solar_geometry_service",
    "build_solar_intelligence_coordinator",
    "resolve_country_code",
]
