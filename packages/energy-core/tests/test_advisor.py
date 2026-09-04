"""Tests for Battery Opportunity Advisor."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.energy_optimizer.advisor import build_battery_opportunity_advice
from energy_core.energy_optimizer.types import EnergyAction
from energy_core.price_engine.strategy import EnergyStrategySnapshot
from energy_core.price_engine.types import OptimizationMode, PriceQuality, StrategyState


def _snapshot(**overrides) -> EnergyStrategySnapshot:
    base = dict(
        site_slug="akarp",
        period_start=datetime(2026, 3, 1, 12, tzinfo=UTC),
        market_price_sek_kwh=0.45,
        import_price_sek_kwh=1.2,
        export_price_sek_kwh=0.35,
        market_quality=PriceQuality.REAL,
        import_quality=PriceQuality.REAL,
        export_quality=PriceQuality.REAL,
        battery_soc_pct=55.0,
        strategy_state=StrategyState.SAVE_BATTERY,
        confidence=0.82,
        reason="Store surplus in battery before evening peak.",
        reason_sv="Spara överskott i batteriet inför kvällstoppen.",
        next_peak_at=datetime(2026, 3, 1, 18, tzinfo=UTC),
        next_peak_import_sek_kwh=2.1,
        optimization_mode=OptimizationMode.MONITOR_ONLY,
        expected_saving_today_sek=12.5,
        recommended_reserve_soc_pct=30.0,
        recommended_action=EnergyAction.STORE_IN_BATTERY.value,
        eov_value_sek_kwh=0.18,
        grid_surcharge_sek_kwh=0.05,
        fuse_headroom_a=None,
        fuse_utilization_pct=None,
    )
    base.update(overrides)
    return EnergyStrategySnapshot(**base)


def test_build_advice_available_with_store_action() -> None:
    advice = build_battery_opportunity_advice(_snapshot())
    assert advice.available is True
    assert advice.monitor_only is True
    assert advice.action == EnergyAction.STORE_IN_BATTERY.value
    assert advice.action_label_sv == "Spara i batteriet"
    assert advice.headline_sv == "Spara i batteriet"
    assert advice.expected_value_sek_kwh == 0.18


def test_build_advice_unavailable_without_import_price() -> None:
    advice = build_battery_opportunity_advice(_snapshot(import_price_sek_kwh=None))
    assert advice.available is False
    assert advice.unavailable_reason_sv is not None
    assert "Importpris" in advice.unavailable_reason_sv


def test_build_advice_unavailable_without_battery_soc() -> None:
    advice = build_battery_opportunity_advice(_snapshot(battery_soc_pct=None))
    assert advice.available is False
    assert advice.unavailable_reason_sv is not None
    assert "SOC" in advice.unavailable_reason_sv


def test_build_advice_peak_protection_headline() -> None:
    advice = build_battery_opportunity_advice(
        _snapshot(
            strategy_state=StrategyState.PEAK_PROTECTION,
            recommended_action=EnergyAction.WAIT.value,
            reason_sv="Toppskydd aktivt — begränsa effektupptag.",
        )
    )
    assert advice.available is True
    assert advice.headline_sv == "Toppskydd — begränsa effektupptag"
