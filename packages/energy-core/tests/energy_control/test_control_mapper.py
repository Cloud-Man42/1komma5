"""Tests for strategy-to-action mapping."""

from datetime import UTC, datetime

from energy_core.energy_control.mapper import action_from_strategy
from energy_core.energy_optimizer.types import EnergyAction
from energy_core.price_engine.strategy import EnergyStrategySnapshot
from energy_core.price_engine.types import OptimizationMode, PriceQuality, StrategyState


def _snapshot(**kwargs) -> EnergyStrategySnapshot:
    defaults = {
        "site_slug": "akarp",
        "period_start": datetime(2026, 9, 2, 8, 0, tzinfo=UTC),
        "market_price_sek_kwh": 0.3,
        "import_price_sek_kwh": 1.2,
        "export_price_sek_kwh": 0.4,
        "market_quality": PriceQuality.REAL,
        "import_quality": PriceQuality.REAL,
        "export_quality": PriceQuality.REAL,
        "battery_soc_pct": 70.0,
        "strategy_state": StrategyState.NORMAL_SELF_USE,
        "confidence": 0.7,
        "reason": "test",
        "reason_sv": "test",
        "next_peak_at": None,
        "next_peak_import_sek_kwh": None,
        "optimization_mode": OptimizationMode.MONITOR_ONLY,
        "expected_saving_today_sek": None,
        "recommended_reserve_soc_pct": None,
    }
    defaults.update(kwargs)
    return EnergyStrategySnapshot(**defaults)


def test_action_from_recommended_action():
    snap = _snapshot(recommended_action="STORE_IN_BATTERY")
    assert action_from_strategy(snap) == EnergyAction.STORE_IN_BATTERY


def test_action_from_strategy_state():
    snap = _snapshot(strategy_state=StrategyState.CHARGE_VEHICLE)
    assert action_from_strategy(snap) == EnergyAction.USE_NOW
