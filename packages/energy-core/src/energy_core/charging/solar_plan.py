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


# Planned solar below this is too small to be worth deferring grid charging for.
MIN_USEFUL_SOLAR_KWH = 1.5


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

    if forecast is None:
        return SolarChargingPlan(
            expected_usable_solar_kwh=0.0,
            planning_solar_kwh=0.0,
            quality="INSUFFICIENT_DATA",
            confidence=0.0,
            expected_solar_window_start=None,
            expected_solar_window_end=None,
            cheapest_grid_window=None,
            explanation_sv="Ingen solprognos tillgänglig — nätladdning planeras efter elpris.",
            reason_code="solar_forecast_unavailable",
            solar_first=False,
        )

    expected = expected_solar_before_deadline(forecast, now=now, deadline=deadline)
    factor = planning_factor(forecast.quality, cfg)
    planning = expected * factor

    win_start, win_end = solar_window(forecast, now=now, deadline=deadline)
    solar_first = planning >= MIN_USEFUL_SOLAR_KWH and win_start is not None

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
    if price_forecast:
        tz = ZoneInfo(timezone)
        cheap_hours = sorted(price_forecast, key=lambda x: x[1])[:charge_hours]
        if cheap_hours:
            times = [h[0].astimezone(tz).strftime("%H:%M") for h in cheap_hours]
            cheapest_window = f"{min(times)}–{max(times)}"

    if solar_first:
        window = _format_window(win_start, win_end, timezone)
        explanation = (
            f"Solöverskott väntas {window} innan deadline "
            f"(träffsäkerhet {forecast.confidence * 100:.0f} %). "
            f"Solel prioriteras och nätladdning väntar tills deadline närmar sig."
        )
        reason = "solar_forecast_wait"
    else:
        explanation = (
            "För lite solöverskott väntas innan deadline — "
            "nätladdning planeras vid billiga timmar."
        )
        if cheapest_window:
            explanation += f" Billigaste nät-fönster: {cheapest_window}."
        reason = "solar_forecast_grid_required"

    if not charge and not solar_first and price_reason == "smart_wait_cheaper":
        explanation += " Väntar på billigare timmar för planerad nätladdning."

    return SolarChargingPlan(
        expected_usable_solar_kwh=expected,
        planning_solar_kwh=planning,
        quality=forecast.quality,
        confidence=forecast.confidence,
        expected_solar_window_start=win_start,
        expected_solar_window_end=win_end,
        cheapest_grid_window=cheapest_window,
        explanation_sv=explanation,
        reason_code=reason,
        solar_first=solar_first,
    )


def _format_window(start: datetime | None, end: datetime | None, timezone: str) -> str:
    if start is None:
        return "senare idag"
    tz = ZoneInfo(timezone)
    start_label = start.astimezone(tz).strftime("%H:%M")
    if end is None or end <= start:
        return f"från {start_label}"
    return f"{start_label}–{end.astimezone(tz).strftime('%H:%M')}"


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
        deadline=deadline,
        now=now,
        timezone=config.timezone,
        price_forecast=price_forecast,
        current_price=current_price,
        departure_time=config.departure_time,
        charge_hours=int(config.smart_charge_hours),
        expensive_threshold=config.expensive_price_eur_kwh,
    )
