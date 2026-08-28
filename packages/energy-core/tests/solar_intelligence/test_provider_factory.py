"""Tests for country-aware solar provider routing."""

from __future__ import annotations

from energy_core.config import Settings
from energy_core.solar_intelligence.confidence import radiation_confidence_for_location
from energy_core.solar_intelligence.provider_factory import (
    SolarIntelligenceProviderFactory,
    resolve_country_code,
)
from energy_core.solar_intelligence.types import RadiationSourceConfidence


def test_resolve_country_code_from_explicit_value():
    assert resolve_country_code("dk", latitude=55.0, longitude=12.0) == "DK"


def test_resolve_country_code_infers_denmark():
    assert resolve_country_code(None, latitude=55.715, longitude=12.561) == "DK"


def test_resolve_country_code_infers_sweden_for_skane():
    assert resolve_country_code(None, latitude=55.60, longitude=13.00) == "SE"


def test_resolve_country_code_infers_sweden_for_stockholm():
    assert resolve_country_code(None, latitude=59.3, longitude=18.0) == "SE"


def test_provider_factory_selects_dmi_for_denmark():
    factory = SolarIntelligenceProviderFactory(Settings())
    bundle = factory.bundle_for(country_code="DK", latitude=55.715, longitude=12.561)
    assert bundle.radiation_name == "dmi-harmonie"
    assert bundle.weather_name == "dmi-harmonie"


def test_provider_factory_selects_smhi_for_sweden():
    factory = SolarIntelligenceProviderFactory(Settings())
    bundle = factory.bundle_for(country_code="SE", latitude=59.3, longitude=18.0)
    assert bundle.radiation_name == "smhi-strang"
    assert bundle.weather_name == "smhi-snow"


def test_dmi_radiation_confidence_high_in_denmark():
    conf = radiation_confidence_for_location(
        latitude=55.715,
        longitude=12.561,
        provider="dmi-harmonie",
    )
    assert conf == RadiationSourceConfidence.HIGH
