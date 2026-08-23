"""Display labels for smart charging status in Swedish."""

from __future__ import annotations

from energy_core.charging.state_machine import SmartChargingState

_REASON_LABELS: dict[str, str] = {
    "smart_wait_cheaper": "Väntar på lägre pris",
    "smart_wait_expensive": "Väntar — dyrt elpris",
    "smart_scheduled": "Laddar smart",
    "smart_urgency_balanced": "Laddar smart (deadline närmar sig)",
    "normal_price_ok": "Laddar smart (normalt pris)",
    "cheap_now": "Laddar smart",
    "quick_charge": "Snabbladdning",
    "override": "Snabbladdning (override)",
    "manual_override": "Snabbladdning (override)",
    "solar_forecast_wait": "Väntar på solel (prognos)",
    "solar_forecast_partial_grid": "Planerar delvis nätenergi",
    "solar_forecast_wait_cheaper": "Väntar på billigare nät + solel",
    "solar_forecast_grid_required": "Planerar nätenergi",
    "solar_forecast_unavailable": "Ingen solprognos",
    "temporary_grid_import": "Tillfälligt nätuttag",
    "reduce_before_stop": "Minskar laddström",
    "stop_delay": "Avslutar laddning",
    "start_delay": "Förbereder start",
    "waiting_for_export": "Väntar på solöverskott",
    "grid_import": "Nätimport — solel räcker inte",
    "cooldown": "Väntar på omstart",
    "user_paused": "Pausad",
    "no_vehicle_connected": "Väntar på bil",
    "fault": "Fel",
    "charger_offline": "Fel",
    "start_rate_limited": "För många omstarter",
    "battery_priority": "Batteri prioriteras",
    "deadline_risk": "Deadline — laddar i tid",
    "deadline_overdue": "Deadline passerad — max laddning",
    "deadline_wait_cheaper": "Väntar trots deadline",
    "smart_solar_surplus": "Smart — solöverskott",
    "stable_grid_export": "Följer solöverskott",
    "insufficient_export": "Otillräckligt solöverskott",
    "solar_start_delay": "Solstart — kort delay",
    "solar_stop_delay": "Solstopp — kort delay",
    "export_hysteresis": "Väntar på stabil export",
}

_STATE_LABELS: dict[SmartChargingState, str] = {
    SmartChargingState.PAUSED: "Pausad",
    SmartChargingState.WAITING_TO_START: "Väntar på omstart",
    SmartChargingState.STARTING: "Laddar smart",
    SmartChargingState.CHARGING_STABLE: "Laddar smart",
    SmartChargingState.REDUCING: "Minskar laddström",
    SmartChargingState.WAITING_TO_STOP: "Minskar laddström",
    SmartChargingState.STOPPING: "Pausad",
    SmartChargingState.COOLDOWN: "Väntar på omstart",
    SmartChargingState.FAULT: "Fel",
}


def display_status_sv(
    *,
    state: SmartChargingState | str | None,
    reason: str | None,
    externally_limited: bool,
) -> str:
    if externally_limited:
        return "Externt begränsad"
    if reason and reason in _REASON_LABELS:
        return _REASON_LABELS[reason]
    if state is not None:
        try:
            parsed = SmartChargingState(state) if isinstance(state, str) else state
        except ValueError:
            parsed = None
        if parsed is not None and parsed in _STATE_LABELS:
            return _STATE_LABELS[parsed]
    return "Laddar smart"
