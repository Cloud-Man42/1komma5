"""Advisory solar charging planner — does not control live current."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.charging.config import ChargingConfig
from energy_core.charging.smart_schedule import should_charge_smart
from energy_core.db.models import EvChargerModel, SiteModel
from energy_core.db.solar_forecast_repo import SolarForecastRepository
from energy_core.solar_forecast.constants import PLANNING_FACTORS
from energy_core.solar_forecast.types import ForecastQuality, SolarChargingPlan, SolarForecast


@dataclass(frozen=True, slots=True)
class SolarPlannerConfig:
    high_factor: float = PLANNING_FACTORS["HIGH"]
    medium_factor: float = PLANNING_FACTORS["MEDIUM"]
    low_factor: float = PLANNING_FACTORS["LOW"]
    insufficient_factor: float = PLANNING_FACTORS["INSUFFICIENT_DATA"]


def planning_factor(quality: ForecastQuality, config: SolarPlannerConfig | None = None) -> float:
    cfg = config or SolarPlannerConfig()
    return {
        "HIGH": cfg.high_factor,
        "MEDIUM": cfg.medium_factor,
        "LOW": cfg.low_factor,
        "INSUFFICIENT_DATA": cfg.insufficient_factor,
    }[quality]


def expected_solar_before_deadline(
    forecast: SolarForecast,
    *,
    now: datetime,
    deadline: datetime,
) -> float:
    """Sum expected usable solar energy kWh from now until deadline."""
    if deadline <= now:
        return 0.0
    total = 0.0
    for p in forecast.points:
        if now <= p.timestamp < deadline:
            total += p.expected_energy_kwh
    return total


def solar_window(
    forecast: SolarForecast,
    *,
    now: datetime,
    deadline: datetime,
    min_power_w: float = 500.0,
) -> tuple[datetime | None, datetime | None]:
    start: datetime | None = None
    end: datetime | None = None
    for p in forecast.points:
        if p.timestamp < now or p.timestamp >= deadline:
            continue
        if p.corrected_power_w >= min_power_w:
            if start is None:
                start = p.timestamp
            end = p.timestamp
    return start, end


def build_solar_charging_plan(
    *,
    forecast: SolarForecast | None,
    ev_required_kwh: float,
    deadline: datetime,
    now: datetime,
    timezone: str,
    price_forecast: tuple[tuple[datetime, float], ...] = (),
    current_price: float | None = None,
    departure_time: str | None = None,
    charge_hours: int = 4,
    expensive_threshold: float = 0.35,
    config: SolarPlannerConfig | None = None,
) -> SolarChargingPlan:
    cfg = config or SolarPlannerConfig()

    if forecast is None or ev_required_kwh <= 0:
        return SolarChargingPlan(
            expected_usable_solar_kwh=0.0,
            planning_solar_kwh=0.0,
            reserved_solar_kwh=0.0,
            planned_grid_kwh=ev_required_kwh,
            quality="INSUFFICIENT_DATA",
            confidence=0.0,
            expected_solar_window_start=None,
            expected_solar_window_end=None,
            cheapest_grid_window=None,
            explanation_sv="Ingen solprognos tillgänglig — planerar nätenergi.",
            reason_code="solar_forecast_unavailable",
        )

    expected = expected_solar_before_deadline(forecast, now=now, deadline=deadline)
    factor = planning_factor(forecast.quality, cfg)
    planning = expected * factor
    reserved = min(ev_required_kwh, planning)
    grid_needed = max(0.0, ev_required_kwh - reserved)

    win_start, win_end = solar_window(forecast, now=now, deadline=deadline)

    charge, price_reason = should_charge_smart(
        now,
        departure_time=departure_time,
        price_forecast=price_forecast,
        current_price=current_price,
        expensive_threshold=expensive_threshold,
        charge_hours=charge_hours,
        timezone=timezone,
    )

    cheapest_window: str | None = None
    if grid_needed > 0 and price_forecast:
        tz = ZoneInfo(timezone)
        cheap_hours = sorted(price_forecast, key=lambda x: x[1])[:charge_hours]
        if cheap_hours:
            times = [h[0].astimezone(tz).strftime("%H:%M") for h in cheap_hours]
            cheapest_window = f"{min(times)}–{max(times)}"

    if grid_needed <= 0.01:
        explanation = (
            f"Bilen behöver {ev_required_kwh:.1f} kWh. "
            f"EMIC prognostiserar {expected:.1f} kWh användbart solöverskott "
            f"innan deadline (confidence {forecast.confidence * 100:.0f}%). "
            f"Väntar med nätladdning och reserverar solel till EV."
        )
        reason = "solar_forecast_wait"
    elif reserved > 0:
        explanation = (
            f"Bilen behöver {ev_required_kwh:.1f} kWh. "
            f"Förväntad solel: {expected:.1f} kWh (planeringsvärde {planning:.1f} kWh). "
            f"Reserverad solel: {reserved:.1f} kWh. "
            f"Planerad nätenergi: {grid_needed:.1f} kWh."
        )
        if cheapest_window:
            explanation += f" Billigaste nät-fönster: {cheapest_window}."
        reason = "solar_forecast_partial_grid"
    else:
        explanation = (
            f"Förväntad solel otillräcklig ({expected:.1f} kWh). "
            f"Planerar {grid_needed:.1f} kWh från nätet."
        )
        reason = "solar_forecast_grid_required"

    if not charge and grid_needed > 0 and price_reason == "smart_wait_cheaper":
        explanation += " Väntar på billigare timmar för planerad nätladdning."

    return SolarChargingPlan(
        expected_usable_solar_kwh=expected,
        planning_solar_kwh=planning,
        reserved_solar_kwh=reserved,
        planned_grid_kwh=grid_needed,
        quality=forecast.quality,
        confidence=forecast.confidence,
        expected_solar_window_start=win_start,
        expected_solar_window_end=win_end,
        cheapest_grid_window=cheapest_window,
        explanation_sv=explanation,
        reason_code=reason,
    )


def charging_config_from_models(charger: EvChargerModel, site: SiteModel) -> ChargingConfig:
    return ChargingConfig(
        max_current_a=charger.max_current_a,
        min_current_a=charger.min_current_a,
        phases=charger.phases,
        nominal_voltage_v=charger.nominal_voltage_v,
        max_power_w=charger.max_power_w,
        max_grid_import_w=charger.max_grid_import_w,
        main_fuse_a=site.main_fuse_a,
        safety_margin_a=site.safety_margin_a,
        solar_start_threshold_w=charger.solar_start_threshold_w,
        solar_stop_threshold_w=charger.solar_stop_threshold_w,
        solar_start_delay_seconds=float(charger.solar_start_delay_seconds),
        solar_stop_delay_seconds=float(charger.solar_stop_delay_seconds),
        timezone=site.timezone or "Europe/Stockholm",
        required_energy_kwh=charger.required_energy_kwh,
        deadline_at=charger.deadline_at,
        departure_time=charger.departure_time,
        start_delay_seconds=float(charger.start_delay_seconds),
        stop_delay_seconds=float(charger.stop_delay_seconds),
        minimum_run_time_seconds=float(charger.minimum_run_time_seconds),
        minimum_off_time_seconds=float(charger.minimum_off_time_seconds),
        temporary_grid_import_allowance_w=charger.temporary_grid_import_allowance_w,
        temporary_grid_import_seconds=float(charger.temporary_grid_import_seconds),
        grid_deadband_w=charger.grid_deadband_w,
        minimum_current_change_interval_seconds=float(charger.minimum_current_change_interval_seconds),
        max_current_increase_per_step_a=charger.max_current_increase_per_step_a,
        max_current_decrease_per_step_a=charger.max_current_decrease_per_step_a,
        max_automatic_starts_per_hour=charger.max_automatic_starts_per_hour,
    )


async def load_solar_charging_plan_for_charger(
    session: AsyncSession,
    site: SiteModel,
    charger: EvChargerModel,
    *,
    now: datetime | None = None,
    price_forecast: tuple[tuple[datetime, float], ...] = (),
    current_price: float | None = None,
) -> SolarChargingPlan | None:
    from energy_core.charging.optimizer import _deadline_from_departure

    config = charging_config_from_models(charger, site)
    if config.required_energy_kwh is None or config.required_energy_kwh <= 0:
        return None

    now = now or datetime.now(UTC)
    deadline = config.deadline_at or _deadline_from_departure(
        now, config.departure_time, config.timezone
    )
    if deadline is None:
        return None

    forecast_repo = SolarForecastRepository(session)
    forecast = await forecast_repo.get_latest(site.id)
    return build_solar_charging_plan(
        forecast=forecast,
        ev_required_kwh=config.required_energy_kwh,
        deadline=deadline,
        now=now,
        timezone=config.timezone,
        price_forecast=price_forecast,
        current_price=current_price,
        departure_time=config.departure_time,
        charge_hours=int(config.smart_charge_hours),
        expensive_threshold=config.expensive_price_eur_kwh,
    )
