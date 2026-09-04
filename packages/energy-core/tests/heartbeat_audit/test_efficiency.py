"""Tests for Heartbeat efficiency formula."""

from energy_core.heartbeat_audit.efficiency import compute_heartbeat_efficiency_pct


def test_efficiency_formula():
    pct = compute_heartbeat_efficiency_pct(
        heartbeat_saving_sek=30.0,
        baseline_cost_sek=100.0,
        emic_theoretical_optimal_cost_sek=50.0,
    )
    assert pct == 37.5


def test_efficiency_none_when_denominator_zero():
    assert (
        compute_heartbeat_efficiency_pct(
            heartbeat_saving_sek=0.0,
            baseline_cost_sek=50.0,
            emic_theoretical_optimal_cost_sek=50.0,
        )
        is None
    )


def test_efficiency_zero_when_no_saving():
    assert (
        compute_heartbeat_efficiency_pct(
            heartbeat_saving_sek=0.0,
            baseline_cost_sek=100.0,
            emic_theoretical_optimal_cost_sek=60.0,
        )
        == 0.0
    )
