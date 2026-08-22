"""Build EnergyState from HeartBeat API payloads."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from energy_core.energy.state import EnergyState
from energy_core.heartbeat.field_discovery import discover_relevant_fields
from energy_core.heartbeat.live_overview import extract_ev_target_power_w, parse_live_overview
from energy_core.heartbeat.market_prices import parse_market_prices


def _parse_ev(ev: dict[str, Any] | None) -> dict[str, Any]:
    if not ev:
        return {}
    settings = ev.get("chargeSettings") or {}
    return {
        "heartbeat_charging_mode": settings.get("chargingMode"),
        "target_soc": settings.get("targetSoc"),
        "departure_time": settings.get("primaryScheduleDepartureTime"),
    }


def _parse_ems(ems: dict[str, Any] | None) -> dict[str, Any]:
    if not ems:
        return {}
    mode = ems.get("activeChargingMode")
    return {
        "heartbeat_charging_mode": mode or None,
        "heartbeat_smart_charge_active": str(mode).upper() == "SMART_CHARGE",
    }


def _parse_optimizations(items: list[dict[str, Any]] | None) -> bool:
    if not items:
        return False
    now = datetime.now(UTC)
    for item in items:
        event_type = str(item.get("type") or item.get("eventType") or "")
        if "EV_CHARGE_FROM_GRID" not in event_type.upper():
            continue
        start = _parse_dt(item.get("start") or item.get("from"))
        end = _parse_dt(item.get("end") or item.get("to"))
        if start and end:
            start_utc = start if start.tzinfo else start.replace(tzinfo=UTC)
            end_utc = end if end.tzinfo else end.replace(tzinfo=UTC)
            if start_utc <= now <= end_utc:
                return True
        if start is None and end is None:
            return True
        if start and not end:
            start_utc = start if start.tzinfo else start.replace(tzinfo=UTC)
            if start_utc <= now:
                return True
    return False


def _parse_market_prices(data: dict[str, Any] | None) -> tuple[float | None, tuple[tuple[datetime, float], ...]]:
    parsed = parse_market_prices(data)
    forecast = tuple(
        (point.timestamp, point.all_in_eur_kwh or point.spot_eur_kwh)
        for point in parsed.points[:48]
    )
    return parsed.current_price_eur_kwh, forecast


def build_energy_state(
    *,
    live_overview: dict[str, Any] | None = None,
    ev: dict[str, Any] | None = None,
    ems: dict[str, Any] | None = None,
    optimizations: list[dict[str, Any]] | None = None,
    market_prices: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> EnergyState:
    now = now or datetime.now(UTC)
    overview = parse_live_overview(live_overview or {})
    ev_fields = _parse_ev(ev)
    ems_fields = _parse_ems(ems)
    price, forecast = _parse_market_prices(market_prices)

    hints = discover_relevant_fields(
        {
            "live_overview": live_overview or {},
            "ev": ev or {},
            "ems": ems or {},
            "optimizations": optimizations or [],
            "market_prices": market_prices or {},
        }
    )
    target = extract_ev_target_power_w(
        live_overview or {},
        ev or {},
        ems or {},
        {"optimizations": optimizations or []},
    )

    charging_mode = ems_fields.get("heartbeat_charging_mode") or ev_fields.get("heartbeat_charging_mode")
    smart_active = ems_fields.get("heartbeat_smart_charge_active") or str(charging_mode or "").upper() == "SMART_CHARGE"

    state = EnergyState(
        timestamp=overview["timestamp"],
        electricity_price_eur_kwh=price,
        price_forecast=forecast,
        pv_power_w=overview.get("pv_power_w"),
        grid_power_w=overview.get("grid_power_w"),
        grid_import_w=overview.get("grid_import_w"),
        grid_export_w=overview.get("grid_export_w"),
        home_consumption_w=overview.get("home_consumption_w"),
        battery_power_w=overview.get("battery_power_w"),
        battery_charge_power_w=overview.get("battery_charge_power_w"),
        battery_discharge_power_w=overview.get("battery_discharge_power_w"),
        battery_soc=overview.get("battery_soc"),
        phase_current_l1_a=overview.get("phase_current_l1_a"),
        phase_current_l2_a=overview.get("phase_current_l2_a"),
        phase_current_l3_a=overview.get("phase_current_l3_a"),
        ev_actual_power_w=overview.get("ev_actual_power_w"),
        ev_target_power_w=target,
        heartbeat_charging_mode=str(charging_mode) if charging_mode else None,
        heartbeat_smart_charge_active=bool(smart_active),
        ev_charge_from_grid_recommended=_parse_optimizations(optimizations),
        departure_time=ev_fields.get("departure_time"),
        target_soc=float(ev_fields["target_soc"]) if isinstance(ev_fields.get("target_soc"), (int, float)) else None,
        raw_field_hints=hints,
    )
    return state.with_age(now)


def _parse_dt(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
