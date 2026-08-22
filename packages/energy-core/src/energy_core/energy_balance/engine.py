"""Energy balance calculation engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from energy_core.energy_balance.correlation import CorrelatedTelemetry
from energy_core.energy_balance.types import EnergyBalanceStatus


@dataclass(frozen=True, slots=True)
class EnergyBalanceSnapshot:
    recorded_at: str
    status: EnergyBalanceStatus
    flags: tuple[str, ...]
    sungrow_pv_power_w: float | None
    sungrow_load_power_w: float | None
    sungrow_grid_import_w: float | None
    sungrow_grid_export_w: float | None
    sungrow_battery_charge_w: float | None
    sungrow_battery_discharge_w: float | None
    sungrow_battery_soc_pct: float | None
    sungrow_fresh: bool | None
    sungrow_telemetry_age_seconds: float | None
    halo_power_w: float | None
    virtual_evse_reported_power_w: float | None
    heartbeat_observed_ev_power_w: float | None
    heartbeat_home_consumption_w: float | None
    non_ev_house_load_w: float | None
    non_ev_house_load_reason: str | None
    residual_w: float | None
    alignment_delta_seconds: float | None
    inverter_display_name: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload


class EnergyBalanceEngine:
    def __init__(
        self,
        *,
        residual_warn_w: float = 500.0,
        double_counting_tolerance_w: float = 800.0,
        inverter_display_name: str = "Sungrow Hybrid Inverter SH10",
    ) -> None:
        self._residual_warn_w = residual_warn_w
        self._double_counting_tolerance_w = double_counting_tolerance_w
        self._inverter_display_name = inverter_display_name

    def calculate(
        self,
        correlated: CorrelatedTelemetry,
        *,
        load_includes_ev_charger: bool | None = None,
    ) -> EnergyBalanceSnapshot:
        flags: list[str] = []
        status = EnergyBalanceStatus.OK

        sungrow = correlated.sungrow
        halo = correlated.halo
        virtual_evse = correlated.virtual_evse
        heartbeat = correlated.heartbeat

        if sungrow is not None and not sungrow.fresh:
            status = EnergyBalanceStatus.DEGRADED
            flags.append("sungrow_stale")

        if sungrow is None:
            status = EnergyBalanceStatus.DEGRADED
            flags.append("sungrow_unavailable")

        if not correlated.aligned:
            return EnergyBalanceSnapshot(
                recorded_at=correlated.recorded_at.isoformat(),
                status=EnergyBalanceStatus.ALIGNMENT_FAILED,
                flags=tuple(flags + ["alignment_failed"]),
                sungrow_pv_power_w=sungrow.pv_power_w if sungrow else None,
                sungrow_load_power_w=sungrow.load_power_w if sungrow else None,
                sungrow_grid_import_w=sungrow.grid_import_w if sungrow else None,
                sungrow_grid_export_w=sungrow.grid_export_w if sungrow else None,
                sungrow_battery_charge_w=sungrow.battery_charge_w if sungrow else None,
                sungrow_battery_discharge_w=sungrow.battery_discharge_w if sungrow else None,
                sungrow_battery_soc_pct=sungrow.battery_soc_pct if sungrow else None,
                sungrow_fresh=sungrow.fresh if sungrow else None,
                sungrow_telemetry_age_seconds=sungrow.data_age_seconds if sungrow else None,
                halo_power_w=halo.power_w if halo else None,
                virtual_evse_reported_power_w=virtual_evse.reported_power_w if virtual_evse else None,
                heartbeat_observed_ev_power_w=heartbeat.ev_actual_power_w if heartbeat else None,
                heartbeat_home_consumption_w=heartbeat.home_consumption_w if heartbeat else None,
                non_ev_house_load_w=None,
                non_ev_house_load_reason=correlated.failure_reason,
                residual_w=None,
                alignment_delta_seconds=correlated.alignment_delta_seconds,
                inverter_display_name=self._inverter_display_name,
            )

        residual_w = self._residual(sungrow) if sungrow else None
        if residual_w is not None and abs(residual_w) > self._residual_warn_w:
            if status == EnergyBalanceStatus.OK:
                status = EnergyBalanceStatus.RESIDUAL_HIGH
            flags.append("residual_high")

        non_ev_load, non_ev_reason = self._non_ev_load(
            sungrow=sungrow,
            halo=halo,
            load_includes_ev_charger=load_includes_ev_charger,
        )

        if self._double_counting_suspected(
            sungrow=sungrow,
            halo=halo,
            heartbeat=heartbeat,
            non_ev_load=non_ev_load,
        ):
            status = EnergyBalanceStatus.POSSIBLE_DOUBLE_COUNTING
            flags.append("possible_double_counting")

        return EnergyBalanceSnapshot(
            recorded_at=correlated.recorded_at.isoformat(),
            status=status,
            flags=tuple(flags),
            sungrow_pv_power_w=sungrow.pv_power_w if sungrow else None,
            sungrow_load_power_w=sungrow.load_power_w if sungrow else None,
            sungrow_grid_import_w=sungrow.grid_import_w if sungrow else None,
            sungrow_grid_export_w=sungrow.grid_export_w if sungrow else None,
            sungrow_battery_charge_w=sungrow.battery_charge_w if sungrow else None,
            sungrow_battery_discharge_w=sungrow.battery_discharge_w if sungrow else None,
            sungrow_battery_soc_pct=sungrow.battery_soc_pct if sungrow else None,
            sungrow_fresh=sungrow.fresh if sungrow else None,
            sungrow_telemetry_age_seconds=sungrow.data_age_seconds if sungrow else None,
            halo_power_w=halo.power_w if halo else None,
            virtual_evse_reported_power_w=virtual_evse.reported_power_w if virtual_evse else None,
            heartbeat_observed_ev_power_w=heartbeat.ev_actual_power_w if heartbeat else None,
            heartbeat_home_consumption_w=heartbeat.home_consumption_w if heartbeat else None,
            non_ev_house_load_w=non_ev_load,
            non_ev_house_load_reason=non_ev_reason,
            residual_w=residual_w,
            alignment_delta_seconds=correlated.alignment_delta_seconds,
            inverter_display_name=self._inverter_display_name,
        )

    def _residual(self, sungrow) -> float | None:
        required = (
            sungrow.pv_power_w,
            sungrow.grid_import_w,
            sungrow.grid_export_w,
            sungrow.battery_charge_w,
            sungrow.battery_discharge_w,
            sungrow.load_power_w,
        )
        if any(value is None for value in required):
            return None
        lhs = sungrow.pv_power_w + sungrow.grid_import_w + sungrow.battery_discharge_w  # type: ignore[operator]
        rhs = sungrow.load_power_w + sungrow.battery_charge_w + sungrow.grid_export_w  # type: ignore[operator]
        return lhs - rhs

    def _non_ev_load(
        self,
        *,
        sungrow,
        halo,
        load_includes_ev_charger: bool | None,
    ) -> tuple[float | None, str | None]:
        if load_includes_ev_charger is None:
            return None, "load_includes_ev_charger_unknown"
        if not load_includes_ev_charger:
            return None, "load_excludes_ev_by_config"
        if sungrow is None or halo is None:
            return None, "missing_sungrow_or_halo"
        if sungrow.load_power_w is None or halo.power_w is None:
            return None, "missing_load_or_halo_power"
        if not sungrow.fresh:
            return None, "sungrow_stale"
        return max(0.0, sungrow.load_power_w - halo.power_w), None

    def _double_counting_suspected(
        self,
        *,
        sungrow,
        halo,
        heartbeat,
        non_ev_load: float | None,
    ) -> bool:
        if heartbeat is None or halo is None or halo.power_w is None:
            return False
        heartbeat_total = heartbeat.home_consumption_w
        if heartbeat_total is None:
            return False
        if non_ev_load is not None:
            expected_total = non_ev_load + halo.power_w
        elif sungrow is not None and sungrow.load_power_w is not None:
            expected_total = sungrow.load_power_w
        else:
            return False
        return abs(heartbeat_total - expected_total - halo.power_w) < self._double_counting_tolerance_w
