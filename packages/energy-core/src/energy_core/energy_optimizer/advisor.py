"""Read-only Battery Opportunity Advisor (Phase 13)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from energy_core.energy_optimizer.types import EnergyAction
from energy_core.price_engine.strategy import EnergyStrategySnapshot
from energy_core.price_engine.types import StrategyState

_ACTION_LABELS_SV: dict[EnergyAction, str] = {
    EnergyAction.USE_NOW: "Använd energin nu",
    EnergyAction.STORE_IN_BATTERY: "Spara i batteriet",
    EnergyAction.EXPORT_TO_GRID: "Exportera till nätet",
    EnergyAction.DISCHARGE_BATTERY: "Urladda batteriet",
    EnergyAction.WAIT: "Avvakta",
}

_STATE_HEADLINES_SV: dict[StrategyState, str] = {
    StrategyState.PEAK_PROTECTION: "Toppskydd — begränsa effektupptag",
    StrategyState.PEAK_AHEAD: "Spara energi inför kommande pristopp",
    StrategyState.SAVE_BATTERY: "Spara i batteriet",
    StrategyState.DISCHARGE_BATTERY: "Urladda batteriet",
    StrategyState.EXPORT: "Exportera överskott",
    StrategyState.CHARGE_VEHICLE: "Prioritera EV-laddning i billigt fönster",
    StrategyState.NORMAL_SELF_USE: "Normal egenförbrukning",
    StrategyState.WAIT: "Avvakta tydligare prissignal",
    StrategyState.CHARGE_BATTERY: "Ladda batteriet",
}


@dataclass(frozen=True, slots=True)
class BatteryOpportunityAdvice:
    available: bool
    monitor_only: bool
    unavailable_reason_sv: str | None = None
    action: str | None = None
    action_label_sv: str | None = None
    headline_sv: str | None = None
    reason_sv: str | None = None
    confidence: float | None = None
    battery_soc_pct: float | None = None
    recommended_reserve_soc_pct: float | None = None
    expected_value_sek_kwh: float | None = None
    next_peak_at: datetime | None = None
    next_peak_import_sek_kwh: float | None = None
    optimization_mode: str | None = None
    strategy_state: str | None = None


def build_battery_opportunity_advice(snapshot: EnergyStrategySnapshot) -> BatteryOpportunityAdvice:
    """Build read-only battery guidance from a strategy snapshot."""
    base = {
        "monitor_only": True,
        "battery_soc_pct": snapshot.battery_soc_pct,
        "recommended_reserve_soc_pct": snapshot.recommended_reserve_soc_pct,
        "expected_value_sek_kwh": snapshot.eov_value_sek_kwh,
        "next_peak_at": snapshot.next_peak_at,
        "next_peak_import_sek_kwh": snapshot.next_peak_import_sek_kwh,
        "optimization_mode": snapshot.optimization_mode.value,
        "strategy_state": snapshot.strategy_state.value,
        "confidence": snapshot.confidence,
        "reason_sv": snapshot.reason_sv,
    }

    if snapshot.import_price_sek_kwh is None:
        return BatteryOpportunityAdvice(
            available=False,
            unavailable_reason_sv="Importpris saknas — batteriråd kan inte beräknas.",
            **base,
        )

    if snapshot.battery_soc_pct is None:
        return BatteryOpportunityAdvice(
            available=False,
            unavailable_reason_sv="Batterinivå (SOC) saknas i senaste mätningen.",
            **base,
        )

    action: EnergyAction | None = None
    if snapshot.recommended_action:
        try:
            action = EnergyAction(snapshot.recommended_action)
        except ValueError:
            action = None

    action_label = _ACTION_LABELS_SV.get(action) if action is not None else None
    headline = _STATE_HEADLINES_SV.get(snapshot.strategy_state)
    if action_label and snapshot.strategy_state not in {
        StrategyState.PEAK_PROTECTION,
        StrategyState.CHARGE_VEHICLE,
    }:
        headline = action_label
    if headline is None:
        headline = snapshot.reason_sv.split(".")[0] or "Batteriråd"

    return BatteryOpportunityAdvice(
        available=True,
        action=action.value if action is not None else None,
        action_label_sv=action_label,
        headline_sv=headline,
        **base,
    )
