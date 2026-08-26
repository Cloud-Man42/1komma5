"""Tests for flexible load deadline urgency."""

from datetime import UTC, datetime, timedelta

from energy_core.flexible_load.deadline import compute_deadline_urgency


def test_deadline_critical_under_2_hours():
    now = datetime(2026, 8, 26, 10, 0, tzinfo=UTC)
    urgency = compute_deadline_urgency(now, now + timedelta(hours=1))
    assert urgency.tier == "critical"
    assert urgency.run_regardless is True


def test_deadline_relaxed_over_12_hours():
    now = datetime(2026, 8, 26, 10, 0, tzinfo=UTC)
    urgency = compute_deadline_urgency(now, now + timedelta(hours=20))
    assert urgency.tier == "relaxed"
    assert urgency.min_score == 20.0
