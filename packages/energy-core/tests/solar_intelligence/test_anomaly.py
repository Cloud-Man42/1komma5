"""Tests for anomaly detection."""

from datetime import date

import pytest

from energy_core.solar_intelligence.anomaly import compute_performance_daily, rolling_underperformance_days


def test_anomaly_flag_when_underperforming():
    perf = compute_performance_daily(performance_date=date(2026, 8, 1), actual_kwh=5.0, expected_kwh=20.0)
    assert perf.anomaly_flag is True
    assert perf.performance_ratio == pytest.approx(0.25)


def test_no_anomaly_when_on_target():
    perf = compute_performance_daily(performance_date=date(2026, 8, 1), actual_kwh=18.0, expected_kwh=20.0)
    assert perf.anomaly_flag is False


def test_rolling_underperformance():
    from energy_core.solar_intelligence.types import PerformanceDaily

    records = [
        PerformanceDaily(date(2026, 8, d), 10.0, 20.0, 20.0, 0.5, 50.0, False)
        for d in range(1, 8)
    ]
    avg = rolling_underperformance_days(records)
    assert avg == pytest.approx(0.5)
