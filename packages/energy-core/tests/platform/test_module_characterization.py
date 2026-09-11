"""Characterization tests for Step 2 module platform."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from energy_core.charging.engine import SmartChargingEngine
from energy_core.db.models import EvChargerModel, SiteModel
from energy_core.platform.modules.bootstrap import register_default_modules
from energy_core.platform.modules.registry import default_module_registry
from energy_core.platform.modules.resolver import CanStartResult
from energy_core.platform.modules.site_modules import SiteModuleResolver


def _charger(**overrides) -> EvChargerModel:
    charger = EvChargerModel(
        id=1,
        site_id=1,
        name="Halo",
        manufacturer="ChargeAmps",
        model="Halo",
        control_source="chargeamp",
        bridge_enabled=True,
        chargeamp_charger_id="halo-1",
        external_charger_id="ext-1",
        charging_mode="SMART_CHARGE",
        max_current_a=16.0,
        min_current_a=6.0,
        phases=3,
        nominal_voltage_v=230.0,
        solar_start_delay_seconds=30,
        solar_stop_delay_seconds=60,
        start_delay_seconds=120,
        stop_delay_seconds=300,
        minimum_run_time_seconds=300,
        minimum_off_time_seconds=300,
        temporary_grid_import_seconds=600,
        minimum_current_change_interval_seconds=30,
        stale_timeout_seconds=120,
        update_interval_seconds=30,
        solar_start_threshold_w=1500.0,
        solar_stop_threshold_w=800.0,
        grid_deadband_w=300.0,
        max_automatic_starts_per_hour=4,
        chargeamps_api_key="",
    )
    for key, value in overrides.items():
        setattr(charger, key, value)
    return charger


@pytest.mark.asyncio
async def test_run_charger_cycle_skips_when_site_module_inactive():
    engine = SmartChargingEngine()
    session = AsyncMock()
    site = MagicMock(spec=SiteModel)
    site.id = 2
    site.slug = "other"
    site.external_system_id = "sys-2"
    charger = _charger(site_id=2)
    now = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)

    with patch.object(SiteModuleResolver, "is_module_active", AsyncMock(return_value=False)):
        with patch("energy_core.charging.engine.enrich_energy_import_prices", AsyncMock()) as enrich:
            await engine._run_charger_cycle(session, charger, site, now=now)
    enrich.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_charger_cycle_skips_when_capabilities_missing():
    engine = SmartChargingEngine()
    session = AsyncMock()
    site = MagicMock(spec=SiteModel)
    site.id = 1
    site.slug = "akarp"
    site.external_system_id = "sys-1"
    charger = _charger()
    now = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)

    blocked = CanStartResult(
        can_start=False,
        missing_required=(__import__("energy_core.platform.capabilities.types", fromlist=["Capability"]).Capability.EV_CHARGER_START,),
    )
    with patch.object(SiteModuleResolver, "is_module_active", AsyncMock(return_value=True)):
        with patch.object(SiteModuleResolver, "can_start_module", AsyncMock(return_value=blocked)):
            with patch("energy_core.charging.engine.enrich_energy_import_prices", AsyncMock()) as enrich:
                await engine._run_charger_cycle(session, charger, site, now=now)
    enrich.assert_not_awaited()


def test_register_default_modules_includes_integration_and_feature_ids():
    default_module_registry.clear()
    register_default_modules()
    module_ids = {module.module_id for module in default_module_registry.list_modules()}
    assert "integration.chargeamps" in module_ids
    assert "feature.smart-charging" in module_ids
    assert "charging" in module_ids
