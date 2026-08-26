"""Tests for spa cleaning requirement."""

from datetime import UTC, datetime, timedelta

from energy_core.spa_energy.requirement import build_cleaning_requirement, detect_last_cleaning_end


def test_detect_last_cleaning_end():
    t0 = datetime(2026, 8, 26, 8, 0, tzinfo=UTC)
    samples = [
        (t0, "Idle"),
        (t0 + timedelta(minutes=30), "Filtering"),
        (t0 + timedelta(hours=2), "Filtering"),
        (t0 + timedelta(hours=2, minutes=30), "Idle"),
    ]
    end = detect_last_cleaning_end(samples)
    assert end == t0 + timedelta(hours=2, minutes=30)


def test_build_cleaning_requirement():
    now = datetime(2026, 8, 26, 10, 0, tzinfo=UTC)
    req = build_cleaning_requirement(
        now=now,
        filter_frequency_per_day=1.0,
        filter_duration_hours=2.0,
        min_cleaning_hours_per_day=2.0,
        last_cleaning_end=now - timedelta(hours=20),
        timezone="Europe/Stockholm",
        allowed_window_end_hhmm="22:00",
    )
    assert req.minimum_runtime_hours >= 2.0
    assert req.cleaning_deadline > now
