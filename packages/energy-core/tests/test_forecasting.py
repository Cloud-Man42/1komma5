from datetime import date

import pytest
from energy_core.db.repositories import FinancialStat
from energy_core.forecasting import build_year_forecast


def _stat(day: str, *, solar: float = 10, battery: float = 2, exported: float = 3, imported: float = 4):
    return FinancialStat(
        period_start=day,
        solar_self_consumed_kwh=solar,
        battery_self_consumed_kwh=battery,
        exported_kwh=exported,
        imported_kwh=imported,
        solar_savings_sek=solar * 2,
        battery_savings_sek=battery * 2,
        export_revenue_sek=exported,
        grid_import_cost_sek=imported * 2,
        market_priced_fraction=1,
    )


def test_current_year_combines_actuals_with_remaining_days():
    result = build_year_forecast(
        [_stat("2026-08-17"), _stat("2026-08-18")],
        target_year=2026,
        today=date(2026, 8, 18),
        purchase_price_sek_kwh=2,
        export_compensation_sek_kwh=1,
    )

    assert result.actual.solar_self_consumed_kwh == 20
    assert result.forecast.solar_self_consumed_kwh > 0
    assert result.total.solar_self_consumed_kwh == (
        result.actual.solar_self_consumed_kwh + result.forecast.solar_self_consumed_kwh
    )
    assert result.months[7].actual.solar_self_consumed_kwh == 20
    assert result.months[7].forecast.solar_self_consumed_kwh > 0
    assert result.confidence == "very_low"
    assert result.uncertainty_pct == 45


def test_next_year_forecasts_all_months_from_historical_calibration():
    history = [_stat(f"2026-08-{day:02d}") for day in range(1, 16)]

    result = build_year_forecast(
        history,
        target_year=2027,
        today=date(2026, 8, 18),
        purchase_price_sek_kwh=2,
        export_compensation_sek_kwh=0.8,
    )

    assert result.actual.solar_self_consumed_kwh == 0
    assert result.forecast.solar_self_consumed_kwh > 0
    assert all(month.forecast.imported_kwh > 0 for month in result.months)
    assert result.confidence == "low"
    assert result.forecast.net_sek == pytest.approx(
        result.forecast.solar_savings_sek
        + result.forecast.battery_savings_sek
        + result.forecast.export_revenue_sek
        - result.forecast.grid_import_cost_sek,
        abs=0.01,
    )


def test_monthly_import_baseline_preserves_known_annual_consumption():
    monthly_import = {
        1: 2000,
        2: 2100,
        3: 1900,
        4: 1800,
        5: 1700,
        6: 1500,
        7: 1200,
        8: 1600,
        9: 1800,
        10: 1900,
        11: 2100,
        12: 2000,
    }

    result = build_year_forecast(
        [_stat("2026-08-18")],
        target_year=2027,
        today=date(2026, 8, 18),
        purchase_price_sek_kwh=2,
        export_compensation_sek_kwh=0.8,
        monthly_import_baseline=monthly_import,
    )

    assert result.forecast.imported_kwh == pytest.approx(21600.0, abs=0.01)
    assert result.months[0].forecast.imported_kwh == pytest.approx(2000, abs=0.01)
    assert result.months[6].forecast.imported_kwh == pytest.approx(1200, abs=0.01)


def test_past_year_has_no_forecast_and_empty_history_is_safe():
    result = build_year_forecast(
        [],
        target_year=2025,
        today=date(2026, 8, 18),
        purchase_price_sek_kwh=2,
        export_compensation_sek_kwh=1,
    )

    assert result.actual.net_sek == 0
    assert result.forecast.net_sek == 0
    assert result.total.net_sek == 0
    assert result.observed_days == 0
