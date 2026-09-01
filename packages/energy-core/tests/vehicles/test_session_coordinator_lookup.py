"""Tests for ChargeFinder lookup gating in VehicleChargeSessionCoordinator."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from energy_core.integrations.charging_stations.models import StationResolutionStatus
from energy_core.vehicles.sessions.coordinator import VehicleChargeSessionCoordinator


@dataclass
class _FakeResolution:
    station_resolution_status: StationResolutionStatus


@pytest.fixture
def coordinator() -> VehicleChargeSessionCoordinator:
    return VehicleChargeSessionCoordinator()


def _lookup(
    coordinator: VehicleChargeSessionCoordinator,
    vehicle_id: int,
    *,
    is_plugged: bool,
    is_charging: bool,
    last_resolution=None,
) -> bool:
    return coordinator._should_lookup(
        vehicle_id,
        is_plugged=is_plugged,
        is_charging=is_charging,
        last_resolution=last_resolution,
    )


def test_lookup_triggers_on_plug_in_while_parked(coordinator):
    assert _lookup(coordinator, 1, is_plugged=False, is_charging=False) is False
    assert _lookup(coordinator, 1, is_plugged=True, is_charging=False) is True


def test_lookup_does_not_repeat_while_plugged_and_parked(coordinator):
    _lookup(coordinator, 1, is_plugged=True, is_charging=False)
    coordinator._lookup_state[1].lookup_done_for_session = True
    assert _lookup(coordinator, 1, is_plugged=True, is_charging=False) is False


def test_lookup_retries_when_gps_arrives_late_after_plug_in(coordinator):
    _lookup(coordinator, 1, is_plugged=True, is_charging=False)
    assert _lookup(coordinator, 1, is_plugged=True, is_charging=False) is True


def test_lookup_still_triggers_on_charging_start_if_not_done(coordinator):
    _lookup(coordinator, 1, is_plugged=True, is_charging=False)
    assert _lookup(coordinator, 1, is_plugged=True, is_charging=True) is True


def test_lookup_skips_charging_start_when_already_done_at_plug_in(coordinator):
    _lookup(coordinator, 1, is_plugged=True, is_charging=False)
    coordinator._lookup_state[1].lookup_done_for_session = True
    assert _lookup(coordinator, 1, is_plugged=True, is_charging=True) is False


def test_lookup_skips_when_unplugged(coordinator):
    _lookup(coordinator, 1, is_plugged=True, is_charging=False)
    coordinator._lookup_state[1].lookup_done_for_session = True
    assert _lookup(coordinator, 1, is_plugged=False, is_charging=False) is False


def test_lookup_keeps_resolution_until_next_plug_in(coordinator):
    _lookup(coordinator, 1, is_plugged=True, is_charging=False)
    coordinator._lookup_state[1].lookup_done_for_session = True
    coordinator._lookup_state[1].last_resolution = _FakeResolution(StationResolutionStatus.OK)

    assert _lookup(coordinator, 1, is_plugged=False, is_charging=False) is False
    assert coordinator._lookup_state[1].last_resolution is not None
    assert coordinator._lookup_state[1].pending_finalize is True

    assert _lookup(coordinator, 1, is_plugged=True, is_charging=False) is True
    assert coordinator._lookup_state[1].last_resolution is None


def test_uncertain_retry_while_plugged_not_charging(coordinator):
    unknown = _FakeResolution(StationResolutionStatus.UNKNOWN)
    _lookup(coordinator, 1, is_plugged=True, is_charging=False)
    coordinator._lookup_state[1].lookup_done_for_session = True

    assert (
        _lookup(
            coordinator,
            1,
            is_plugged=True,
            is_charging=False,
            last_resolution=unknown,
        )
        is True
    )
    assert (
        _lookup(
            coordinator,
            1,
            is_plugged=True,
            is_charging=False,
            last_resolution=unknown,
        )
        is False
    )


def test_uncertain_retry_for_multiple_candidates(coordinator):
    candidates = _FakeResolution(StationResolutionStatus.MULTIPLE_CANDIDATES)
    _lookup(coordinator, 1, is_plugged=True, is_charging=False)
    coordinator._lookup_state[1].lookup_done_for_session = True

    assert (
        _lookup(
            coordinator,
            1,
            is_plugged=True,
            is_charging=True,
            last_resolution=candidates,
        )
        is True
    )
