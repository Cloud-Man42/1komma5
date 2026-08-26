"""Smart charging signal adapter — exposes forecast fields without changing optimizer."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from energy_core.solar_intelligence.types import HourlyForecastPoint


def build_charging_signals(
    *,
    hourly: list[HourlyForecastPoint],
    expected_today_kwh: float,
    now: datetime,
    timezone: str,
    confidence: float,
) -> dict[str, float | str | None]:
    tz = ZoneInfo(timezone)
    future = [p for p in hourly if p.timestamp > now and p.corrected_w > 100]
    peak_w = max((p.corrected_w for p in future), default=0.0)
    peak_time = next((p.timestamp for p in future if p.corrected_w == peak_w), None)

    # Best 2-hour window with highest average power (future only)
    best_window: tuple[datetime, datetime] | None = None
    best_avg = 0.0
    if future:
        for i, start_p in enumerate(future):
            window_end = start_p.timestamp + timedelta(hours=2)
            window_pts = [p for p in future if start_p.timestamp <= p.timestamp < window_end]
            if not window_pts:
                continue
            avg = sum(p.corrected_w for p in window_pts) / len(window_pts)
            if avg > best_avg:
                best_avg = avg
                best_window = (start_p.timestamp, window_end)

    surplus = max(0.0, expected_today_kwh * 0.3)  # conservative surplus estimate

    return {
        "expectedSolarKwh": round(expected_today_kwh, 2),
        "expectedPeakPvPower": round(peak_w, 0),
        "expectedPeakPvTime": peak_time.isoformat() if peak_time else None,
        "bestSolarChargingWindow": (
            f"{best_window[0].astimezone(tz).strftime('%H:%M')}-{best_window[1].astimezone(tz).strftime('%H:%M')}"
            if best_window
            else None
        ),
        "expectedSurplusKwh": round(surplus, 2),
        "forecastConfidence": round(confidence, 1),
    }
