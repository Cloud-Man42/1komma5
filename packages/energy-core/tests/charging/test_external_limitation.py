"""Tests for external limitation detection."""

from datetime import UTC, datetime, timedelta

from energy_core.charging.external_limitation import (
    EXTERNAL_LIMIT_STABLE_SECONDS,
    ExternalLimitationTracker,
)


def test_not_limited_when_actual_matches_requested():
    tracker = ExternalLimitationTracker()
    now = datetime(2026, 8, 20, 10, 0, tzinfo=UTC)
    limited = tracker.update(
        requested_current_a=12.0,
        configured_current_a=12.0,
        actual_charging_current_a=11.5,
        is_charging=True,
        now=now,
    )
    assert limited is False


def test_limited_after_stable_gap():
    tracker = ExternalLimitationTracker()
    start = datetime(2026, 8, 20, 10, 0, tzinfo=UTC)
    for offset in range(0, int(EXTERNAL_LIMIT_STABLE_SECONDS) + 5, 5):
        limited = tracker.update(
            requested_current_a=12.0,
            configured_current_a=12.0,
            actual_charging_current_a=7.0,
            is_charging=True,
            now=start + timedelta(seconds=offset),
        )
    assert limited is True


def test_not_limited_without_actual_current():
    tracker = ExternalLimitationTracker()
    now = datetime(2026, 8, 20, 10, 0, tzinfo=UTC)
    limited = tracker.update(
        requested_current_a=12.0,
        configured_current_a=12.0,
        actual_charging_current_a=None,
        is_charging=True,
        now=now,
    )
    assert limited is False
