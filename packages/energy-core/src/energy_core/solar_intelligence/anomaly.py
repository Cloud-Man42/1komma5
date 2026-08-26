"""Weather-normalized performance and anomaly detection."""

from __future__ import annotations

from datetime import date

from energy_core.solar_intelligence.types import PerformanceDaily


def compute_performance_daily(
    *,
    performance_date: date,
    actual_kwh: float | None,
    expected_kwh: float | None,
) -> PerformanceDaily:
    ratio = None
    normalized = expected_kwh
    if actual_kwh is not None and expected_kwh is not None and expected_kwh > 0.5:
        ratio = actual_kwh / expected_kwh
    anomaly_score = None
    anomaly_flag = False
    if ratio is not None:
        anomaly_score = round((1.0 - ratio) * 100.0, 1)
        if ratio < 0.7 and actual_kwh is not None and actual_kwh > 2.0:
            anomaly_flag = True
    return PerformanceDaily(
        performance_date=performance_date,
        actual_kwh=actual_kwh,
        expected_kwh=expected_kwh,
        weather_normalized_kwh=normalized,
        performance_ratio=round(ratio, 3) if ratio is not None else None,
        anomaly_score=anomaly_score,
        anomaly_flag=anomaly_flag,
    )


def rolling_underperformance_days(records: list[PerformanceDaily], *, window: int = 7) -> float | None:
    recent = [r for r in records if r.performance_ratio is not None][-window:]
    if len(recent) < 3:
        return None
    return sum(r.performance_ratio or 0.0 for r in recent) / len(recent)
