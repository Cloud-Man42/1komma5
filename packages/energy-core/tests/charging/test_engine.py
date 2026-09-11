"""Tests for SmartChargingEngine."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from energy_core.charging.engine import SmartChargingEngine, _clamp_config_to_capabilities
from energy_core.charging.config import ChargingConfig
from energy_core.chargers.capabilities import ChargerCapabilities
from energy_core.db.models import EvChargerModel


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
    )
    for key, value in overrides.items():
        setattr(charger, key, value)
    return charger


@pytest.mark.asyncio
async def test_get_bridge_status_defaults_without_runtime():
    engine = SmartChargingEngine()
    status = await engine.get_bridge_status(_charger())
    assert status.charger_id == 1
    assert status.charging_mode == "SMART_CHARGE"
    assert status.active_policy == "SMART_CHARGE"
    assert status.discovery_hints == ()


@pytest.mark.asyncio
async def test_clamp_config_to_capabilities():
    adapter = AsyncMock()
    adapter.get_capabilities.return_value = ChargerCapabilities(
        min_current_a=6.0,
        max_current_a=16.0,
        phases=3,
        supports_current_control=True,
        supports_remote_start_stop=True,
        supports_power_reading=False,
        supports_dynamic_phases=False,
    )
    config = ChargingConfig(max_current_a=32.0, min_current_a=4.0, phases=3)
    clamped = await _clamp_config_to_capabilities(config, adapter)
    assert clamped.max_current_a == 16.0
    assert clamped.min_current_a == 6.0


@pytest.mark.asyncio
async def test_is_due_respects_update_interval():
    engine = SmartChargingEngine()
    now = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)
    charger = _charger(update_interval_seconds=60, last_bridge_run_at=now)
    assert engine._is_due(charger, now) is False
    assert engine._is_due(charger, now.replace(minute=1)) is True


@pytest.mark.asyncio
async def test_run_cycle_continues_without_heartbeat_client_degraded():
    engine = SmartChargingEngine()
    session = AsyncMock()
    charger = _charger()
    site = MagicMock()
    site.id = 1
    site.slug = "akarp"
    site.external_system_id = "sys-1"
    site.timezone = "Europe/Stockholm"
    site.main_fuse_a = 25.0
    site.safety_margin_a = 2.0
    with patch("energy_core.charging.engine.resolve_energy_state_provider", AsyncMock(return_value=None)):
        with patch.object(engine, "_list_active_chargers", AsyncMock(return_value=[(charger, site)])):
            with patch.object(engine, "_is_due", return_value=True):
                with patch.object(engine, "_run_charger_cycle", AsyncMock()) as run_one:
                    processed = await engine.run_cycle(session)
    assert processed == 1
    run_one.assert_awaited_once()
    session.commit.assert_awaited_once()


def test_degraded_energy_state_marks_stale_without_heartbeat():
    now = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)
    from energy_core.charging.engine import _degraded_energy_state

    charger = _charger(
        last_heartbeat_data_at=datetime(2026, 8, 18, 11, 30, tzinfo=UTC),
        charging_mode="SMART_CHARGE",
    )
    energy = _degraded_energy_state(charger, now=now)
    assert energy.stale is True
    assert energy.heartbeat_charging_mode == "SMART_CHARGE"
    assert energy.data_age_seconds == 30 * 60


@pytest.mark.asyncio
async def test_run_charger_cycle_skips_heartbeat_provider_when_client_none():
    engine = SmartChargingEngine()
    session = AsyncMock()
    session.bind = MagicMock(dialect=MagicMock(name="sqlite"))
    charger = _charger(external_charger_id="ext-1", chargeamps_api_key="")
    site = MagicMock()
    site.id = 1
    site.slug = "akarp"
    site.external_system_id = "sys-1"
    site.timezone = "Europe/Stockholm"
    site.main_fuse_a = 25.0
    site.safety_margin_a = 2.0
    now = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)

    from energy_core.platform.modules.resolver import CanStartResult
    from energy_core.platform.modules.site_modules import SiteModuleResolver

    with patch("energy_core.platform.modules.gating.is_module_runtime_active", AsyncMock(return_value=True)):
        with patch.object(SiteModuleResolver, "is_module_active", AsyncMock(return_value=True)):
            with patch.object(
                SiteModuleResolver,
                "can_start_module",
                AsyncMock(return_value=CanStartResult(can_start=True)),
            ):
                with patch(
                    "energy_core.charging.engine.resolve_energy_state_provider",
                    AsyncMock(return_value=None),
                ) as resolve_provider:
                    with patch(
                        "energy_core.charging.engine.enrich_energy_import_prices",
                        AsyncMock(side_effect=lambda _s, _site, energy, **_k: energy),
                    ):
                        with patch("energy_core.charging.engine.resolve_vehicle_charging_context", AsyncMock(return_value=None)):
                            with patch(
                                "energy_core.charging.engine.apply_vehicle_charging_context",
                                side_effect=lambda _c, energy, config, _v: (energy, config),
                            ):
                                with patch.object(engine, "_ensure_runtime", AsyncMock(return_value=MagicMock())):
                                    with patch.object(engine, "_read_meter", AsyncMock(return_value=None)):
                                        with patch.object(engine, "_build_solar_plan", AsyncMock(return_value=None)):
                                            with patch("energy_core.charging.engine.LegacyControlBridge") as bridge_cls:
                                                with patch("energy_core.charging.engine.ChargingCommandController") as command_cls:
                                                    adapter = AsyncMock()
                                                    adapter.get_status.return_value = MagicMock(
                                                        connected=True,
                                                        vehicle_connected=False,
                                                        charging=False,
                                                        current_limit_a=16.0,
                                                    )
                                                    adapter.get_capabilities.return_value = ChargerCapabilities(
                                                        min_current_a=6.0,
                                                        max_current_a=16.0,
                                                        phases=3,
                                                        supports_current_control=True,
                                                        supports_remote_start_stop=True,
                                                        supports_power_reading=False,
                                                        supports_dynamic_phases=False,
                                                    )
                                                    bridge_cls.return_value = adapter
                                                    command_cls.return_value.apply = AsyncMock(
                                                        return_value=MagicMock(
                                                            applied=False,
                                                            applied_current_a=0.0,
                                                            error_code=None,
                                                            charger_status=None,
                                                        )
                                                    )
                                                    runtime = MagicMock()
                                                    runtime.signal_filter.update.return_value = (None, MagicMock())
                                                    runtime.optimizer.optimize_target.return_value = MagicMock(
                                                        target_current_a=0.0,
                                                        reason="idle",
                                                    )
                                                    runtime.smart_runtime.state.value = "idle"
                                                    runtime.smart_runtime.externally_limited = False
                                                    runtime.smart_runtime.requested_current_a = 0.0
                                                    engine._ensure_runtime = AsyncMock(return_value=runtime)
                                                    await engine._run_charger_cycle(session, charger, site, now=now)

                    resolve_provider.assert_awaited_once()
