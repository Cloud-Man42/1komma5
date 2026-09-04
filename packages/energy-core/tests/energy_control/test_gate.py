"""Tests for optimization mode gating."""

from energy_core.energy_control.gate import (
    mode_allows_automatic_apply,
    mode_allows_manual_apply,
    mode_allows_preview,
)
from energy_core.price_engine.types import OptimizationMode


def test_monitor_only_blocks_preview_and_apply():
    assert mode_allows_preview(OptimizationMode.MONITOR_ONLY) is False
    assert mode_allows_manual_apply(OptimizationMode.MONITOR_ONLY, control_enabled=True) is False
    assert mode_allows_automatic_apply(OptimizationMode.MONITOR_ONLY, control_enabled=True) is False


def test_recommend_allows_preview_not_apply():
    assert mode_allows_preview(OptimizationMode.RECOMMEND) is True
    assert mode_allows_manual_apply(OptimizationMode.RECOMMEND, control_enabled=True) is False
    assert mode_allows_automatic_apply(OptimizationMode.RECOMMEND, control_enabled=True) is False


def test_automatic_requires_control_enabled():
    assert mode_allows_manual_apply(OptimizationMode.AUTOMATIC, control_enabled=False) is False
    assert mode_allows_automatic_apply(OptimizationMode.AUTOMATIC, control_enabled=False) is False
    assert mode_allows_manual_apply(OptimizationMode.AUTOMATIC, control_enabled=True) is True
    assert mode_allows_automatic_apply(OptimizationMode.AUTOMATIC, control_enabled=True) is True
