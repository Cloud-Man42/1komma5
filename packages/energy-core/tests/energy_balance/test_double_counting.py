"""Double counting detection tests."""

from datetime import UTC, datetime

from energy_core.chargers.meter_adapter import MeterSnapshot
from energy_core.energy.state import EnergyState
from energy_core.energy_balance.correlation import correlate_telemetry
from energy_core.energy_balance.engine import EnergyBalanceEngine
from energy_core.energy_balance.types import EnergyBalanceStatus
from energy_core.sungrow.types import SungrowTelemetrySnapshot


def _scenario(*, load: float, halo: float, heartbeat_home: float):
    ts = datetime(2026, 8, 21, 10, 0, tzinfo=UTC)
    sungrow = SungrowTelemetrySnapshot(
        recorded_at=ts,
        pv_power_w=0,
        pv_energy_today_kwh=None,
        load_power_w=load,
        grid_import_w=load,
        grid_export_w=0,
        battery_charge_w=0,
        battery_discharge_w=0,
        battery_soc_pct=50,
        inverter_status="ONLINE",
        data_age_seconds=1,
        fresh=True,
        source="heartbeat",
    )
    meter = MeterSnapshot(
        recorded_at=ts,
        cumulative_kwh=1,
        power_w=halo,
        configured_current_a=16,
        actual_charging_current_a=14,
        is_charging=True,
        vehicle_connected=True,
        ocpp_status="Charging",
        phase_current_l1_a=14,
        phase_current_l2_a=None,
        phase_current_l3_a=None,
        energy_source="meter",
    )
    heartbeat = EnergyState(timestamp=ts, home_consumption_w=heartbeat_home, ev_actual_power_w=halo)
    return correlate_telemetry(
        sungrow=sungrow,
        halo=meter,
        virtual_evse=None,
        heartbeat=heartbeat,
        max_alignment_age_seconds=10,
    )


def test_double_counting_suspected():
    engine = EnergyBalanceEngine(double_counting_tolerance_w=800)
    result = engine.calculate(_scenario(load=12000, halo=10000, heartbeat_home=22000), load_includes_ev_charger=True)
    assert result.status == EnergyBalanceStatus.POSSIBLE_DOUBLE_COUNTING


def test_no_double_counting():
    engine = EnergyBalanceEngine(double_counting_tolerance_w=800)
    result = engine.calculate(_scenario(load=12000, halo=10000, heartbeat_home=12000), load_includes_ev_charger=True)
    assert result.status == EnergyBalanceStatus.OK
