"""Tests for EV smart charging optimizer."""

from datetime import UTC, datetime, timedelta

from energy_core.charging.config import ChargingConfig
from energy_core.charging.optimizer import EvChargingOptimizer
from energy_core.energy.state import EnergyState


def _state(**kwargs) -> EnergyState:
    defaults = {"timestamp": datetime.now(UTC)}
    defaults.update(kwargs)
    return EnergyState(**defaults)


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


def test_solar_strong_export_increases_charging():
    optimizer = EvChargingOptimizer()
    decision = optimizer.optimize(
        _state(grid_export_w=6000, grid_import_w=0),
        config=_config(),
        charging_mode="SOLAR_CHARGE",
    )
    assert decision.requested_current_a > 0
    assert decision.reason == "stable_grid_export"


def test_solar_grid_import_pauses():
    optimizer = EvChargingOptimizer()
    decision = optimizer.optimize(
        _state(grid_export_w=0, grid_import_w=1200),
        config=_config(),
        charging_mode="SOLAR_CHARGE",
    )
    assert decision.requested_current_a == 0
    assert decision.reason == "grid_import"


def test_solar_ignores_battery_discharge_as_free_solar():
    optimizer = EvChargingOptimizer()
    decision = optimizer.optimize(
        _state(
            grid_export_w=4000,
            grid_import_w=0,
            battery_discharge_power_w=4000,
            pv_power_w=2000,
            home_consumption_w=2000,
        ),
        config=_config(),
        charging_mode="SOLAR_CHARGE",
    )
    assert decision.requested_current_a == 0


def test_smart_waits_for_cheaper_hours():
    optimizer = EvChargingOptimizer()
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    forecast = (
        (now, 0.55),
        (now + timedelta(hours=1), 0.12),
        (now + timedelta(hours=2), 0.15),
        (now + timedelta(hours=3), 0.18),
        (now + timedelta(hours=4), 0.52),
        (now + timedelta(hours=5), 0.48),
    )
    decision = optimizer.optimize(
        _state(
            timestamp=now,
            electricity_price_eur_kwh=0.55,
            price_forecast=forecast,
            departure_time="20:00",
        ),
        config=_config(),
        charging_mode="SMART_CHARGE",
        now=now,
    )
    assert decision.requested_current_a == 0
    assert decision.reason == "smart_wait_cheaper"


def test_deadline_risk_starts_early():
    optimizer = EvChargingOptimizer()
    now = datetime(2026, 8, 14, 6, 0, tzinfo=UTC)
    deadline = now + timedelta(hours=2)
    decision = optimizer.optimize(
        _state(timestamp=now, price_forecast=((now, 0.45),)),
        config=_config(deadline_at=deadline),
        charging_mode="SMART_CHARGE",
        now=now,
    )
    assert decision.requested_current_a > 0
    assert decision.reason == "deadline_risk"


def test_price_charge_ignores_deadline_and_waits_for_cheaper_price():
    optimizer = EvChargingOptimizer()
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    forecast = (
        (now, 0.55),
        (now + timedelta(hours=1), 0.12),
        (now + timedelta(hours=2), 0.15),
        (now + timedelta(hours=3), 0.18),
        (now + timedelta(hours=4), 0.52),
    )
    deadline = now + timedelta(hours=2)
    decision = optimizer.optimize(
        _state(
            timestamp=now,
            price_forecast=forecast,
            electricity_price_eur_kwh=0.55,
        ),
        config=_config(
            deadline_at=deadline,
            departure_time="07:00",
        ),
        charging_mode="PRICE_CHARGE",
        now=now,
    )
    assert decision.requested_current_a == 0
    assert decision.reason == "smart_wait_cheaper"


def test_main_fuse_no_longer_blocks_optimizer():
    optimizer = EvChargingOptimizer()
    decision = optimizer.optimize(
        _state(
            phase_current_l1_a=19,
            phase_current_l2_a=19,
            phase_current_l3_a=19,
            electricity_price_eur_kwh=0.05,
        ),
        config=_config(main_fuse_a=20.0, safety_margin_a=2.0),
        charging_mode="QUICK_CHARGE",
    )
    assert decision.requested_current_a > 0


def test_paused_mode_returns_zero():
    optimizer = EvChargingOptimizer()
    decision = optimizer.optimize(
        _state(grid_export_w=6000),
        config=_config(),
        charging_mode="PAUSED",
    )
    assert decision.requested_current_a == 0
    assert decision.reason == "user_paused"


def test_override_bypasses_paused_mode():
    optimizer = EvChargingOptimizer()
    decision = optimizer.optimize(
        _state(grid_export_w=0, grid_import_w=5000),
        config=_config(),
        charging_mode="PAUSED",
        override_active=True,
    )
    assert decision.requested_current_a == 16.0
    assert decision.reason == "override"


def test_quick_charge_ignores_expensive_price():
    optimizer = EvChargingOptimizer()
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    decision = optimizer.optimize(
        _state(
            timestamp=now,
            electricity_price_eur_kwh=0.99,
            grid_import_w=8000,
        ),
        config=_config(),
        charging_mode="QUICK_CHARGE",
        now=now,
    )
    assert decision.requested_current_a == 16.0
    assert decision.reason == "quick_charge"


def test_stale_data_is_safe():
    optimizer = EvChargingOptimizer()
    decision = optimizer.optimize(
        _state(stale=True),
        config=_config(),
        charging_mode="SMART_CHARGE",
    )
    assert decision.action == "none"
    assert decision.reason == "stale_data"


def test_smart_everyday_mode_charges_at_average_price():
    optimizer = EvChargingOptimizer()
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    forecast = (
        (now, 0.52),
        (now + timedelta(hours=1), 0.54),
        (now + timedelta(hours=2), 0.50),
        (now + timedelta(hours=3), 0.56),
    )
    decision = optimizer.optimize(
        _state(
            timestamp=now,
            electricity_price_eur_kwh=0.52,
            price_forecast=forecast,
        ),
        config=_config(),
        charging_mode="SMART_CHARGE",
        now=now,
    )
    assert decision.requested_current_a > 0
    assert decision.reason == "normal_price_ok"


def test_smart_high_urgency_charges_despite_expensive_hour():
    optimizer = EvChargingOptimizer()
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    deadline = now + timedelta(hours=3)
    forecast = (
        (now, 0.55),
        (now + timedelta(hours=1), 0.12),
        (now + timedelta(hours=2), 0.15),
        (now + timedelta(hours=3), 0.18),
    )
    decision = optimizer.optimize(
        _state(
            timestamp=now,
            electricity_price_eur_kwh=0.55,
            price_forecast=forecast,
        ),
        config=_config(deadline_at=deadline),
        charging_mode="SMART_CHARGE",
        now=now,
    )
    assert decision.requested_current_a > 0
    assert decision.reason == "deadline_risk"


def test_deadline_with_slack_uses_live_price_instead_of_waiting():
    optimizer = EvChargingOptimizer()
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    deadline = now + timedelta(hours=10)
    forecast = (
        (now, 0.40),
        (now + timedelta(hours=1), 0.90),
        (now + timedelta(hours=2), 0.90),
        (now + timedelta(hours=3), 0.90),
    )
    decision = optimizer.optimize(
        _state(
            timestamp=now,
            electricity_price_eur_kwh=0.40,
            price_forecast=forecast,
        ),
        config=_config(deadline_at=deadline),
        charging_mode="SMART_CHARGE",
        now=now,
    )
    assert decision.reason == "cheap_now"
    assert decision.requested_current_a > 0


def test_deadline_far_away_waits_for_cheaper_hours():
    optimizer = EvChargingOptimizer()
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    deadline = now + timedelta(hours=20)
    forecast = (
        (now, 0.90),
        (now + timedelta(hours=1), 0.20),
        (now + timedelta(hours=2), 0.22),
        (now + timedelta(hours=3), 0.24),
        (now + timedelta(hours=4), 0.26),
    )
    decision = optimizer.optimize(
        _state(
            timestamp=now,
            electricity_price_eur_kwh=0.90,
            price_forecast=forecast,
        ),
        config=_config(deadline_at=deadline),
        charging_mode="SMART_CHARGE",
        now=now,
    )
    assert decision.requested_current_a == 0
    assert decision.reason == "smart_wait_cheaper"


def test_deadline_urgency_needs_no_energy_target():
    from energy_core.charging.optimizer import charging_urgency

    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    config = _config()
    assert charging_urgency(now, deadline=None, config=config) == 0.0
    assert charging_urgency(now, deadline=now - timedelta(minutes=1), config=config) == 1.0
    assert charging_urgency(now, deadline=now + timedelta(hours=2), config=config) == 1.0
    assert charging_urgency(now, deadline=now + timedelta(hours=24), config=config) == 0.0
    mid = charging_urgency(now, deadline=now + timedelta(hours=8), config=config)
    assert 0.0 < mid < 1.0


def test_deadline_passed_charges_at_max():
    optimizer = EvChargingOptimizer()
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    decision = optimizer.optimize(
        _state(timestamp=now, electricity_price_eur_kwh=0.99),
        config=_config(deadline_at=now - timedelta(hours=1)),
        charging_mode="SMART_CHARGE",
        now=now,
    )
    assert decision.requested_current_a == 16.0
    assert decision.reason == "deadline_overdue"


def test_smart_prefers_live_solar_surplus_over_deadline_grid_charge():
    optimizer = EvChargingOptimizer()
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    decision = optimizer.optimize(
        _state(
            timestamp=now,
            grid_export_w=5000,
            electricity_price_eur_kwh=0.99,
        ),
        config=_config(deadline_at=now + timedelta(hours=20)),
        charging_mode="SMART_CHARGE",
        now=now,
    )
    assert decision.requested_current_a > 0
    assert decision.reason == "smart_solar_surplus"


def test_solar_starts_at_lower_export_threshold():
    optimizer = EvChargingOptimizer()
    decision = optimizer.optimize(
        _state(grid_export_w=1200, grid_import_w=0),
        config=_config(
            solar_start_delay_seconds=0.0,
            solar_start_threshold_w=1000.0,
            solar_stop_threshold_w=600.0,
            phases=1,
            min_current_a=4.0,
        ),
        charging_mode="SOLAR_CHARGE",
    )
    assert decision.requested_current_a > 0
    assert decision.reason == "stable_grid_export"


def test_solar_export_below_lowered_threshold_still_waits():
    optimizer = EvChargingOptimizer()
    decision = optimizer.optimize(
        _state(grid_export_w=800, grid_import_w=0),
        config=_config(
            solar_start_delay_seconds=0.0,
            solar_start_threshold_w=1000.0,
            solar_stop_threshold_w=600.0,
            phases=1,
            min_current_a=4.0,
        ),
        charging_mode="SOLAR_CHARGE",
    )
    assert decision.requested_current_a == 0
    assert decision.reason == "export_hysteresis"


def test_default_config_uses_balanced_solar_thresholds():
    config = ChargingConfig()
    assert config.solar_start_threshold_w == 1000.0
    assert config.solar_stop_threshold_w == 600.0
    assert config.solar_start_delay_seconds == 15.0


def test_solar_forecast_wait_defers_grid_charging():
    from energy_core.solar_forecast.types import SolarChargingPlan

    optimizer = EvChargingOptimizer()
    plan = SolarChargingPlan(
        expected_usable_solar_kwh=15.0,
        planning_solar_kwh=14.0,
        quality="HIGH",
        confidence=0.9,
        expected_solar_window_start=None,
        expected_solar_window_end=None,
        cheapest_grid_window=None,
        explanation_sv="test",
        reason_code="solar_forecast_wait",
        solar_first=True,
    )
    target = optimizer.optimize_target(
        _state(grid_export_w=0, electricity_price_eur_kwh=0.55, price_forecast=((datetime.now(UTC), 0.55),)),
        config=_config(),
        charging_mode="SMART_CHARGE",
        solar_plan=plan,
    )
    assert target.target_current_a == 0.0
    assert target.reason == "solar_forecast_wait"


def test_solar_forecast_wait_allows_cheap_grid_charging():
    from energy_core.solar_forecast.types import SolarChargingPlan

    optimizer = EvChargingOptimizer()
    plan = SolarChargingPlan(
        expected_usable_solar_kwh=15.0,
        planning_solar_kwh=14.0,
        quality="HIGH",
        confidence=0.9,
        expected_solar_window_start=None,
        expected_solar_window_end=None,
        cheapest_grid_window=None,
        explanation_sv="test",
        reason_code="solar_forecast_wait",
        solar_first=True,
    )
    target = optimizer.optimize_target(
        _state(grid_export_w=0, electricity_price_eur_kwh=0.05),
        config=_config(),
        charging_mode="SMART_CHARGE",
        solar_plan=plan,
    )
    assert target.target_current_a > 0
    assert target.reason == "cheap_now"


def test_little_expected_solar_tops_up_from_grid():
    from energy_core.solar_forecast.types import SolarChargingPlan

    optimizer = EvChargingOptimizer()
    plan = SolarChargingPlan(
        expected_usable_solar_kwh=0.4,
        planning_solar_kwh=0.3,
        quality="LOW",
        confidence=0.3,
        expected_solar_window_start=None,
        expected_solar_window_end=None,
        cheapest_grid_window=None,
        explanation_sv="test",
        reason_code="solar_forecast_grid_required",
        solar_first=False,
    )
    target = optimizer.optimize_target(
        _state(grid_export_w=0, electricity_price_eur_kwh=0.05),
        config=_config(),
        charging_mode="SMART_CHARGE",
        solar_plan=plan,
    )
    assert target.target_current_a > 0
    assert target.reason == "solar_forecast_partial_grid"

