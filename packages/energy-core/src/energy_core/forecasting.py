"""Seasonal energy and financial forecasts calibrated from site history."""

from __future__ import annotations

from calendar import monthrange
from collections.abc import Iterable
from dataclasses import dataclass, fields
from datetime import date, timedelta

from energy_core.db.repositories import FinancialStat

SOLAR_PROFILE = (0.08, 0.18, 0.55, 1.1, 1.55, 1.75, 1.65, 1.35, 0.8, 0.35, 0.12, 0.05)
BATTERY_PROFILE = (0.3, 0.4, 0.75, 1.1, 1.35, 1.45, 1.4, 1.25, 0.9, 0.6, 0.4, 0.3)
IMPORT_PROFILE = (1.35, 1.25, 1.1, 0.9, 0.75, 0.68, 0.66, 0.72, 0.9, 1.1, 1.25, 1.4)


@dataclass(frozen=True, slots=True)
class ForecastValues:
    solar_self_consumed_kwh: float = 0.0
    battery_self_consumed_kwh: float = 0.0
    exported_kwh: float = 0.0
    imported_kwh: float = 0.0
    solar_savings_sek: float = 0.0
    battery_savings_sek: float = 0.0
    export_revenue_sek: float = 0.0
    grid_import_cost_sek: float = 0.0
    net_sek: float = 0.0


@dataclass(frozen=True, slots=True)
class MonthlyForecast:
    month: str
    actual: ForecastValues
    forecast: ForecastValues
    total: ForecastValues


@dataclass(frozen=True, slots=True)
class YearForecast:
    year: int
    observed_days: int
    confidence: str
    uncertainty_pct: int
    actual: ForecastValues
    forecast: ForecastValues
    total: ForecastValues
    months: tuple[MonthlyForecast, ...]


def build_year_forecast(
    history: Iterable[FinancialStat],
    *,
    target_year: int,
    today: date,
    purchase_price_sek_kwh: float,
    export_compensation_sek_kwh: float,
    monthly_import_baseline: dict[int, float] | None = None,
) -> YearForecast:
    records = list(history)
    parsed = [(date.fromisoformat(record.period_start), record) for record in records]
    observed_days = len({day for day, _ in parsed})
    confidence, uncertainty = _confidence(observed_days)
    calibration = _calibrate(parsed)

    actual_by_month = {month: ForecastValues() for month in range(1, 13)}
    target_days: list[date] = []
    for day, record in parsed:
        if day.year != target_year:
            continue
        actual_by_month[day.month] = _add(actual_by_month[day.month], _actual_values(record))
        target_days.append(day)

    forecast_start = _forecast_start(target_year, today, target_days)
    forecast_by_month = {month: ForecastValues() for month in range(1, 13)}
    if forecast_start is not None:
        end = date(target_year, 12, 31)
        day = forecast_start
        while day <= end:
            energy = _forecast_energy(
                day,
                calibration,
                monthly_import_baseline=monthly_import_baseline,
            )
            values = ForecastValues(
                solar_self_consumed_kwh=energy.solar_self_consumed_kwh,
                battery_self_consumed_kwh=energy.battery_self_consumed_kwh,
                exported_kwh=energy.exported_kwh,
                imported_kwh=energy.imported_kwh,
                solar_savings_sek=energy.solar_self_consumed_kwh * purchase_price_sek_kwh,
                battery_savings_sek=energy.battery_self_consumed_kwh * purchase_price_sek_kwh,
                export_revenue_sek=energy.exported_kwh * export_compensation_sek_kwh,
                grid_import_cost_sek=energy.imported_kwh * purchase_price_sek_kwh,
                net_sek=(
                    (energy.solar_self_consumed_kwh + energy.battery_self_consumed_kwh)
                    * purchase_price_sek_kwh
                    + energy.exported_kwh * export_compensation_sek_kwh
                    - energy.imported_kwh * purchase_price_sek_kwh
                ),
            )
            forecast_by_month[day.month] = _add(forecast_by_month[day.month], values)
            day += timedelta(days=1)

    months = tuple(
        MonthlyForecast(
            month=f"{target_year}-{month:02d}",
            actual=_rounded(actual_by_month[month]),
            forecast=_rounded(forecast_by_month[month]),
            total=_rounded(_add(actual_by_month[month], forecast_by_month[month])),
        )
        for month in range(1, 13)
    )
    actual = _rounded(_sum(month.actual for month in months))
    forecast = _rounded(_sum(month.forecast for month in months))
    return YearForecast(
        year=target_year,
        observed_days=observed_days,
        confidence=confidence,
        uncertainty_pct=uncertainty,
        actual=actual,
        forecast=forecast,
        total=_rounded(_add(actual, forecast)),
        months=months,
    )


def _calibrate(parsed: list[tuple[date, FinancialStat]]) -> dict[str, float]:
    definitions = {
        "solar": ("solar_self_consumed_kwh", SOLAR_PROFILE),
        "battery": ("battery_self_consumed_kwh", BATTERY_PROFILE),
        "export": ("exported_kwh", SOLAR_PROFILE),
        "import": ("imported_kwh", IMPORT_PROFILE),
    }
    result: dict[str, float] = {}
    for key, (attribute, profile) in definitions.items():
        total_value = sum(float(getattr(record, attribute)) for _, record in parsed)
        total_weight = sum(profile[day.month - 1] for day, _ in parsed)
        result[key] = total_value / total_weight if total_weight > 0 else 0.0
    return result


def _forecast_energy(
    day: date,
    calibration: dict[str, float],
    *,
    monthly_import_baseline: dict[int, float] | None,
) -> ForecastValues:
    month = day.month - 1
    imported_kwh = calibration["import"] * IMPORT_PROFILE[month]
    if monthly_import_baseline and day.month in monthly_import_baseline:
        imported_kwh = monthly_import_baseline[day.month] / monthrange(day.year, day.month)[1]
    return ForecastValues(
        solar_self_consumed_kwh=calibration["solar"] * SOLAR_PROFILE[month],
        battery_self_consumed_kwh=calibration["battery"] * BATTERY_PROFILE[month],
        exported_kwh=calibration["export"] * SOLAR_PROFILE[month],
        imported_kwh=imported_kwh,
    )


def _forecast_start(target_year: int, today: date, actual_days: list[date]) -> date | None:
    if target_year < today.year:
        return None
    if target_year > today.year:
        return date(target_year, 1, 1)
    latest_actual = max(actual_days, default=date(target_year, 1, 1) - timedelta(days=1))
    return max(today + timedelta(days=1), latest_actual + timedelta(days=1))


def _actual_values(record: FinancialStat) -> ForecastValues:
    net = (
        record.solar_savings_sek
        + record.battery_savings_sek
        + record.export_revenue_sek
        - record.grid_import_cost_sek
    )
    return ForecastValues(
        solar_self_consumed_kwh=record.solar_self_consumed_kwh,
        battery_self_consumed_kwh=record.battery_self_consumed_kwh,
        exported_kwh=record.exported_kwh,
        imported_kwh=record.imported_kwh,
        solar_savings_sek=record.solar_savings_sek,
        battery_savings_sek=record.battery_savings_sek,
        export_revenue_sek=record.export_revenue_sek,
        grid_import_cost_sek=record.grid_import_cost_sek,
        net_sek=net,
    )


def _add(left: ForecastValues, right: ForecastValues) -> ForecastValues:
    return ForecastValues(
        **{
            field.name: getattr(left, field.name) + getattr(right, field.name)
            for field in fields(ForecastValues)
        }
    )


def _sum(values: Iterable[ForecastValues]) -> ForecastValues:
    total = ForecastValues()
    for value in values:
        total = _add(total, value)
    return total


def _rounded(value: ForecastValues) -> ForecastValues:
    return ForecastValues(
        **{
            field.name: round(getattr(value, field.name), 2)
            for field in fields(ForecastValues)
        }
    )


def _confidence(observed_days: int) -> tuple[str, int]:
    if observed_days < 14:
        return "very_low", 45
    if observed_days < 45:
        return "low", 35
    if observed_days < 120:
        return "medium", 25
    return "high", 15
