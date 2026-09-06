"""Platform forecasting factory tests."""

from __future__ import annotations


def test_build_solar_forecast_coordinator_implements_contract() -> None:
    from energy_core.config import get_settings
    from energy_core.contracts.forecasting import ISolarForecastCoordinator
    from energy_core.platform.forecasting import build_solar_forecast_coordinator

    coordinator = build_solar_forecast_coordinator(get_settings())
    assert isinstance(coordinator, ISolarForecastCoordinator)
