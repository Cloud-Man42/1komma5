"""Tests for spa sample backfill."""

from types import SimpleNamespace

from energy_core.consumer_accounting.sample_backfill import SpaSampleBackfillService


def test_sample_totals():
    samples = [
        SimpleNamespace(energy_delta_wh=0.0, power_w=0.0),
        SimpleNamespace(energy_delta_wh=500.0, power_w=3000.0),
        SimpleNamespace(energy_delta_wh=250.0, power_w=1500.0),
    ]
    totals = SpaSampleBackfillService.sample_totals(samples)
    assert totals["energy_kwh"] == 0.75
    assert totals["samples_with_energy"] == 2
    assert totals["samples_with_power"] == 2
