"""Golden decision tests for smart charging modes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from energy_core.charging.config import ChargingConfig
from energy_core.charging.optimizer import EvChargingOptimizer
from energy_core.energy.state import EnergyState


def _state(**kwargs) -> EnergyState:
    base = dict(timestamp=datetime(2026, 9, 3, 22, 0, tzinfo=UTC), import_price_sek_kwh=1.5)
    base.update(kwargs)
    return EnergyState(**base)


def _config(**kwargs) -> ChargingConfig:
    defaults = {
        "max_current_a": 16.0,
        "min_current_a": 6.0,
        "solar_start_threshold_w": 1500.0,
        "solar_stop_threshold_w": 800.0,
        "solar_start_delay_seconds": 0.0,
        "solar_stop_delay_seconds": 0.0,
    }
    defaults.update(kwargs)
    return ChargingConfig(**defaults)


def test_golden_paused_mode():
    decision = EvChargingOptimizer().optimize(
        _state(),
        config=_config(),
        charging_mode="PAUSED",
    )
    assert decision.requested_current_a == 0
    assert decision.reason == "user_paused"


def test_golden_quick_charge():
    decision = EvChargingOptimizer().optimize(
        _state(grid_import_w=11000),
        config=_config(),
        charging_mode="QUICK_CHARGE",
    )
    assert decision.requested_current_a > 0
    assert decision.reason == "quick_charge"


def test_golden_price_charge():
    now = datetime(2026, 9, 3, 22, 0, tzinfo=UTC)
    decision = EvChargingOptimizer().optimize(
        _state(
            import_price_sek_kwh=0.5,
            import_price_forecast=((now + timedelta(hours=1), 0.3),),
        ),
        config=_config(),
        charging_mode="PRICE_CHARGE",
    )
    assert decision.requested_current_a >= 0


def test_golden_solar_charge():
    decision = EvChargingOptimizer().optimize(
        _state(pv_power_w=5000, grid_export_w=2000, grid_import_w=0, home_consumption_w=1000),
        config=_config(),
        charging_mode="SOLAR_CHARGE",
    )
    assert decision.requested_current_a >= 0


def test_golden_smart_charge():
    decision = EvChargingOptimizer().optimize(
        _state(
            pv_power_w=3000,
            import_price_sek_kwh=1.2,
            target_soc=80,
            ev_soc=50,
            deadline_at=datetime(2026, 9, 4, 7, 0, tzinfo=UTC),
        ),
        config=_config(),
        charging_mode="SMART_CHARGE",
    )
    assert decision.requested_current_a >= 0
