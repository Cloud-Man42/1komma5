"""Tests for energy control service sync."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from energy_core.energy_control.service import EnergyControlService
from energy_core.energy_control.types import ControlOutcome
from energy_core.energy_optimizer.types import EnergyAction
from energy_core.price_engine.strategy import EnergyStrategySnapshot
from energy_core.price_engine.types import OptimizationMode, PriceQuality, StrategyState


def _snapshot(**overrides) -> EnergyStrategySnapshot:
    base = dict(
        site_slug="akarp",
        period_start=datetime(2026, 9, 4, 8, tzinfo=UTC),
        market_price_sek_kwh=0.4,
        import_price_sek_kwh=1.1,
        export_price_sek_kwh=0.35,
        market_quality=PriceQuality.REAL,
        import_quality=PriceQuality.REAL,
        export_quality=PriceQuality.REAL,
        battery_soc_pct=60.0,
        strategy_state=StrategyState.SAVE_BATTERY,
        confidence=0.7,
        reason="test",
        reason_sv="test",
        next_peak_at=None,
        next_peak_import_sek_kwh=None,
        optimization_mode=OptimizationMode.MONITOR_ONLY,
        expected_saving_today_sek=None,
        recommended_reserve_soc_pct=None,
        recommended_action=EnergyAction.STORE_IN_BATTERY.value,
    )
    base.update(overrides)
    return EnergyStrategySnapshot(**base)


def _site(**overrides):
    site = MagicMock()
    site.id = 1
    site.optimization_mode = OptimizationMode.MONITOR_ONLY.value
    site.energy_control_enabled = False
    for key, value in overrides.items():
        setattr(site, key, value)
    return site


@pytest.mark.asyncio
async def test_sync_from_strategy_skips_monitor_only() -> None:
    session = AsyncMock()
    service = EnergyControlService(session)
    result = await service.sync_from_strategy(_site(), _snapshot())
    assert result is None


@pytest.mark.asyncio
async def test_sync_from_strategy_previews_in_recommend_mode() -> None:
    session = AsyncMock()
    service = EnergyControlService(session)
    service._repo.append = AsyncMock()
    site = _site(optimization_mode=OptimizationMode.RECOMMEND.value)
    result = await service.sync_from_strategy(site, _snapshot())
    assert result is not None
    assert result.outcome == ControlOutcome.PREVIEW
    assert result.dry_run is True


@pytest.mark.asyncio
async def test_sync_from_strategy_applies_in_automatic_mode_when_enabled() -> None:
    session = AsyncMock()
    service = EnergyControlService(session)
    service._repo.append = AsyncMock()
    site = _site(
        optimization_mode=OptimizationMode.AUTOMATIC.value,
        energy_control_enabled=True,
    )
    result = await service.sync_from_strategy(site, _snapshot())
    assert result is not None
    assert result.outcome == ControlOutcome.APPLIED
