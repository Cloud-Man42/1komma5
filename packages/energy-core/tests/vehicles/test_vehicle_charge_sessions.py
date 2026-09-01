"""Tests for vehicle charge session lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from energy_core.chargers.meter_adapter import MeterSnapshot
from energy_core.db.models import VehicleStateLatestModel
from energy_core.vehicles.charging_intelligence.service import ChargingSessionService
from energy_core.vehicles.sessions.constants import SOC_TO_KWH_FACTOR, estimate_battery_delta_kwh
from energy_core.vehicles.sessions.session_service import VehicleChargeSessionService


def _csi() -> ChargingSessionService:
    return ChargingSessionService()


def _latest(*, plugged: bool, charging: bool, soc: float = 50.0) -> VehicleStateLatestModel:
    return VehicleStateLatestModel(
        vehicle_id=1,
        state_of_charge_percent=soc,
        target_soc_percent=80.0,
        is_plugged_in=plugged,
        is_charging=charging,
        connection_state="CONNECTED",
        data_quality="MEASURED",
        last_vehicle_update=datetime(2026, 8, 23, 12, 0, tzinfo=UTC),
    )


def _meter(*, kwh: float, connected: bool = True) -> MeterSnapshot:
    return MeterSnapshot(
        cumulative_kwh=kwh,
        power_w=7400.0 if connected else 0.0,
        vehicle_connected=connected,
        recorded_at=datetime(2026, 8, 23, 12, 0, tzinfo=UTC),
        configured_current_a=16.0,
        actual_charging_current_a=16.0 if connected else 0.0,
        is_charging=connected,
        ocpp_status="Charging" if connected else "Available",
        phase_current_l1_a=16.0 if connected else 0.0,
        phase_current_l2_a=None,
        phase_current_l3_a=None,
        energy_source="meter",
    )


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (40.0, 55.0, 15.0 * SOC_TO_KWH_FACTOR),
        (40.0, 40.0, None),
        (None, 55.0, None),
    ],
)
def test_estimate_battery_delta_kwh(start, end, expected):
    assert estimate_battery_delta_kwh(start, end) == expected


@pytest.mark.asyncio
async def test_session_start_on_plug_in(monkeypatch):
    service = VehicleChargeSessionService()
    db = AsyncMock()
    repo = AsyncMock()
    repo.get_active_for_vehicle = AsyncMock(return_value=None)
    created = MagicMock(id=10)
    repo.create = AsyncMock(return_value=created)
    ev_repo = AsyncMock()
    ev_repo.get_active_for_charger = AsyncMock(return_value=None)

    vehicle = MagicMock(id=1)
    charger = MagicMock(id=2)
    site = MagicMock(id=3)

    monkeypatch.setattr(
        "energy_core.vehicles.sessions.session_service.VehicleChargeSessionRepository",
        lambda _session: repo,
    )
    monkeypatch.setattr(
        "energy_core.vehicles.sessions.session_service.EvChargingSessionRepository",
        lambda _session: ev_repo,
    )
    session_id = await service.process_vehicle(
        db,
        vehicle=vehicle,
        charger=charger,
        site=site,
        latest=_latest(plugged=True, charging=False, soc=42.0),
        meter=_meter(kwh=100.0),
        identification_confidence=0.9,
        csi=_csi(),
    )

    assert session_id == 10
    repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_session_complete_on_unplug(monkeypatch):
    service = VehicleChargeSessionService()
    runtime = service.get_runtime_state(1)
    runtime.last_plugged_in = True
    runtime.last_meter_kwh = 100.0

    active = MagicMock(
        id=10,
        vehicle_id=1,
        meter_start_kwh=100.0,
        start_soc=40.0,
        charging_started_at=datetime(2026, 8, 23, 11, 0, tzinfo=UTC),
        charging_stopped_at=None,
        ev_charging_session_id=None,
    )
    repo = AsyncMock()
    repo.get_active_for_vehicle = AsyncMock(return_value=active)
    repo.update_charging_timestamps = AsyncMock()
    repo.update_csi_fields = AsyncMock()
    repo.complete = AsyncMock()
    interval_repo = AsyncMock()
    interval_repo.list_for_session = AsyncMock(return_value=[])

    vehicle = MagicMock(id=1)
    charger = MagicMock(id=2)
    site = MagicMock(id=3)
    db = AsyncMock()

    monkeypatch.setattr(
        "energy_core.vehicles.sessions.session_service.VehicleChargeSessionRepository",
        lambda _session: repo,
    )
    monkeypatch.setattr(
        "energy_core.vehicles.sessions.session_service.VehicleChargingIntervalRepository",
        lambda _session: interval_repo,
    )
    session_id = await service.process_vehicle(
        db,
        vehicle=vehicle,
        charger=charger,
        site=site,
        latest=_latest(plugged=False, charging=False, soc=55.0),
        meter=_meter(kwh=112.5, connected=False),
        identification_confidence=0.9,
        csi=_csi(),
    )

    assert session_id == 10
    repo.complete.assert_awaited_once()
    kwargs = repo.complete.await_args.kwargs
    assert kwargs["end_soc"] == 55.0
    assert kwargs["estimated_battery_energy_delta_kwh"] == pytest.approx(15.0 * SOC_TO_KWH_FACTOR)


@pytest.mark.asyncio
async def test_orphaned_active_session_closes_without_unplug_transition(monkeypatch):
    service = VehicleChargeSessionService()
    runtime = service.get_runtime_state(1)
    runtime.last_plugged_in = True

    active = MagicMock(
        id=10,
        vehicle_id=1,
        meter_start_kwh=100.0,
        start_soc=40.0,
        charging_started_at=datetime(2026, 8, 23, 11, 0, tzinfo=UTC),
        charging_stopped_at=None,
        ev_charging_session_id=None,
    )
    repo = AsyncMock()
    repo.get_active_for_vehicle = AsyncMock(return_value=active)
    repo.update_csi_fields = AsyncMock()
    repo.complete = AsyncMock()
    interval_repo = AsyncMock()
    interval_repo.list_for_session = AsyncMock(return_value=[])

    vehicle = MagicMock(id=1)
    charger = MagicMock(id=2)
    site = MagicMock(id=3)
    db = AsyncMock()

    monkeypatch.setattr(
        "energy_core.vehicles.sessions.session_service.VehicleChargeSessionRepository",
        lambda _session: repo,
    )
    monkeypatch.setattr(
        "energy_core.vehicles.sessions.session_service.VehicleChargingIntervalRepository",
        lambda _session: interval_repo,
    )

    await service.process_vehicle(
        db,
        vehicle=vehicle,
        charger=charger,
        site=site,
        latest=_latest(plugged=False, charging=False, soc=55.0),
        meter=_meter(kwh=100.0, connected=False),
        identification_confidence=0.9,
        csi=_csi(),
    )

    repo.complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_sampler_skips_when_ev_session_linked():
    from energy_core.vehicles.sessions.sampler import VehicleChargeSessionSampler

    service = AsyncMock()
    service.get_runtime_state = MagicMock(return_value=MagicMock(last_sample_at=None, last_meter_kwh=None))
    sampler = VehicleChargeSessionSampler(service)
    session_repo = AsyncMock()
    session_repo.get_active_for_vehicle = AsyncMock(
        return_value=MagicMock(id=1, connected_at=datetime(2026, 8, 23, 10, 0, tzinfo=UTC), ev_charging_session_id=99)
    )

    db = AsyncMock()
    import energy_core.vehicles.sessions.sampler as sampler_mod

    original = sampler_mod.VehicleChargeSessionRepository
    sampler_mod.VehicleChargeSessionRepository = lambda _s: session_repo
    try:
        await sampler.sample_active_session(
            db,
            vehicle=MagicMock(id=1),
            charger=MagicMock(id=2),
            site=MagicMock(id=3),
            meter=_meter(kwh=10.0),
            energy_sample=MagicMock(ev_power_w=7000),
            is_sqlite=True,
            is_charging=True,
        )
    finally:
        sampler_mod.VehicleChargeSessionRepository = original

    session_repo.get_active_for_vehicle.assert_awaited_once()
