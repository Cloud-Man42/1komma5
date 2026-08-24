"""Tests for SmartChargingEngine."""

from datetime import UTC, datetime
from types import SimpleNamespace
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
async def test_run_cycle_skips_without_heartbeat_client():
    engine = SmartChargingEngine()
    session = AsyncMock()
    with patch("energy_core.charging.engine.create_heartbeat_client", AsyncMock(return_value=None)):
        processed = await engine.run_cycle(session)
    assert processed == 0
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_run_charger_cycle_calls_heartbeat_sync():
    engine = SmartChargingEngine()
    session = AsyncMock()
    client = AsyncMock()
    charger = _charger(
        heartbeat_sync_enabled=True,
        heartbeat_ev_id="ev-1",
        external_charger_id="halo-1",
    )
    site = SimpleNamespace(
        id=1,
        slug="akarp",
        external_system_id="sys-1",
        timezone="Europe/Stockholm",
        main_fuse_a=25,
        safety_margin_a=2,
    )

    sync_mock = AsyncMock(return_value=SimpleNamespace(pushed=False, pulled=True))
    provider_instance = AsyncMock()
    provider_instance.get_energy_state = AsyncMock(side_effect=RuntimeError("stop-after-sync"))
    with (
        patch("energy_core.charging.engine.HeartbeatEvSyncService") as sync_cls,
        patch("energy_core.charging.engine.HeartbeatEnergyProvider", return_value=provider_instance),
    ):
        sync_cls.return_value.sync_charger = sync_mock
        with pytest.raises(RuntimeError, match="stop-after-sync"):
            await engine._run_charger_cycle(
                session,
                client,
                charger,
                site,
                now=datetime(2026, 8, 18, 12, 0, tzinfo=UTC),
            )

    sync_mock.assert_awaited_once_with(charger, site, client=client)
