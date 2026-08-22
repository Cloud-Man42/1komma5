"""Virtual EVSE SEMP reporting tests."""

from datetime import UTC, datetime

from energy_core.chargers.meter_adapter import MeterSnapshot
from energy_core.virtual_evse.device_profile import VirtualEvseDeviceProfile
from energy_core.virtual_evse.reporter import meter_to_virtual_evse_state
from energy_core.virtual_evse.semp_payloads import build_device_status


def test_semp_reports_halo_power():
    profile = VirtualEvseDeviceProfile.for_charger(1)
    meter = MeterSnapshot(
        recorded_at=datetime(2026, 8, 21, 10, 0, tzinfo=UTC),
        cumulative_kwh=12.5,
        power_w=10200,
        configured_current_a=16,
        actual_charging_current_a=15,
        is_charging=True,
        vehicle_connected=True,
        ocpp_status="Charging",
        phase_current_l1_a=15,
        phase_current_l2_a=15,
        phase_current_l3_a=15,
        energy_source="meter",
    )
    state = meter_to_virtual_evse_state(profile, meter, heartbeat_ev_power_w=10000)
    payload = build_device_status(state)
    assert payload["status"] == "Charging"
    assert payload["powerConsumption"]["powerInfo"][0]["averagePower"] == 10200
    assert state.heartbeat_detected is True


def test_heartbeat_detected_when_idle_ev_power_is_zero():
    profile = VirtualEvseDeviceProfile.for_charger(1)
    meter = MeterSnapshot(
        recorded_at=datetime(2026, 8, 21, 10, 0, tzinfo=UTC),
        cumulative_kwh=12.5,
        power_w=0,
        configured_current_a=6,
        actual_charging_current_a=0,
        is_charging=False,
        vehicle_connected=False,
        ocpp_status="Available",
        phase_current_l1_a=0,
        phase_current_l2_a=0,
        phase_current_l3_a=0,
        energy_source="meter",
    )
    state = meter_to_virtual_evse_state(profile, meter, heartbeat_ev_power_w=0.0)
    assert state.heartbeat_detected is True
