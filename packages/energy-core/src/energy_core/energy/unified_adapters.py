"""Adapters from legacy EMIC state models to UnifiedEnergyState."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from energy_core.energy.state import EnergyState
from energy_core.energy.unified import (
    BatterySection,
    DataFreshness,
    EvSection,
    ForecastSection,
    GridSection,
    HealthSection,
    HouseSection,
    HvacSection,
    PricesSection,
    ProviderHealth,
    ProviderHealthStatus,
    SolarSection,
    SpaSection,
    UnifiedEnergyState,
    WeatherSection,
)
from energy_core.energy_state.models import EnergySiteSnapshot, EvState


def _w_to_kw(value: float | None) -> float | None:
    if value is None:
        return None
    return value / 1000.0


def _parse_freshness(value: str | None) -> DataFreshness:
    if not value:
        return DataFreshness.UNKNOWN
    try:
        return DataFreshness(value.upper())
    except ValueError:
        return DataFreshness.UNKNOWN


def from_energy_state(
    state: EnergyState,
    *,
    site_id: int,
    site_slug: str,
) -> UnifiedEnergyState:
    """Map charging-policy EnergyState (W-based) to UnifiedEnergyState."""
    charge_kw = _w_to_kw(state.battery_charge_power_w)
    discharge_kw = _w_to_kw(state.battery_discharge_power_w)
    battery_power_kw = _w_to_kw(state.battery_power_w)

    if charge_kw is not None and charge_kw > 0:
        battery_state = "charging"
    elif discharge_kw is not None and discharge_kw > 0:
        battery_state = "discharging"
    else:
        battery_state = None

    ev_charging = (state.ev_actual_power_w or 0) > 0
    ev_connected = state.ev_actual_power_w is not None or state.ev_soc is not None

    return UnifiedEnergyState(
        site_id=site_id,
        site_slug=site_slug,
        timestamp=state.timestamp,
        data_freshness=DataFreshness.STALE if state.stale else DataFreshness.LIVE,
        age_seconds=state.data_age_seconds,
        stale=state.stale,
        solar=SolarSection(production_kw=_w_to_kw(state.pv_power_w)),
        grid=GridSection(
            import_kw=_w_to_kw(state.grid_import_w),
            export_kw=_w_to_kw(state.grid_export_w),
        ),
        battery=BatterySection(
            soc_percent=state.battery_soc,
            charge_kw=charge_kw,
            discharge_kw=discharge_kw,
            state=battery_state,
        ),
        house=HouseSection(consumption_kw=_w_to_kw(state.home_consumption_w)),
        ev=EvSection(
            connected=ev_connected,
            charging=ev_charging,
            power_kw=_w_to_kw(state.ev_actual_power_w),
            soc_percent=state.ev_soc,
            target_soc=state.target_soc,
            departure_time=state.departure_time,
        ),
        prices=PricesSection(
            import_price_sek_kwh=state.import_price_sek_kwh,
            import_price_eur_kwh=state.electricity_price_eur_kwh,
        ),
        forecast=ForecastSection(
            price_eur_kwh=state.electricity_price_eur_kwh,
        ),
    )


def from_site_snapshot(snapshot: EnergySiteSnapshot) -> UnifiedEnergyState:
    """Map widget/display EnergySiteSnapshot (kW-based) to UnifiedEnergyState."""
    ev_connected = snapshot.ev_state not in {EvState.UNAVAILABLE, EvState.DISCONNECTED, None}
    ev_charging = snapshot.ev_state == EvState.CHARGING

    battery_charge = snapshot.battery_power_kw if (snapshot.battery_power_kw or 0) > 0 else None
    battery_discharge = (
        abs(snapshot.battery_power_kw) if (snapshot.battery_power_kw or 0) < 0 else None
    )

    freshness = DataFreshness.STALE if snapshot.is_stale else DataFreshness.LIVE

    return UnifiedEnergyState(
        site_id=snapshot.site_id,
        site_slug=snapshot.site_slug,
        timestamp=snapshot.updated_at or datetime.now(UTC),
        data_freshness=freshness,
        age_seconds=float(snapshot.data_age_seconds or 0),
        stale=snapshot.is_stale,
        solar=SolarSection(
            production_kw=snapshot.solar_power_kw,
            today_kwh=snapshot.solar_energy_today_kwh,
        ),
        grid=GridSection(
            import_kw=snapshot.grid_import_power_kw,
            export_kw=snapshot.grid_export_power_kw,
            import_today_kwh=snapshot.grid_import_today_kwh,
            export_today_kwh=snapshot.grid_export_today_kwh,
        ),
        battery=BatterySection(
            soc_percent=snapshot.battery_soc_percent,
            charge_kw=battery_charge,
            discharge_kw=battery_discharge,
            state=snapshot.battery_state.value if snapshot.battery_state else None,
        ),
        house=HouseSection(
            consumption_kw=snapshot.house_power_kw,
            today_kwh=snapshot.house_energy_today_kwh,
        ),
        ev=EvSection(
            connected=ev_connected,
            charging=ev_charging,
            power_kw=snapshot.ev_power_kw,
            state=snapshot.ev_state.value if snapshot.ev_state else None,
        ),
        prices=PricesSection(
            import_price_eur_kwh=snapshot.current_electricity_price,
            import_price_sek_kwh=snapshot.current_electricity_price_including_fees,
        ),
    )


def from_snapshot_payload(payload: dict[str, Any]) -> UnifiedEnergyState:
    """Map site_live_snapshots JSON payload to UnifiedEnergyState."""
    site = payload.get("site") or {}
    live = payload.get("live") or {}
    today = payload.get("today") or {}
    solar = payload.get("solar") or {}
    economy = payload.get("economy") or {}
    ev = payload.get("ev") or {}
    source_status = payload.get("source_status") or {}

    generated_at_raw = payload.get("generated_at")
    if isinstance(generated_at_raw, str):
        timestamp = datetime.fromisoformat(generated_at_raw.replace("Z", "+00:00"))
    else:
        timestamp = datetime.now(UTC)

    freshness = _parse_freshness(payload.get("freshness"))
    age_seconds = float(payload.get("age_seconds") or 0)

    heartbeat_status = ProviderHealthStatus.OK if source_status.get("heartbeat") == "db_only" else ProviderHealthStatus.UNKNOWN
    forecast_status = ProviderHealthStatus.OK if source_status.get("forecast") == "db_only" else ProviderHealthStatus.UNKNOWN

    battery_power_w = live.get("battery_power_w")
    battery_charge_kw = _w_to_kw(battery_power_w) if (battery_power_w or 0) > 0 else None
    battery_discharge_kw = _w_to_kw(abs(battery_power_w)) if (battery_power_w or 0) < 0 else None

    return UnifiedEnergyState(
        site_id=int(payload.get("site_id") or 0),
        site_slug=str(site.get("slug") or ""),
        timestamp=timestamp,
        data_freshness=freshness,
        age_seconds=age_seconds,
        stale=freshness in {DataFreshness.STALE, DataFreshness.DEGRADED, DataFreshness.OFFLINE},
        solar=SolarSection(
            production_kw=_w_to_kw(live.get("solar_production_w")),
            today_kwh=today.get("produced_kwh"),
            expected_today_kwh=solar.get("expected_today_kwh"),
            remaining_kwh=solar.get("remaining_kwh"),
            confidence_pct=solar.get("confidence_pct"),
        ),
        grid=GridSection(
            import_kw=_w_to_kw(live.get("grid_import_w")),
            export_kw=_w_to_kw(live.get("grid_export_w")),
            import_today_kwh=today.get("imported_kwh"),
            export_today_kwh=today.get("exported_kwh"),
        ),
        battery=BatterySection(
            soc_percent=live.get("battery_soc_pct"),
            charge_kw=battery_charge_kw,
            discharge_kw=battery_discharge_kw,
        ),
        house=HouseSection(
            consumption_kw=_w_to_kw(live.get("consumption_w")),
            today_kwh=today.get("consumed_kwh"),
        ),
        ev=EvSection(
            connected=bool(ev.get("available")),
            charging=bool(ev.get("charging")),
            power_kw=_w_to_kw(ev.get("power_w")),
        ),
        prices=PricesSection(
            import_price_eur_kwh=economy.get("current_eur_kwh"),
            current_tier=economy.get("tier"),
        ),
        forecast=ForecastSection(solar_kwh_today=solar.get("expected_today_kwh")),
        health=HealthSection(
            heartbeat=ProviderHealth(status=heartbeat_status),
            weather=ProviderHealth(status=forecast_status),
        ),
    )
