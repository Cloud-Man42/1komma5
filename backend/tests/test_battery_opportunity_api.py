"""API tests for battery opportunity advisor."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
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
        battery_soc_pct=60.0,
        strategy_state=StrategyState.SAVE_BATTERY,
        confidence=0.75,
        reason="Store in battery.",
        reason_sv="Spara i batteriet.",
        next_peak_at=None,
        next_peak_import_sek_kwh=None,
        optimization_mode=OptimizationMode.MONITOR_ONLY,
        expected_saving_today_sek=None,
        recommended_reserve_soc_pct=25.0,
        recommended_action=EnergyAction.STORE_IN_BATTERY.value,
        eov_value_sek_kwh=0.12,
    )
    base.update(overrides)
    return EnergyStrategySnapshot(**base)


@pytest.mark.asyncio
async def test_battery_opportunity_returns_advice(client) -> None:
    ac, _, _ = client
    with patch(
        "energy_core.price_engine.strategy_service.build_current_strategy_for_slug",
        new=AsyncMock(return_value=_snapshot()),
    ):
        res = await ac.get("/api/sites/akarp/battery-opportunity")

    assert res.status_code == 200
    body = res.json()
    assert body["slug"] == "akarp"
    assert body["available"] is True
    assert body["monitor_only"] is True
    assert body["action"] == EnergyAction.STORE_IN_BATTERY.value
    assert body["headline_sv"] == "Spara i batteriet"
    assert body["battery_soc_pct"] == 60.0


@pytest.mark.asyncio
async def test_battery_opportunity_site_not_found(client) -> None:
    ac, _, _ = client
    with patch(
        "energy_core.price_engine.strategy_service.build_current_strategy_for_slug",
        new=AsyncMock(return_value=None),
    ):
        res = await ac.get("/api/sites/missing/battery-opportunity")

    assert res.status_code == 404


@pytest.mark.asyncio
async def test_battery_opportunity_unavailable_when_soc_missing(client) -> None:
    ac, _, _ = client
    with patch(
        "energy_core.price_engine.strategy_service.build_current_strategy_for_slug",
        new=AsyncMock(return_value=_snapshot(battery_soc_pct=None)),
    ):
        res = await ac.get("/api/sites/akarp/battery-opportunity")

    assert res.status_code == 200
    body = res.json()
    assert body["available"] is False
    assert body["unavailable_reason_sv"] is not None
