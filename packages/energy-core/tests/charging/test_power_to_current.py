"""Tests for power_to_current conversion."""

from energy_core.charging.power_to_current import power_to_current_a


def test_power_to_current_three_phase():
    # 5500 W @ 230 V 3-phase ≈ 13.8 A, clamped to max 16
    current = power_to_current_a(
        5500,
        phases=3,
        nominal_voltage_v=230,
        min_current_a=6,
        max_current_a=16,
    )
    assert 13.0 <= current <= 14.5


def test_max_current_clamp():
    current = power_to_current_a(
        20000,
        phases=3,
        nominal_voltage_v=230,
        min_current_a=6,
        max_current_a=16,
    )
    assert current == 16.0


def test_min_current_pause():
    current = power_to_current_a(
        500,
        phases=3,
        nominal_voltage_v=230,
        min_current_a=6,
        max_current_a=16,
    )
    assert current == 0.0


def test_zero_target_stops():
    assert power_to_current_a(0, phases=3, nominal_voltage_v=230) == 0.0
    assert power_to_current_a(-100, phases=3, nominal_voltage_v=230) == 0.0
