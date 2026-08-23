"""Tests for anti-flapping logic."""

from datetime import UTC, datetime, timedelta

from energy_core.charging.anti_flapping import (
    AntiFlappingConfig,
    AntiFlappingState,
    record_applied,
    should_apply_current,
)


def test_anti_flapping_hysteresis():
    state = AntiFlappingState(last_applied_current_a=10.0, last_change_at=datetime.now(UTC))
    config = AntiFlappingConfig(current_hysteresis_a=1.0, min_change_interval_seconds=0)
    apply_ok, applied, reason = should_apply_current(10.4, state, config)
    assert apply_ok is False
    assert applied == 10.0
    assert reason == "hysteresis"


def test_min_interval_blocks_change():
    now = datetime.now(UTC)
    state = AntiFlappingState(
        last_applied_current_a=8.0, last_change_at=now - timedelta(seconds=10)
    )
    config = AntiFlappingConfig(min_change_interval_seconds=60, current_hysteresis_a=0)
    apply_ok, _, reason = should_apply_current(12.0, state, config, now=now)
    assert apply_ok is False
    assert reason == "min_interval"


def test_duplicate_command_skipped():
    state = AntiFlappingState(last_command_current_a=8.0, last_applied_current_a=8.0)
    config = AntiFlappingConfig(min_change_interval_seconds=0, current_hysteresis_a=0)
    apply_ok, _, reason = should_apply_current(8.0, state, config)
    assert apply_ok is False
    assert reason == "duplicate_command"


def test_apply_and_record():
    state = AntiFlappingState()
    config = AntiFlappingConfig(min_change_interval_seconds=0, current_hysteresis_a=0)
    apply_ok, applied, _ = should_apply_current(8.0, state, config)
    assert apply_ok is True
    assert applied == 8.0
    record_applied(state, 8.0)
    assert state.last_applied_current_a == 8.0
