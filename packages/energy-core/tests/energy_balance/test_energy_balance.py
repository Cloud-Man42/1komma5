"""Energy balance engine scenarios."""

from datetime import UTC, datetime

from energy_core.chargers.meter_adapter import MeterSnapshot
from energy_core.energy.state import EnergyState
from energy_core.energy_balance.correlation import correlate_telemetry
from energy_core.energy_balance.engine import EnergyBalanceEngine
from energy_core.energy_balance.types import EnergyBalanceStatus
from energy_core.sungrow.types import SungrowTelemetrySnapshot


def _snap(**kwargs) -> SungrowTelemetrySnapshot:
    base = dict(
        recorded_at=datetime(2026, 8, 21, 10, 0, tzinfo=UTC),
        pv_power_w=0,
        pv_energy_today_kwh=None,
        load_power_w=12000,
        grid_import_w=12000,
        grid_export_w=0,
        battery_charge_w=0,
        battery_discharge_w=0,
        battery_soc_pct=50,
        inverter_status="ONLINE",
        data_age_seconds=5,
        fresh=True,
        source="heartbeat",
    )
    base.update(kwargs)
    return SungrowTelemetrySnapshot(**base)


def _halo(power_w: float) -> MeterSnapshot:
    return MeterSnapshot(
        recorded_at=datetime(2026, 8, 21, 10, 0, tzinfo=UTC),
        cumulative_kwh=1,
        power_w=power_w,
        configured_current_a=16,
        actual_charging_current_a=14,
        is_charging=power_w > 0,
        vehicle_connected=True,
        ocpp_status="Charging",
        phase_current_l1_a=14,
        phase_current_l2_a=None,
        phase_current_l3_a=None,
        energy_source="meter",
    )


def test_normal_ev_non_ev_load():
    engine = EnergyBalanceEngine()
    correlated = correlate_telemetry(
        sungrow=_snap(load_power_w=12000),
        halo=_halo(10000),
        virtual_evse=None,
        heartbeat=EnergyState(
            timestamp=datetime(2026, 8, 21, 10, 0, tzinfo=UTC),
            ev_actual_power_w=10000,
            home_consumption_w=12000,
        ),
        max_alignment_age_seconds=10,
    )
    result = engine.calculate(correlated, load_includes_ev_charger=True)
    assert result.non_ev_house_load_w == 2000
    assert result.status == EnergyBalanceStatus.OK


def test_sungrow_unavailable_degraded():
    engine = EnergyBalanceEngine()
    correlated = correlate_telemetry(
        sungrow=None,
        halo=_halo(5000),
        virtual_evse=None,
        heartbeat=EnergyState(timestamp=datetime(2026, 8, 21, 10, 0, tzinfo=UTC)),
        max_alignment_age_seconds=10,
    )
    result = engine.calculate(correlated, load_includes_ev_charger=True)
    assert result.status == EnergyBalanceStatus.DEGRADED
    assert "sungrow_unavailable" in result.flags


def test_alignment_failed_no_derived_metrics():
    engine = EnergyBalanceEngine()
    correlated = correlate_telemetry(
        sungrow=_snap(),
        halo=MeterSnapshot(
            recorded_at=datetime(2026, 8, 21, 10, 1, tzinfo=UTC),
            cumulative_kwh=1,
            power_w=10000,
            configured_current_a=16,
            actual_charging_current_a=14,
            is_charging=True,
            vehicle_connected=True,
            ocpp_status="Charging",
            phase_current_l1_a=14,
            phase_current_l2_a=None,
            phase_current_l3_a=None,
            energy_source="meter",
        ),
        virtual_evse=None,
        heartbeat=EnergyState(timestamp=datetime(2026, 8, 21, 10, 0, tzinfo=UTC)),
        max_alignment_age_seconds=10,
    )
    result = engine.calculate(correlated, load_includes_ev_charger=True)
    assert result.status == EnergyBalanceStatus.ALIGNMENT_FAILED
    assert result.residual_w is None
    assert result.non_ev_house_load_w is None


def test_sungrow_stale_degraded():
    engine = EnergyBalanceEngine()
    correlated = correlate_telemetry(
        sungrow=_snap(fresh=False, data_age_seconds=120),
        halo=_halo(10000),
        virtual_evse=None,
        heartbeat=EnergyState(timestamp=datetime(2026, 8, 21, 10, 0, tzinfo=UTC)),
        max_alignment_age_seconds=10,
    )
    result = engine.calculate(correlated, load_includes_ev_charger=True)
    assert result.status == EnergyBalanceStatus.DEGRADED
    assert "sungrow_stale" in result.flags
