"""Normalized Module Store category mapping."""

from __future__ import annotations

STORE_CATEGORIES: tuple[str, ...] = (
    "Energy",
    "Solar",
    "Battery",
    "EV Charging",
    "Vehicles",
    "Climate",
    "SPA & Pool",
    "Weather",
    "Electricity Pricing",
    "Automation",
    "AI",
    "Monitoring",
    "Infrastructure",
    "Other",
)

_DEVICE_CATEGORY_MAP: dict[str, str] = {
    "energy_provider": "Energy",
    "energy": "Energy",
    "solar": "Solar",
    "battery": "Battery",
    "ev_charger": "EV Charging",
    "vehicle": "Vehicles",
    "climate": "Climate",
    "hvac": "Climate",
    "spa": "SPA & Pool",
    "pool": "SPA & Pool",
    "weather": "Weather",
    "pricing": "Electricity Pricing",
    "electricity_pricing": "Electricity Pricing",
    "automation": "Automation",
    "ai": "AI",
    "monitoring": "Monitoring",
    "infrastructure": "Infrastructure",
}

_MODULE_ID_HINTS: dict[str, str] = {
    "heartbeat": "Energy",
    "chargeamps": "EV Charging",
    "mercedes": "Vehicles",
    "arctic_spa": "SPA & Pool",
    "weather": "Weather",
    "price": "Electricity Pricing",
    "solar": "Solar",
    "forecast": "Solar",
}


def normalize_category(*, device_categories: tuple[str, ...] | list[str], module_id: str) -> str:
    for raw in device_categories:
        mapped = _DEVICE_CATEGORY_MAP.get(str(raw).lower())
        if mapped:
            return mapped
    lowered = module_id.lower()
    for hint, category in _MODULE_ID_HINTS.items():
        if hint in lowered:
            return category
    return "Other"


def categories_for_module(*, device_categories: tuple[str, ...] | list[str], module_id: str) -> tuple[str, ...]:
    primary = normalize_category(device_categories=device_categories, module_id=module_id)
    extras: list[str] = []
    for raw in device_categories:
        mapped = _DEVICE_CATEGORY_MAP.get(str(raw).lower())
        if mapped and mapped not in extras and mapped != primary:
            extras.append(mapped)
    return (primary, *extras)
