"""Tests for spa sample backfill."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from energy_core.consumer_accounting.sample_backfill import (
    SpaSampleBackfillService,
    _energy_wh_for_pair,
)


def test_sample_totals_from_power_pairs():
    now = datetime.now(UTC)
    samples = [
        SimpleNamespace(
            recorded_at=now,
            energy_delta_wh=0.0,
            power_w=3000.0,
        ),
        SimpleNamespace(
            recorded_at=now + timedelta(seconds=60),
            energy_delta_wh=0.0,
            power_w=3000.0,
        ),
    ]
    totals = SpaSampleBackfillService.sample_totals(samples, poll_interval_seconds=60)
    assert totals["energy_kwh"] == 0.05
    assert totals["samples_with_power"] == 2


def test_energy_wh_for_pair_skips_long_gap():
    now = datetime.now(UTC)
    prev = SimpleNamespace(recorded_at=now, energy_delta_wh=0.0, power_w=3000.0)
    curr = SimpleNamespace(recorded_at=now + timedelta(hours=5), energy_delta_wh=0.0, power_w=3000.0)
    assert _energy_wh_for_pair(prev, curr, poll_interval_seconds=60) == 0.0
