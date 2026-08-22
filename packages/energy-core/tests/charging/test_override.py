"""Tests for manual charger override."""

from datetime import UTC, datetime, timedelta

import pytest

from energy_core.charging.override import (
    ALLOWED_OVERRIDE_HOURS,
    override_active,
    override_decision,
    override_until_from_hours,
)
from energy_core.charging.override import BridgeChargerConfig


def test_allowed_override_hours():
    assert ALLOWED_OVERRIDE_HOURS == {4, 8, 12, 24}


def test_override_active_when_future():
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    until = now + timedelta(hours=4)
    assert override_active(until, now=now) is True


def test_override_inactive_when_expired():
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    until = now - timedelta(minutes=1)
    assert override_active(until, now=now) is False


def test_override_until_from_hours_rejects_invalid():
    with pytest.raises(ValueError):
        override_until_from_hours(6)


def test_override_decision_requests_max_current():
    decision = override_decision(config=BridgeChargerConfig(max_current_a=16, min_current_a=6))
    assert decision.requested_current_a == 16.0
    assert decision.policy_mode == "override"
    assert decision.reason == "manual_override"
