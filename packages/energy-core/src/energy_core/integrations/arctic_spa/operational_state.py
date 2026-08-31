"""Derive live spa operational state from reported status and measured load."""

from __future__ import annotations

FILTER_ACTIVE_STATUSES = frozenset(
    {"Filtering", "Boost", "Resuming", "Overtemperature", "Sanitize", "Purge"},
)
MIN_SPA_LOAD_W = 100.0
MIN_PUMP_LOAD_W = 75.0
MIN_HEATER_LOAD_W = 50.0

# Arctic Spa reports filter status in English; Swedish surfaces (kiosk display,
# dashboards) must never show the raw API value.
FILTER_STATUS_SV = {
    "Filtering": "Pågår",
    "Idle": "Av",
    "Boost": "Boost",
    "Resuming": "Återstartar",
    "Overtemperature": "Övertemperatur",
    "Sanitize": "Rening",
    "Purge": "Rensning",
    "Heating": "Värmer",
    "Off": "Av",
}


def filter_status_sv(filter_status: str | None) -> str | None:
    """Swedish label for an Arctic Spa filter status, or None when unknown."""
    if not filter_status:
        return None
    return FILTER_STATUS_SV.get(filter_status.strip().title(), filter_status)


def pump_power_w(breakdown: dict[str, float]) -> float:
    return sum(watts for key, watts in breakdown.items() if "pump" in key.lower())


def heater_power_w(breakdown: dict[str, float]) -> float:
    keys = {"heater", "värmare", "varmare"}
    return sum(watts for key, watts in breakdown.items() if key.lower() in keys)


def spa_load_w(current_power_w: float | None, breakdown: dict[str, float]) -> float:
    if current_power_w is not None and current_power_w > 0:
        return current_power_w
    return sum(breakdown.values())


def filter_cycle_active(
    *,
    filter_status: str | None,
    current_power_w: float | None,
    breakdown: dict[str, float],
) -> bool:
    if not filter_status or filter_status not in FILTER_ACTIVE_STATUSES:
        return False
    total = spa_load_w(current_power_w, breakdown)
    pumps = pump_power_w(breakdown)
    return total >= MIN_SPA_LOAD_W or pumps >= MIN_PUMP_LOAD_W


def heater_drawing_power(
    *,
    heater_active_reported: bool,
    current_power_w: float | None,
    breakdown: dict[str, float],
) -> bool:
    heater = heater_power_w(breakdown)
    if heater >= MIN_HEATER_LOAD_W:
        return True
    total = spa_load_w(current_power_w, breakdown)
    return bool(heater_active_reported and total >= MIN_SPA_LOAD_W)
