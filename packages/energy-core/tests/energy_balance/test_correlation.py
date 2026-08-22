"""Tests for telemetry correlation."""

from datetime import UTC, datetime, timedelta

from energy_core.chargers.meter_adapter import MeterSnapshot
from energy_core.energy.state import EnergyState
from energy_core.energy_balance.correlation import correlate_telemetry
from energy_core.sungrow.types import SungrowTelemetrySnapshot
from energy_core.virtual_evse.state import VirtualEvseState, VirtualEvseStatus


def _sungrow(offset_seconds: float = 0) -> SungrowTelemetrySnapshot:
    ts = datetime(2026, 8, 21, 10, 0, 0, tzinfo=UTC) + timedelta(seconds=offset_seconds)
    return SungrowTelemetrySnapshot(
        recorded_at=ts,
        pv_power_w=5000,
        pv_energy_today_kwh=None,
        load_power_w=12000,
        grid_import_w=1000,
        grid_export_w=0,
        battery_charge_w=0,
        battery_discharge_w=0,
        battery_soc_pct=50,
        inverter_status="ONLINE",
        data_age_seconds=0,
        fresh=True,
        source="heartbeat",
    )


def _halo(offset_seconds: float = 0) -> MeterSnapshot:
    ts = datetime(2026, 8, 21, 10, 0, 0, tzinfo=UTC) + timedelta(seconds=offset_seconds)
    return MeterSnapshot(
        recorded_at=ts,
        cumulative_kwh=10.0,
        power_w=10000,
        configured_current_a=16,
        actual_charging_current_a=14,
        is_charging=True,
        vehicle_connected=True,
        ocpp_status="Charging",
        phase_current_l1_a=14,
        phase_current_l2_a=14,
        phase_current_l3_a=14,
        energy_source="meter",
    )


def test_correlation_aligned():
    result = correlate_telemetry(
        sungrow=_sungrow(),
        halo=_halo(),
        virtual_evse=None,
        heartbeat=None,
        max_alignment_age_seconds=10,
    )
    assert result.aligned is True
    assert result.failure_reason is None


def test_correlation_timestamp_mismatch():
    result = correlate_telemetry(
        sungrow=_sungrow(),
        halo=_halo(offset_seconds=30),
        virtual_evse=None,
        heartbeat=None,
        max_alignment_age_seconds=10,
    )
    assert result.aligned is False
    assert result.failure_reason == "timestamp_mismatch"
