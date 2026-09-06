"""Forecasting contracts."""

from energy_core.contracts.forecasting.solar import ISolarForecastCoordinator
from energy_core.solar_forecast.weather import WeatherForecastProvider

__all__ = ["ISolarForecastCoordinator", "WeatherForecastProvider"]
