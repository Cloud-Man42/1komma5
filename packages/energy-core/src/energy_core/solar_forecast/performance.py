"""Weather-normalized solar performance derived from daily observations."""

from __future__ import annotations

from datetime import UTC, date, datetime

from energy_core.config import Settings, get_settings
from energy_core.solar_forecast.calibration import is_outlier_ratio
from energy_core.solar_forecast.physical import baseline_energy_kwh
from energy_core.solar_forecast.types import SolarForecast, SolarForecastObservation, SolarForecastPoint

MIN_EXPECTED_KWH = 0.5


def performance_ratio(actual_kwh: float | None, expected_kwh: float | None) -> float | None:
    """Actual production divided by weather-normalized (physical) expectation."""
    if actual_kwh is None or expected_kwh is None or expected_kwh < MIN_EXPECTED_KWH:
        return None
    return round(actual_kwh / expected_kwh, 3)


def forecast_expected_kwh_for_comparison(obs: SolarForecastObservation) -> float | None:
    """User-facing forecast total for prognos-vs-verklig charts (corrected, not raw physics)."""
    return obs.forecast_kwh_corrected or obs.forecast_kwh_raw or obs.physical_kwh


def observation_to_performance_day(obs: SolarForecastObservation) -> dict | None:
    expected = forecast_expected_kwh_for_comparison(obs)
    ratio = performance_ratio(obs.actual_kwh, expected)
    if ratio is None:
        return None
    return {
        "date": obs.forecast_date.isoformat(),
        "actual_kwh": obs.actual_kwh,
        "expected_kwh": expected,
        "performance_ratio": ratio,
        "anomaly_flag": bool(ratio < 0.7 and (obs.actual_kwh or 0) > 2.0),
    }


def performance_days_from_observations(
    observations: list[SolarForecastObservation],
) -> list[dict]:
    days: list[dict] = []
    for obs in sorted(observations, key=lambda o: o.forecast_date):
        row = observation_to_performance_day(obs)
        if row is not None:
            days.append(row)
    return days


def raw_forecast_kwh_for_points(points: list[SolarForecastPoint]) -> float:
    return round(sum(baseline_energy_kwh(p.baseline_power_w) for p in points), 3)


def raw_forecast_so_far(
    forecast: SolarForecast,
    *,
    timezone: str,
    now: datetime | None = None,
) -> tuple[float, float]:
    """Return (raw_kwh_so_far, raw_kwh_full_day) for the local calendar day at ``now``."""
    from energy_core.solar_forecast.day_metrics import today_forecast_points

    when = now or datetime.now(UTC)
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)

    today_pts = today_forecast_points(forecast.points, timezone=timezone, now=when)
    if not today_pts:
        stored = float(getattr(forecast, "raw_forecast_today_kwh", 0.0) or 0.0)
        return 0.0, stored

    past = [p for p in today_pts if p.timestamp.astimezone(UTC) <= when]
    so_far = raw_forecast_kwh_for_points(past)
    full_day = raw_forecast_kwh_for_points(today_pts)
    return so_far, full_day


def today_deviation_pct(actual_kwh: float, raw_expected_so_far_kwh: float | None) -> float | None:
    if raw_expected_so_far_kwh is None or raw_expected_so_far_kwh < MIN_EXPECTED_KWH:
        return None
    return round(((actual_kwh - raw_expected_so_far_kwh) / raw_expected_so_far_kwh) * 100.0, 1)


def estimate_raw_so_far_from_totals(
    *,
    raw_today_kwh: float | None,
    corrected_so_far_kwh: float | None,
    corrected_today_kwh: float | None,
) -> float | None:
    """Fallback when point-level baselines are missing (e.g. intelligence refresh)."""
    if not raw_today_kwh or raw_today_kwh < MIN_EXPECTED_KWH:
        return None
    if not corrected_so_far_kwh or not corrected_today_kwh or corrected_today_kwh <= 0:
        return None
    fraction = min(1.0, corrected_so_far_kwh / corrected_today_kwh)
    return round(raw_today_kwh * fraction, 3)


def average_ratio(
    days: list[dict],
    *,
    last_n: int | None = None,
    settings: Settings | None = None,
) -> float | None:
    cfg = settings or get_settings()
    subset = days[-last_n:] if last_n is not None else days
    ratios = [
        d["performance_ratio"]
        for d in subset
        if d.get("performance_ratio") is not None and not is_outlier_ratio(d["performance_ratio"], cfg)
    ]
    if not ratios:
        return None
    return round(sum(ratios) / len(ratios), 3)


def build_performance_summary(
    days: list[dict],
    *,
    actual_today_kwh: float | None = None,
    raw_forecast_so_far_kwh: float | None = None,
    settings: Settings | None = None,
) -> dict:
    cfg = settings or get_settings()
    return {
        "headline_ratio": average_ratio(days, last_n=30, settings=cfg)
        or average_ratio(days, last_n=7, settings=cfg),
        "today_deviation_pct": (
            today_deviation_pct(actual_today_kwh, raw_forecast_so_far_kwh)
            if actual_today_kwh is not None
            else None
        ),
        "week_avg": average_ratio(days, last_n=7, settings=cfg),
        "month_avg": average_ratio(days, last_n=30, settings=cfg),
        "quarter_avg": average_ratio(days, last_n=90, settings=cfg),
        "ytd_avg": average_ratio(days, settings=cfg),
    }
