"""Tests for consumer aggregate helpers."""

from datetime import UTC, datetime

from energy_core.consumer_accounting.aggregator import period_bounds, quality_percentages


def test_period_bounds_day_stockholm():
    ref = datetime(2026, 3, 15, 12, 0, tzinfo=UTC)
    start, end = period_bounds(granularity="day", reference=ref, timezone="Europe/Stockholm")
    assert start < end
    assert 23 * 3600 <= (end - start).total_seconds() <= 25 * 3600


def test_quality_percentages():
    pct = quality_percentages({"CALCULATED": 8, "ESTIMATED": 2})
    assert pct["calculated_pct"] == 80.0
    assert pct["estimated_pct"] == 20.0
