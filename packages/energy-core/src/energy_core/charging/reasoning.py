"""Explain Heartbeat inputs and EMIC charging decisions for diagnostics UI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from energy_core.charging.display_status import display_status_sv
from energy_core.charging.override import override_active
from energy_core.charging.policy import (
    immediate_start,
    normalized_mode,
    respects_manual_pause,
    uses_price_optimization,
)
from energy_core.charging.smart_schedule import GREEN_PRICE_RATIO, should_charge_smart
from energy_core.db.models import EvChargerModel, SiteModel
from energy_core.energy.state import EnergyState
from energy_core.solar_forecast.types import SolarChargingPlan


@dataclass(frozen=True, slots=True)
class EnergyReasoningSnapshot:
    bridge_enabled: bool
    charging_active: bool
    charging_mode: str
    heartbeat_charging_mode: str | None
    ev_charge_from_grid_recommended: bool
    ev_target_power_w: float | None
    pv_power_w: float | None
    grid_import_w: float | None
    grid_export_w: float | None
    home_consumption_w: float | None
    battery_soc_pct: float | None
    ev_actual_power_w: float | None
    current_price_eur_kwh: float | None
    price_average_eur_kwh: float | None
    price_tier: str
    price_would_charge: bool
    price_reason: str
    smart_charging_state: str | None
    decision_reason: str | None
    decision_reason_sv: str | None
    display_status_sv: str | None
    requested_current_a: float | None
    applied_current_a: float | None
    vehicle_connected: bool | None
    halo_connected: bool | None
    solar_plan_available: bool
    solar_plan_reason: str | None
    solar_first: bool
    active_optimizations: tuple[str, ...]
    energy_flow_line: str | None
    energy_balance_status: str | None
    reasoning_steps: tuple[str, ...]
    vehicle_linked: bool = False
    vehicle_display_name: str | None = None
    vehicle_soc_pct: float | None = None
    vehicle_target_soc_pct: float | None = None
    vehicle_required_energy_kwh: float | None = None
    vehicle_departure_time: str | None = None
    vehicle_energy_quality: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "bridge_enabled": self.bridge_enabled,
            "charging_active": self.charging_active,
            "charging_mode": self.charging_mode,
            "heartbeat_charging_mode": self.heartbeat_charging_mode,
            "ev_charge_from_grid_recommended": self.ev_charge_from_grid_recommended,
            "ev_target_power_w": self.ev_target_power_w,
            "pv_power_w": self.pv_power_w,
            "grid_import_w": self.grid_import_w,
            "grid_export_w": self.grid_export_w,
            "home_consumption_w": self.home_consumption_w,
            "battery_soc_pct": self.battery_soc_pct,
            "ev_actual_power_w": self.ev_actual_power_w,
            "current_price_eur_kwh": self.current_price_eur_kwh,
            "price_average_eur_kwh": self.price_average_eur_kwh,
            "price_tier": self.price_tier,
            "price_would_charge": self.price_would_charge,
            "price_reason": self.price_reason,
            "smart_charging_state": self.smart_charging_state,
            "decision_reason": self.decision_reason,
            "decision_reason_sv": self.decision_reason_sv,
            "display_status_sv": self.display_status_sv,
            "requested_current_a": self.requested_current_a,
            "applied_current_a": self.applied_current_a,
            "vehicle_connected": self.vehicle_connected,
            "halo_connected": self.halo_connected,
            "solar_plan_available": self.solar_plan_available,
            "solar_plan_reason": self.solar_plan_reason,
            "solar_first": self.solar_first,
            "active_optimizations": list(self.active_optimizations),
            "energy_flow_line": self.energy_flow_line,
            "energy_balance_status": self.energy_balance_status,
            "reasoning_steps": list(self.reasoning_steps),
            "vehicle_linked": self.vehicle_linked,
            "vehicle_display_name": self.vehicle_display_name,
            "vehicle_soc_pct": self.vehicle_soc_pct,
            "vehicle_target_soc_pct": self.vehicle_target_soc_pct,
            "vehicle_required_energy_kwh": self.vehicle_required_energy_kwh,
            "vehicle_departure_time": self.vehicle_departure_time,
            "vehicle_energy_quality": self.vehicle_energy_quality,
        }


def build_energy_reasoning(
    *,
    charger: EvChargerModel,
    site: SiteModel,
    energy: EnergyState | None = None,
    solar_plan: SolarChargingPlan | None = None,
    energy_flow_line: str | None = None,
    energy_balance_status: str | None = None,
    active_optimizations: tuple[str, ...] = (),
    vehicle_context=None,
    now: datetime | None = None,
) -> EnergyReasoningSnapshot:
    now = now or datetime.now(UTC)
    mode = charger.charging_mode or "SMART_CHARGE"
    is_override = override_active(charger.override_until, now=now)
    charging_active = bool(charger.bridge_enabled) and not respects_manual_pause(
        mode, override_active=is_override
    )
    departure_time = (
        (energy.departure_time if energy and energy.vehicle_linked else None)
        or charger.departure_time
        or (energy.departure_time if energy else None)
    )
    timezone = site.timezone or "Europe/Stockholm"
    expensive_threshold = 0.35
    charge_hours = 4.0

    current_price = energy.electricity_price_eur_kwh if energy else None
    forecast = energy.price_forecast if energy else ()
    average = _forecast_average(forecast)
    price_tier = _price_tier(current_price, average)
    show_price_rules = uses_price_optimization(mode, override_active=is_override)
    if show_price_rules:
        price_would_charge, price_reason = should_charge_smart(
            now,
            departure_time=departure_time,
            price_forecast=forecast,
            current_price=current_price,
            expensive_threshold=expensive_threshold,
            charge_hours=charge_hours,
            timezone=timezone,
        )
    else:
        price_would_charge = immediate_start(mode, override_active=is_override)
        price_reason = "quick_charge" if price_would_charge else "not_applicable"

    decision_reason = charger.last_charging_reason
    display = display_status_sv(
        state=charger.smart_charging_state,
        reason=decision_reason,
        externally_limited=bool(charger.externally_limited),
    )
    decision_reason_sv = display_status_sv(
        state=None,
        reason=decision_reason,
        externally_limited=False,
    )

    steps = _build_steps(
        charger=charger,
        energy=energy,
        price_tier=price_tier,
        price_would_charge=price_would_charge,
        price_reason=price_reason,
        solar_plan=solar_plan,
        active_optimizations=active_optimizations,
        charging_active=charging_active,
        decision_reason=decision_reason,
        display_status_sv=display,
        override_active=is_override,
        show_price_rules=show_price_rules,
        vehicle_context=vehicle_context,
    )

    vehicle_soc = None
    vehicle_target = None
    vehicle_required = None
    vehicle_departure = None
    vehicle_quality = None
    vehicle_linked = bool(energy and energy.vehicle_linked)
    vehicle_name = energy.vehicle_display_name if energy else None
    if energy and energy.vehicle_linked:
        vehicle_soc = energy.ev_soc * 100.0 if energy.ev_soc is not None else None
        vehicle_target = energy.target_soc * 100.0 if energy.target_soc is not None else None
        vehicle_required = energy.vehicle_required_energy_kwh
        vehicle_departure = energy.departure_time
        vehicle_quality = energy.vehicle_energy_quality
    elif vehicle_context is not None:
        vehicle_name = vehicle_context.display_name
        vehicle_soc = vehicle_context.requirement.current_soc_percent
        vehicle_target = vehicle_context.requirement.target_soc_percent
        vehicle_required = vehicle_context.requirement.required_energy_kwh
        vehicle_departure = vehicle_context.departure_time
        vehicle_quality = vehicle_context.requirement.quality

    return EnergyReasoningSnapshot(
        bridge_enabled=bool(charger.bridge_enabled),
        charging_active=charging_active,
        charging_mode=mode,
        heartbeat_charging_mode=energy.heartbeat_charging_mode if energy else None,
        ev_charge_from_grid_recommended=bool(energy.ev_charge_from_grid_recommended) if energy else False,
        ev_target_power_w=energy.ev_target_power_w if energy else None,
        pv_power_w=energy.pv_power_w if energy else None,
        grid_import_w=energy.grid_import_w if energy else None,
        grid_export_w=energy.grid_export_w if energy else None,
        home_consumption_w=energy.home_consumption_w if energy else None,
        battery_soc_pct=energy.battery_soc if energy else None,
        ev_actual_power_w=energy.ev_actual_power_w if energy else charger.last_actual_power_w,
        current_price_eur_kwh=current_price,
        price_average_eur_kwh=average,
        price_tier=price_tier,
        price_would_charge=price_would_charge,
        price_reason=price_reason,
        smart_charging_state=charger.smart_charging_state,
        decision_reason=decision_reason,
        decision_reason_sv=decision_reason_sv,
        display_status_sv=display,
        requested_current_a=charger.last_requested_current_a,
        applied_current_a=charger.last_applied_current_a,
        vehicle_connected=charger.last_vehicle_connected,
        halo_connected=charger.last_halo_connected,
        solar_plan_available=solar_plan is not None,
        solar_plan_reason=solar_plan.reason_code if solar_plan else None,
        solar_first=bool(solar_plan.solar_first) if solar_plan else False,
        active_optimizations=active_optimizations,
        energy_flow_line=energy_flow_line,
        energy_balance_status=energy_balance_status,
        reasoning_steps=steps,
        vehicle_linked=vehicle_linked,
        vehicle_display_name=vehicle_name,
        vehicle_soc_pct=vehicle_soc,
        vehicle_target_soc_pct=vehicle_target,
        vehicle_required_energy_kwh=vehicle_required,
        vehicle_departure_time=vehicle_departure,
        vehicle_energy_quality=vehicle_quality,
    )


def _forecast_average(forecast: tuple[tuple[datetime, float], ...]) -> float | None:
    if not forecast:
        return None
    return sum(price for _, price in forecast) / len(forecast)


def _price_tier(current: float | None, average: float | None) -> str:
    if current is None or average is None or average <= 0:
        return "unknown"
    if current <= average * GREEN_PRICE_RATIO:
        return "green"
    if current >= average * 1.15:
        return "red"
    return "normal"


def _build_steps(
    *,
    charger: EvChargerModel,
    energy: EnergyState | None,
    price_tier: str,
    price_would_charge: bool,
    price_reason: str,
    solar_plan: SolarChargingPlan | None,
    active_optimizations: tuple[str, ...],
    charging_active: bool,
    decision_reason: str | None,
    display_status_sv: str | None,
    override_active: bool = False,
    show_price_rules: bool = True,
    vehicle_context=None,
) -> tuple[str, ...]:
    steps: list[str] = []

    if not charger.bridge_enabled:
        steps.append("EMIC-styrning är avstängd — laddboxen styrs inte automatiskt.")
        return tuple(steps)

    if override_active:
        steps.append("Snabbladdning (override) — pris- och solregler ignoreras tillfälligt.")
    elif normalized_mode(charger.charging_mode) in {"QUICK_CHARGE", "QUICK"}:
        steps.append("Snabbladdning — laddar med max ström från nätet.")
    elif normalized_mode(charger.charging_mode) in {"SOLAR_CHARGE", "SOLAR"}:
        steps.append("Solel — laddning styrs av solöverskott/export.")
    elif not charging_active:
        steps.append("Laddning är pausad manuellt (PAUSED).")

    if energy is None:
        steps.append("Live Heartbeat-data saknas — visar senaste sparade beslut.")
    else:
        if energy.pv_power_w is not None and energy.grid_export_w is not None:
            if energy.grid_export_w >= 1500:
                steps.append(
                    f"Solel/export: PV {energy.pv_power_w / 1000:.1f} kW, "
                    f"nätexport {energy.grid_export_w / 1000:.1f} kW — solöverskott kan användas."
                )
            elif energy.grid_import_w and energy.grid_import_w > 500:
                steps.append(
                    f"Nätimport {energy.grid_import_w / 1000:.1f} kW — solel räcker inte just nu."
                )
        if energy.ev_charge_from_grid_recommended:
            steps.append("Heartbeat AI rekommenderar laddning från nätet just nu.")
        if energy.ev_target_power_w is not None:
            steps.append(f"Heartbeat EV-mål: {energy.ev_target_power_w / 1000:.1f} kW.")

    if energy is not None and energy.vehicle_linked:
        soc = f"{energy.ev_soc * 100:.0f} %" if energy.ev_soc is not None else "—"
        target = f"{energy.target_soc * 100:.0f} %" if energy.target_soc is not None else "—"
        need = (
            f"{energy.vehicle_required_energy_kwh:.1f} kWh"
            if energy.vehicle_required_energy_kwh is not None
            else "—"
        )
        quality = energy.vehicle_energy_quality or "UNKNOWN"
        label = energy.vehicle_display_name or "Fordon"
        steps.append(
            f"Fordonsdata ({label}): SoC {soc}, mål {target}, behov {need} ({quality.lower()})."
        )
        if energy.departure_time:
            steps.append(f"Mercedes avresa: {energy.departure_time}.")
    elif vehicle_context is not None and not vehicle_context.active:
        reason = "inaktuell data" if vehicle_context.stale else "låg Halo-korrelation"
        steps.append(f"Fordonsdata används inte i SmartLaddning ({reason}).")

    tier_label = {"green": "grönt (billigt)", "red": "rött (dyrt)", "normal": "normalt"}.get(
        price_tier, "okänt"
    )
    if show_price_rules:
        steps.append(f"Elprisnivå: {tier_label}.")
        if price_would_charge:
            steps.append(_price_charge_step(price_reason))
        else:
            steps.append(_price_wait_step(price_reason))

    if solar_plan is not None:
        if solar_plan.solar_first:
            steps.append("Solplan: solel prioriteras — nätladdning väntar tills deadline närmar sig.")
        else:
            steps.append("Solplan: för lite solel väntas — nätladdning planeras vid billiga timmar.")

    if active_optimizations:
        steps.append(f"Aktiva Heartbeat-optimeringar: {', '.join(active_optimizations)}.")

    if charger.last_vehicle_connected is False:
        steps.append("Ingen bil detekterad — laddning blockeras tills bilen är inkopplad.")
    elif charger.last_vehicle_connected:
        steps.append("Bil inkopplad.")

    if decision_reason:
        steps.append(f"EMIC-beslut: {display_status_sv or decision_reason} ({decision_reason}).")
    if charger.last_applied_current_a is not None:
        steps.append(f"Tillämpad ström: {charger.last_applied_current_a:.1f} A.")

    return tuple(steps)


def _price_charge_step(reason: str) -> str:
    labels = {
        "cheap_now": "Prisregel: billigt elpris — laddar från nätet.",
        "normal_price_ok": "Vardagsläge: normalt pris — laddar utan att vänta på dyraste timmarna.",
        "smart_scheduled": "Prisregel: nuvarande timme är bland de billigaste — laddar.",
        "smart_urgency_balanced": "Deadline närmar sig — laddar vid normalt pris.",
        "deadline_risk": "Deadline närmar sig — laddar för att hinna klart.",
    }
    return labels.get(reason, f"Prisregel säger ladda ({reason}).")


def _price_wait_step(reason: str) -> str:
    labels = {
        "smart_wait_cheaper": "Gott om tid — väntar på billigare timmar.",
        "smart_wait_expensive": "Elpriset är tydligt dyrt — väntar.",
        "expensive_no_forecast": "Dyrt elpris och ingen prognos — väntar.",
        "no_forecast": "Ingen elprisprognos — väntar.",
        "solar_forecast_wait": "Solel väntas innan deadline — väntar med nätladdning.",
        "solar_forecast_wait_cheaper": "Lite solel väntas — väntar på billigare nät-timmar.",
    }
    return labels.get(reason, f"Prisregel säger vänta ({reason}).")


def parse_active_optimizations(items: list[dict[str, Any]] | None, *, now: datetime | None = None) -> tuple[str, ...]:
    if not items:
        return ()
    now = now or datetime.now(UTC)
    active: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        event_type = str(item.get("type") or item.get("eventType") or "UNKNOWN")
        start = _parse_dt(item.get("start") or item.get("from"))
        end = _parse_dt(item.get("end") or item.get("to"))
        if start and end:
            if start <= now <= end:
                active.append(event_type)
        elif start and start <= now:
            active.append(event_type)
        elif start is None and end is None:
            active.append(event_type)
    return tuple(active)


def _parse_dt(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


async def load_energy_reasoning_for_charger(
    session,
    site: SiteModel,
    charger: EvChargerModel,
    *,
    now: datetime | None = None,
) -> EnergyReasoningSnapshot:
    """Load live Heartbeat context and build a reasoning snapshot for API/UI."""
    import logging

    from energy_core.charging.solar_plan import load_solar_charging_plan_for_charger
    from energy_core.config import get_settings
    from energy_core.db.energy_balance_repo import EnergyBalanceRepository
    from energy_core.energy.heartbeat_provider import HeartbeatEnergyProvider
    from energy_core.heartbeat_client_factory import create_heartbeat_client
    from energy_core.vehicles.smart_charging import apply_vehicle_charging_context, resolve_vehicle_charging_context
    from energy_core.charging.solar_plan import charging_config_from_models

    logger = logging.getLogger(__name__)
    now = now or datetime.now(UTC)
    energy = None
    active_optimizations: tuple[str, ...] = ()
    vehicle_context = None
    config = charging_config_from_models(charger, site)

    client = await create_heartbeat_client(session)
    if client is not None and site.external_system_id:
        try:
            provider = HeartbeatEnergyProvider(
                client,
                system_id=site.external_system_id,
                ev_id=charger.heartbeat_ev_id,
            )
            energy = await provider.get_energy_state(now=now)
            from_iso = (now - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
            to_iso = (now + timedelta(hours=24)).isoformat().replace("+00:00", "Z")
            items = await client.fetch_optimizations(
                site.external_system_id,
                from_iso=from_iso,
                to_iso=to_iso,
            )
            active_optimizations = parse_active_optimizations(items, now=now)
        except Exception:
            logger.debug("energy reasoning heartbeat fetch failed site=%s", site.slug, exc_info=True)

    vehicle_context = await resolve_vehicle_charging_context(
        session,
        site_id=site.id,
        charger_id=charger.id,
        timezone=config.timezone,
        now=now,
    )
    if energy is not None:
        energy, config = apply_vehicle_charging_context(charger, energy, config, vehicle_context)

    settings = get_settings()
    balance_repo = EnergyBalanceRepository(session, is_sqlite=settings.is_sqlite)
    latest = await balance_repo.get_latest(site_id=site.id, charger_id=charger.id)
    energy_flow_line = None
    energy_balance_status = None
    if latest is not None:
        energy_balance_status = latest.status if latest.status != "UNAVAILABLE" else None
        energy_flow_line = _energy_flow_line_from_payload(latest.payload)

    solar_plan = await load_solar_charging_plan_for_charger(
        session,
        site,
        charger,
        now=now,
        price_forecast=energy.price_forecast if energy else (),
        current_price=energy.electricity_price_eur_kwh if energy else None,
        config=config,
    )

    return build_energy_reasoning(
        charger=charger,
        site=site,
        energy=energy,
        solar_plan=solar_plan,
        energy_flow_line=energy_flow_line,
        energy_balance_status=energy_balance_status,
        active_optimizations=active_optimizations,
        vehicle_context=vehicle_context,
        now=now,
    )


def _energy_flow_line_from_payload(payload: dict[str, Any]) -> str | None:
    pv = payload.get("sungrow_pv_power_w")
    load = payload.get("sungrow_load_power_w")
    ev = payload.get("halo_power_w")
    if pv is None and load is None and ev is None:
        return None

    def fmt(value: Any) -> str:
        if not isinstance(value, (int, float)):
            return "—"
        return f"{value / 1000:.1f}kW"

    return f"PV {fmt(pv)} → Load {fmt(load)} | EV {fmt(ev)}"
