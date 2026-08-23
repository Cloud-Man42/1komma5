"""Map stored energy balance snapshots to API responses."""

from __future__ import annotations

from datetime import datetime

from app.schemas import EnergyBalanceResponse
from energy_core.db.energy_balance_repo import StoredEnergyBalanceSnapshot


def _fmt_kw(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value / 1000:.1f}kW"


def build_energy_flow_line(payload: dict) -> str | None:
    pv = payload.get("sungrow_pv_power_w")
    load = payload.get("sungrow_load_power_w")
    ev = payload.get("halo_power_w")
    if pv is None and load is None and ev is None:
        return None
    return f"PV {_fmt_kw(pv)} → Load {_fmt_kw(load)} | EV {_fmt_kw(ev)}"


def snapshot_to_response(
    stored: StoredEnergyBalanceSnapshot | None,
    *,
    charger_id: int,
) -> EnergyBalanceResponse:
    if stored is None:
        return EnergyBalanceResponse(charger_id=charger_id, status="UNAVAILABLE", flags=[])

    payload = stored.payload
    recorded_raw = payload.get("recorded_at")
    recorded_at = (
        datetime.fromisoformat(recorded_raw)
        if isinstance(recorded_raw, str)
        else stored.recorded_at
    )

    return EnergyBalanceResponse(
        charger_id=charger_id,
        recorded_at=recorded_at,
        status=stored.status,
        flags=stored.flags,
        inverter_display_name=payload.get("inverter_display_name")
        or "Sungrow Hybrid Inverter SH10",
        sungrow_pv_power_w=payload.get("sungrow_pv_power_w"),
        sungrow_load_power_w=payload.get("sungrow_load_power_w"),
        sungrow_grid_import_w=payload.get("sungrow_grid_import_w"),
        sungrow_grid_export_w=payload.get("sungrow_grid_export_w"),
        sungrow_battery_charge_w=payload.get("sungrow_battery_charge_w"),
        sungrow_battery_discharge_w=payload.get("sungrow_battery_discharge_w"),
        sungrow_battery_soc_pct=payload.get("sungrow_battery_soc_pct"),
        sungrow_fresh=payload.get("sungrow_fresh"),
        sungrow_telemetry_age_seconds=payload.get("sungrow_telemetry_age_seconds"),
        halo_power_w=payload.get("halo_power_w"),
        virtual_evse_reported_power_w=payload.get("virtual_evse_reported_power_w"),
        heartbeat_observed_ev_power_w=payload.get("heartbeat_observed_ev_power_w"),
        heartbeat_home_consumption_w=payload.get("heartbeat_home_consumption_w"),
        non_ev_house_load_w=payload.get("non_ev_house_load_w"),
        non_ev_house_load_reason=payload.get("non_ev_house_load_reason"),
        residual_w=payload.get("residual_w"),
        alignment_delta_seconds=payload.get("alignment_delta_seconds"),
        energy_flow_line=build_energy_flow_line(payload),
    )
