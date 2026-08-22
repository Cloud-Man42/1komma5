"""Tests for charging mode policy helpers."""

from energy_core.charging.policy import (
    bypasses_guardrails,
    decision_policy_mode,
    ignores_schedule_constraints,
    immediate_start,
    respects_manual_pause,
    uses_price_optimization,
    uses_start_delay,
)


def test_override_overrides_pause():
    assert respects_manual_pause("PAUSED", override_active=True) is False
    assert respects_manual_pause("PAUSED", override_active=False) is True


def test_immediate_start_for_quick_and_override():
    assert immediate_start("QUICK_CHARGE", override_active=False) is True
    assert immediate_start("SMART_CHARGE", override_active=False) is False
    assert immediate_start("PAUSED", override_active=True) is True


def test_start_delay_only_for_smart():
    assert uses_start_delay("SMART_CHARGE", override_active=False) is True
    assert uses_start_delay("PRICE_CHARGE", override_active=False) is True
    assert uses_start_delay("SOLAR_CHARGE", override_active=False) is False
    assert uses_start_delay("QUICK_CHARGE", override_active=False) is False
    assert uses_start_delay("SMART_CHARGE", override_active=True) is False


def test_guardrails_bypassed_for_quick():
    assert bypasses_guardrails("QUICK_CHARGE", override_active=False) is True
    assert bypasses_guardrails("SMART_CHARGE", override_active=False) is False


def test_price_optimization_modes():
    assert uses_price_optimization("SMART_CHARGE", override_active=False) is True
    assert uses_price_optimization("PRICE_CHARGE", override_active=False) is True
    assert uses_price_optimization("QUICK_CHARGE", override_active=False) is False
    assert uses_price_optimization("SMART_CHARGE", override_active=True) is False


def test_price_mode_ignores_schedule_constraints():
    assert ignores_schedule_constraints("PRICE_CHARGE") is True
    assert ignores_schedule_constraints("SMART_CHARGE") is False


def test_decision_policy_mode():
    assert decision_policy_mode("SMART_CHARGE", override_active=False) == "SMART_CHARGE"
    assert decision_policy_mode("PAUSED", override_active=True) == "override"
