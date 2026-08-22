"""Tests for inferred Arctic Spa power model."""

from energy_core.consumer_accounting.types import DataQuality
from energy_core.integrations.arctic_spa.config import SpaPowerProfiles
from energy_core.integrations.arctic_spa.inferred_meter import InferredArcticSpaMeter
from energy_core.integrations.arctic_spa.models import ArcticSpaStatus


def _status(**kwargs) -> ArcticSpaStatus:
    payload = {
        "connected": True,
        "temperatureF": 100,
        "setpointF": 102,
        "pump1": "off",
        "pump2": "off",
        "filter_status": "Filtering",
        "errors": [],
    }
    payload.update(kwargs)
    return ArcticSpaStatus.from_api(payload)


def test_pump_and_heater_power_summed():
    meter = InferredArcticSpaMeter(profiles=SpaPowerProfiles(heater_w=3000, pump_low_w=150, pump_high_w=400))
    sample = meter.estimate_sample(
        _status(pump1="high"),
        prev_status=None,
        elapsed_seconds=60,
        poll_interval_seconds=60,
    )
    assert sample.power_w == 3400
    assert sample.quality == DataQuality.CALCULATED
    assert sample.energy_delta_wh > 0


def test_offline_sample_is_missing():
    meter = InferredArcticSpaMeter(profiles=SpaPowerProfiles())
    sample = meter.estimate_sample(
        _status(connected=False),
        prev_status=None,
        elapsed_seconds=60,
        poll_interval_seconds=60,
    )
    assert sample.quality == DataQuality.MISSING
    assert sample.energy_delta_wh == 0


def test_large_gap_marks_estimated_without_energy():
    meter = InferredArcticSpaMeter(profiles=SpaPowerProfiles())
    sample = meter.estimate_sample(
        _status(pump1="high"),
        prev_status=None,
        elapsed_seconds=300,
        poll_interval_seconds=60,
    )
    assert sample.quality == DataQuality.ESTIMATED
    assert sample.energy_delta_wh == 0
