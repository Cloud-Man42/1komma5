"""Aggregate consumer intervals into hourly/daily/monthly/yearly buckets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class AggregateBucket:
    granularity: str
    period_start: datetime
    period_end: datetime
    energy_kwh: float = 0.0
    solar_direct_kwh: float = 0.0
    solar_battery_kwh: float = 0.0
    grid_battery_kwh: float = 0.0
    grid_direct_kwh: float = 0.0
    unknown_kwh: float = 0.0
    actual_cost_sek: float = 0.0
    reference_cost_sek: float = 0.0
    savings_sek: float = 0.0
    max_power_w: float = 0.0
    power_sum: float = 0.0
    power_count: int = 0
    heater_runtime_seconds: float = 0.0
    pump_runtime_seconds: float = 0.0
    quality_counts: dict[str, int] | None = None

    @property
    def avg_power_w(self) -> float | None:
        if self.power_count <= 0:
            return None
        return self.power_sum / self.power_count


def period_bounds(
    *,
    granularity: str,
    reference: datetime,
    timezone: str,
) -> tuple[datetime, datetime]:
    tz = ZoneInfo(timezone)
    local = reference.astimezone(tz)
    if granularity == "hour":
        start = local.replace(minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=1)
    elif granularity == "day":
        start = local.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif granularity == "month":
        start = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
    elif granularity == "year":
        start = local.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(year=start.year + 1)
    else:
        start = local.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(day=start.day + 1)
    return start.astimezone(UTC), end.astimezone(UTC)


def merge_interval_into_bucket(bucket: AggregateBucket, interval) -> AggregateBucket:
    quality_counts = dict(bucket.quality_counts or {})
    q = getattr(interval, "data_quality", None) or "CALCULATED"
    quality_counts[q] = quality_counts.get(q, 0) + 1
    avg_power = getattr(interval, "average_power_w", None) or 0.0
    return AggregateBucket(
        granularity=bucket.granularity,
        period_start=bucket.period_start,
        period_end=bucket.period_end,
        energy_kwh=bucket.energy_kwh + interval.energy_kwh,
        solar_direct_kwh=bucket.solar_direct_kwh + interval.solar_direct_kwh,
        solar_battery_kwh=bucket.solar_battery_kwh + interval.solar_battery_kwh,
        grid_battery_kwh=bucket.grid_battery_kwh + interval.grid_battery_kwh,
        grid_direct_kwh=bucket.grid_direct_kwh + interval.grid_direct_kwh,
        unknown_kwh=bucket.unknown_kwh + interval.unknown_kwh,
        actual_cost_sek=bucket.actual_cost_sek + interval.actual_cost_sek,
        reference_cost_sek=bucket.reference_cost_sek + (interval.reference_cost_sek or 0.0),
        savings_sek=bucket.savings_sek + (interval.savings_sek or 0.0),
        max_power_w=max(bucket.max_power_w, avg_power),
        power_sum=bucket.power_sum + avg_power,
        power_count=bucket.power_count + (1 if avg_power > 0 else 0),
        heater_runtime_seconds=bucket.heater_runtime_seconds + interval.heater_runtime_seconds,
        pump_runtime_seconds=bucket.pump_runtime_seconds + interval.pump_runtime_seconds,
        quality_counts=quality_counts,
    )


def quality_percentages(counts: dict[str, int]) -> dict[str, float]:
    total = sum(counts.values())
    if total <= 0:
        return {"measured_pct": 0.0, "calculated_pct": 0.0, "estimated_pct": 0.0, "missing_pct": 0.0}
    return {
        "measured_pct": round(100.0 * counts.get("MEASURED", 0) / total, 1),
        "calculated_pct": round(100.0 * counts.get("CALCULATED", 0) / total, 1),
        "estimated_pct": round(100.0 * counts.get("ESTIMATED", 0) / total, 1),
        "missing_pct": round(100.0 * counts.get("MISSING", 0) / total, 1),
    }


def sum_interval_fields(intervals: list) -> dict:
    if not intervals:
        return {}
    return {
        "energy_kwh": sum(r.energy_kwh for r in intervals),
        "solar_direct_kwh": sum(r.solar_direct_kwh for r in intervals),
        "solar_battery_kwh": sum(r.solar_battery_kwh for r in intervals),
        "grid_battery_kwh": sum(r.grid_battery_kwh for r in intervals),
        "grid_direct_kwh": sum(r.grid_direct_kwh for r in intervals),
        "unknown_kwh": sum(r.unknown_kwh for r in intervals),
        "actual_cost_sek": sum(r.actual_cost_sek for r in intervals),
        "reference_cost_sek": sum(r.reference_cost_sek or 0.0 for r in intervals),
        "savings_sek": sum(r.savings_sek or 0.0 for r in intervals),
        "heater_runtime_seconds": sum(r.heater_runtime_seconds for r in intervals),
        "pump_runtime_seconds": sum(r.pump_runtime_seconds for r in intervals),
        "max_power_w": max((r.average_power_w or 0.0 for r in intervals), default=0.0),
    }


def group_intervals_by_local_period(
    intervals: list,
    *,
    granularity: str,
    timezone: str,
) -> list[tuple[datetime, list]]:
    """Group intervals by local day or month. Returns (period_start_utc, rows) sorted ascending."""
    tz = ZoneInfo(timezone)
    buckets: dict[datetime, list] = {}
    for interval in intervals:
        local = interval.start_time.astimezone(tz)
        if granularity == "month":
            key_local = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            key_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
        key_utc = key_local.astimezone(UTC)
        buckets.setdefault(key_utc, []).append(interval)
    return sorted(buckets.items(), key=lambda item: item[0])


def spa_cost_split(totals: dict, *, fallback_price_sek_kwh: float) -> dict[str, float]:
    """Map interval totals to spa UI fields.

    Energy columns are mutually exclusive:
    - solar_kwh: direct solar + solar via battery
    - battery_kwh: grid energy discharged from battery
    - grid_kwh: direct grid import

    Cost columns follow site ekonomi semantics:
    - grid_cost_sek: actual cash paid (grid direct + grid-via-battery)
    - solar_value_sek / battery_value_sek: avoided purchase (besparing), not extra cost
    """
    energy = totals.get("energy_kwh", 0.0) or 0.0
    solar_direct = totals.get("solar_direct_kwh", 0.0) or 0.0
    solar_battery = totals.get("solar_battery_kwh", 0.0) or 0.0
    grid_battery = totals.get("grid_battery_kwh", 0.0) or 0.0
    grid_direct = totals.get("grid_direct_kwh", 0.0) or 0.0
    solar_kwh = solar_direct + solar_battery
    reference = totals.get("reference_cost_sek")
    savings = totals.get("savings_sek")
    ref_price = (
        reference / energy
        if reference is not None and energy > 0
        else fallback_price_sek_kwh
    )
    solar_savings = round(solar_kwh * ref_price, 2)
    total_savings = round(savings, 2) if savings is not None else solar_savings
    battery_savings = round(max(0.0, total_savings - solar_savings), 2)
    return {
        "solar_kwh": round(solar_kwh, 3),
        "battery_kwh": round(grid_battery, 3),
        "grid_kwh": round(grid_direct, 3),
        "grid_cost_sek": round(totals.get("actual_cost_sek", 0.0) or 0.0, 2),
        "solar_value_sek": solar_savings,
        "battery_value_sek": battery_savings,
    }
