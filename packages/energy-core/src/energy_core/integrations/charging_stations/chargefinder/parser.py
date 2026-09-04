"""Parse ChargeFinder station payloads into ChargingStationCandidate."""

from __future__ import annotations

from typing import Any

from energy_core.integrations.charging_stations.models import ChargingStationCandidate, DataQuality, StationProvider
from energy_core.vehicles.charging_intelligence.location import haversine_m

STATION_URL_TEMPLATE = "https://chargefinder.com/en/charging-station/{slug}"


def parse_station(raw: dict[str, Any], *, vehicle_lat: float, vehicle_lon: float) -> ChargingStationCandidate | None:
    slug = raw.get("slug")
    if not slug:
        return None
    location = raw.get("location") or {}
    lat = location.get("latitude")
    lon = location.get("longitude")
    if lat is None or lon is None:
        return None

    operator = _clean(raw.get("operator")) or _clean(raw.get("owner"))
    station_name = _clean(raw.get("title"))
    address_info = raw.get("locationAddress") or {}
    connector_type, max_power_kw, charging_type = _parse_outlets(raw.get("outletList"))
    if max_power_kw is None:
        max_power_kw = _float_or_none(raw.get("maxCapacity")) or _float_or_none(raw.get("minCapacity"))
        if max_power_kw is not None:
            charging_type = "DC" if max_power_kw >= 50 else "AC"

    distance_m = haversine_m(vehicle_lat, vehicle_lon, float(lat), float(lon))
    price_model, price_value = _parse_pricing(
        raw.get("outletList"),
        free_charging=_truthy_flag(raw.get("freeCharging")),
    )

    return ChargingStationCandidate(
        provider=StationProvider.CHARGEFINDER,
        provider_station_id=str(slug),
        operator=operator,
        station_name=station_name,
        network_name=operator,
        latitude=float(lat),
        longitude=float(lon),
        address=_clean(address_info.get("full")) or _clean(address_info.get("street")),
        postal_code=_clean(address_info.get("zip")),
        city=_clean(address_info.get("city")),
        country=_clean(address_info.get("countryCode")) or _clean(address_info.get("country")),
        connector_type=connector_type,
        max_power_kw=max_power_kw,
        charging_type=charging_type,
        distance_m=round(distance_m, 1),
        price_model=price_model,
        price_value_sek_kwh=price_value,
        external_url=STATION_URL_TEMPLATE.format(slug=slug),
        data_quality=DataQuality.LIVE,
        raw_provider_data=_mask_raw(raw),
    )


def parse_stations(
    raw_stations: list[dict[str, Any]],
    *,
    vehicle_lat: float,
    vehicle_lon: float,
    radius_m: float | None = None,
) -> list[ChargingStationCandidate]:
    candidates: list[ChargingStationCandidate] = []
    for raw in raw_stations:
        parsed = parse_station(raw, vehicle_lat=vehicle_lat, vehicle_lon=vehicle_lon)
        if parsed is None:
            continue
        if radius_m is not None and parsed.distance_m is not None and parsed.distance_m > radius_m:
            continue
        candidates.append(parsed)
    candidates.sort(key=lambda c: c.distance_m or float("inf"))
    return candidates


def _parse_outlets(outlet_list: Any) -> tuple[str | None, float | None, str | None]:
    if not isinstance(outlet_list, list) or not outlet_list:
        return None, None, None
    connector: str | None = None
    max_kw: float | None = None
    charging_type: str | None = None
    for group in outlet_list:
        if not isinstance(group, dict):
            continue
        capacity = _float_or_none(group.get("capacity"))
        if capacity is not None:
            max_kw = max(max_kw or 0.0, capacity)
        acdc = _clean(group.get("acdc"))
        if acdc and acdc.upper().startswith("DC"):
            charging_type = "DC"
        outlets = group.get("outlets")
        if isinstance(outlets, list):
            for outlet in outlets:
                if not isinstance(outlet, dict):
                    continue
                plug = _clean(outlet.get("plug"))
                if plug and connector is None:
                    connector = plug
                plug_kw = _float_or_none(outlet.get("capacity"))
                if plug_kw is not None:
                    max_kw = max(max_kw or 0.0, plug_kw)
                plug_acdc = _clean(outlet.get("acdc"))
                if plug_acdc and plug_acdc.upper().startswith("DC"):
                    charging_type = "DC"
    if charging_type is None:
        charging_type = "DC" if max_kw is not None and max_kw >= 50 else "AC"
    if connector and any(token in connector.upper() for token in ("CCS", "CHADEMO")):
        charging_type = "DC"
    return connector, max_kw, charging_type


def _parse_pricing(outlet_list: Any, *, free_charging: bool | None = None) -> tuple[str, float | None]:
    if not isinstance(outlet_list, list):
        return "UNKNOWN", None
    saw_zero_kwh = False
    max_cost_min: float | None = None
    for group in outlet_list:
        if not isinstance(group, dict):
            continue
        cost_kwh = _float_or_none(group.get("costKwh"))
        if cost_kwh is not None and cost_kwh > 0:
            return "PER_KWH", cost_kwh
        if cost_kwh == 0:
            saw_zero_kwh = True
        cost_min = _float_or_none(group.get("costMin"))
        if cost_min is not None and cost_min > 0:
            max_cost_min = max(max_cost_min or 0.0, cost_min)
        outlets = group.get("outlets")
        if isinstance(outlets, list):
            for outlet in outlets:
                if not isinstance(outlet, dict):
                    continue
                outlet_cost = _float_or_none(outlet.get("costKwh"))
                if outlet_cost is not None and outlet_cost > 0:
                    return "PER_KWH", outlet_cost
                if outlet_cost == 0:
                    saw_zero_kwh = True
                outlet_min = _float_or_none(outlet.get("costMin"))
                if outlet_min is not None and outlet_min > 0:
                    max_cost_min = max(max_cost_min or 0.0, outlet_min)
    if max_cost_min is not None and max_cost_min > 0:
        return "FIXED", max_cost_min
    if saw_zero_kwh and free_charging is True:
        return "FREE", 0.0
    return "UNKNOWN", None


def _parse_pricing_from_status(status_items: Any) -> tuple[str, float | None]:
    """Read live tariffs returned by ChargeFinder /status/{realtimeId}."""
    if not isinstance(status_items, list):
        return "UNKNOWN", None
    max_cost_kwh: float | None = None
    max_cost_session: float | None = None
    max_cost_min: float | None = None
    for item in status_items:
        if not isinstance(item, dict):
            continue
        tariffs = item.get("tariffs")
        if not isinstance(tariffs, list):
            continue
        for tariff in tariffs:
            if not isinstance(tariff, dict):
                continue
            cost_kwh = _float_or_none(tariff.get("costKwh"))
            if cost_kwh is not None and cost_kwh > 0:
                max_cost_kwh = max(max_cost_kwh or 0.0, cost_kwh)
            cost_session = _float_or_none(tariff.get("costSession"))
            if cost_session is not None and cost_session > 0:
                max_cost_session = max(max_cost_session or 0.0, cost_session)
            cost_min = _float_or_none(tariff.get("costMin"))
            if cost_min is not None and cost_min > 0:
                max_cost_min = max(max_cost_min or 0.0, cost_min)
            cost_parking = _float_or_none(tariff.get("costParking"))
            if cost_parking is not None and cost_parking > 0:
                max_cost_min = max(max_cost_min or 0.0, cost_parking)
    if max_cost_kwh is not None and max_cost_kwh > 0:
        return "PER_KWH", max_cost_kwh
    if max_cost_session is not None and max_cost_session > 0:
        return "FIXED", max_cost_session
    if max_cost_min is not None and max_cost_min > 0:
        return "FIXED", max_cost_min
    return "UNKNOWN", None


def _mask_raw(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "slug": raw.get("slug"),
        "title": raw.get("title"),
        "operator": raw.get("operator"),
        "owner": raw.get("owner"),
        "location": raw.get("location"),
        "locationAddress": raw.get("locationAddress"),
        "minCapacity": raw.get("minCapacity"),
        "maxCapacity": raw.get("maxCapacity"),
        "outletList_count": len(raw.get("outletList") or []) if isinstance(raw.get("outletList"), list) else 0,
    }


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _truthy_flag(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes"}:
        return True
    if text in {"0", "false", "no"}:
        return False
    return None
