"""Tests for spa shadow mode."""

from datetime import UTC, datetime

import pytest

from energy_core.spa_energy.shadow import SpaShadowModeAnalyzer


def test_shadow_comparison():
    result = SpaShadowModeAnalyzer().compare(
        actual_by_day={"2026-08-25": (5.0, 38.4)},
        optimized_by_day={"2026-08-25": (5.0, 21.7)},
        shadow_mode_active=True,
        period_start=datetime(2026, 8, 20, tzinfo=UTC),
        period_end=datetime(2026, 8, 26, tzinfo=UTC),
    )
    assert result.total_actual_cost_sek == 38.4
    assert result.total_optimized_cost_sek == 21.7
    assert result.total_potential_saving_sek == pytest.approx(16.7, rel=0.01)
