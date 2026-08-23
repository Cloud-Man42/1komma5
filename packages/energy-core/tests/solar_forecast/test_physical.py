"""Tests for physical PV baseline model."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from energy_core.solar_forecast.physical import baseline_energy_kwh, baseline_power_w
from energy_core.solar_forecast.types import SolarSiteConfiguration, WeatherForecastPoint


def _site(**kwargs) -> SolarSiteConfiguration:
    defaults = dict(
        site_id=1,
        latitude=55.6,
        longitude=13.0,
        installed_peak_power_kw=8.0,
        enabled=True,
    )
    defaults.update(kwargs)
    return SolarSiteConfiguration(**defaults)


def test_zero_irradiance_gives_zero_power() -> None:
    site = _site()
    point = WeatherForecastPoint(timestamp=datetime(2026, 6, 15, 12, 0, tzinfo=UTC), gti_wm2=0.0)
    assert baseline_power_w(point, site) == 0.0


def test_positive_irradiance_gives_positive_power() -> None:
    site = _site()
    point = WeatherForecastPoint(timestamp=datetime(2026, 6, 15, 12, 0, tzinfo=UTC), gti_wm2=800.0)
    power = baseline_power_w(point, site)
    assert power > 0


def test_inverter_clipping() -> None:
    site = _site(inverter_max_power_kw=5.0)
    point = WeatherForecastPoint(timestamp=datetime(2026, 6, 15, 12, 0, tzinfo=UTC), gti_wm2=1000.0)
    power = baseline_power_w(point, site)
    assert power <= 5000.0 + 1e-6


def test_disabled_site_returns_zero() -> None:
    site = _site(enabled=False)
    point = WeatherForecastPoint(timestamp=datetime(2026, 6, 15, 12, 0, tzinfo=UTC), gti_wm2=800.0)
    assert baseline_power_w(point, site) == 0.0


def test_system_loss_reduces_output() -> None:
    site_low = _site(system_loss_percent=5.0)
    site_high = _site(system_loss_percent=20.0)
    point = WeatherForecastPoint(timestamp=datetime(2026, 6, 15, 12, 0, tzinfo=UTC), gti_wm2=700.0)
    assert baseline_power_w(point, site_low) > baseline_power_w(point, site_high)


def test_baseline_energy_from_power() -> None:
    assert baseline_energy_kwh(4000.0) == pytest.approx(1.0)
