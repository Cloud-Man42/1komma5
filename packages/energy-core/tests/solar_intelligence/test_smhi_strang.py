"""Tests for SMHI STRÅNG parsing."""

from energy_core.solar_intelligence.providers.smhi_strang import (
    STRANG_MISSING_VALUE,
    StrangParameterCatalog,
    _parse_strang_timeseries,
)
from energy_core.solar_intelligence.types import SampleQuality


def test_strang_missing_value_not_numeric():
    payload = {"values": [{"date": "2026-08-20T10:00:00Z", "value": STRANG_MISSING_VALUE}]}
    samples = _parse_strang_timeseries(payload, parameter_id=117, provider="smhi-strang")
    assert len(samples) == 1
    assert samples[0].value_wm2 is None
    assert samples[0].quality == SampleQuality.MISSING


def test_strang_parses_ghi():
    payload = {"values": [{"date": "2026-08-20T10:00:00Z", "value": 450.0}]}
    samples = _parse_strang_timeseries(payload, parameter_id=StrangParameterCatalog.GLOBAL_IRRADIANCE, provider="smhi-strang")
    assert samples[0].parameter == "ghi"
    assert samples[0].value_wm2 == 450.0


def test_parameter_catalog_names():
    assert StrangParameterCatalog.name_for(117) == "ghi"
