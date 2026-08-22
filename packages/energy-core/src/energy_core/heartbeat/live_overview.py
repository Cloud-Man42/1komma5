"""Parse HeartBeat live-overview and related payloads into partial state."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _power_value(data: Any) -> float | None:
    if isinstance(data, dict):
        value = data.get("value")
        if isinstance(value, (int, float)):
            return float(value)
    if isinstance(data, (int, float)):
        return float(data)
    return None


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def extract_pv_power_w(data: dict[str, Any]) -> float | None:
    """Shared PV extraction for live-overview parsers and Sungrow proxy."""
    hero = data.get("liveHeroView") or {}
    cards = data.get("summaryCards") or {}
    pv = cards.get("photovoltaic") or {}
    production = _power_value(pv.get("production") if isinstance(pv, dict) else pv)
    if production is not None:
        return production
    hero_production = hero.get("production")
    return _power_value(hero_production)


def parse_live_overview(data: dict[str, Any]) -> dict[str, Any]:
    hero = data.get("liveHeroView") or {}
    cards = data.get("summaryCards") or {}
    battery = cards.get("battery") or {}
    pv = cards.get("photovoltaic") or {}
    grid = cards.get("grid") or hero.get("grid") or {}
    household = cards.get("household") or hero.get("consumption") or {}

    ev_chargers = cards.get("evChargers") or []
    ev_power = None
    if isinstance(ev_chargers, list) and ev_chargers:
        ev_power = _power_value((ev_chargers[0] or {}).get("power"))
    if ev_power is None:
        aggregated = hero.get("evChargersAggregated") or data.get("evChargersAggregated") or {}
        ev_power = _power_value(aggregated.get("power") if isinstance(aggregated, dict) else aggregated)

    battery_power = _power_value(battery.get("power"))
    battery_soc = battery.get("stateOfCharge")
    if battery_soc is None:
        battery_soc = hero.get("totalStateOfCharge")
    battery_charge_power_w = max(0.0, battery_power) if battery_power is not None else None
    battery_discharge_power_w = abs(min(0.0, battery_power)) if battery_power is not None else None

    phase_currents = _extract_phase_currents(data)

    grid_power = _power_value(grid)
    grid_import = _power_value(hero.get("gridConsumption"))
    grid_export = _power_value(hero.get("gridFeedIn"))

    home_consumption_w = _power_value(household.get("power") if isinstance(household, dict) else household)
    if home_consumption_w is None and isinstance(household, dict):
        home_consumption_w = _power_value(household)

    return {
        "timestamp": _parse_timestamp(data.get("timestamp")) or datetime.now(UTC),
        "pv_power_w": extract_pv_power_w(data),
        "grid_power_w": grid_power,
        "grid_import_w": grid_import,
        "grid_export_w": grid_export,
        "home_consumption_w": home_consumption_w,
        "battery_power_w": battery_power,
        "battery_charge_power_w": battery_charge_power_w,
        "battery_discharge_power_w": battery_discharge_power_w,
        "battery_soc": float(battery_soc) if isinstance(battery_soc, (int, float)) else None,
        "phase_current_l1_a": phase_currents.get("l1"),
        "phase_current_l2_a": phase_currents.get("l2"),
        "phase_current_l3_a": phase_currents.get("l3"),
        "ev_actual_power_w": ev_power,
    }


def _extract_phase_currents(data: dict[str, Any]) -> dict[str, float | None]:
    candidates = (
        data.get("phaseCurrents"),
        data.get("gridPhaseCurrents"),
        (data.get("liveHeroView") or {}).get("phaseCurrents"),
        (data.get("summaryCards") or {}).get("grid"),
    )
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        l1 = _float_or_none(candidate.get("l1") or candidate.get("L1") or candidate.get("phase1"))
        l2 = _float_or_none(candidate.get("l2") or candidate.get("L2") or candidate.get("phase2"))
        l3 = _float_or_none(candidate.get("l3") or candidate.get("L3") or candidate.get("phase3"))
        if any(value is not None for value in (l1, l2, l3)):
            return {"l1": l1, "l2": l2, "l3": l3}
    return {"l1": None, "l2": None, "l3": None}


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def extract_ev_target_power_w(*payloads: dict[str, Any]) -> float | None:
    """Search parsed/discovery hints for a numeric EV power target in watts."""
    target_keys = (
        "powerTarget",
        "targetPower",
        "chargingPowerTarget",
        "evPowerTarget",
        "plannedPower",
        "powerSetpoint",
        "optimizedPower",
    )

    def walk(value: Any) -> float | None:
        if isinstance(value, dict):
            for key, child in value.items():
                if str(key) in target_keys:
                    power = _power_value(child)
                    if power is not None:
                        return power
                found = walk(child)
                if found is not None:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = walk(child)
                if found is not None:
                    return found
        return None

    for payload in payloads:
        found = walk(payload)
        if found is not None:
            return found
    return None
