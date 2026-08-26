"""Tests for spa site energy sample helpers."""

from datetime import UTC, datetime, timedelta

from energy_core.consumer_accounting.site_sample import (
    nearest_reading_before,
    site_energy_sample_from_reading,
)
from energy_core.db.repositories import ReadingRecord


def _reading(at: datetime, *, solar_w: float = 0.0, import_w: float = 0.0) -> ReadingRecord:
    return ReadingRecord(
        site_id=1,
        site_slug="akarp",
        recorded_at=at,
        solar_production_w=solar_w,
        consumption_w=1000.0,
        grid_import_w=import_w,
        grid_export_w=0.0,
        battery_soc_pct=50.0,
        battery_power_w=0.0,
    )


def test_nearest_reading_before_picks_latest_within_window():
    base = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)
    readings = [
        _reading(base - timedelta(minutes=4), solar_w=1000.0),
        _reading(base - timedelta(minutes=1), solar_w=3000.0),
        _reading(base + timedelta(minutes=1), solar_w=5000.0),
    ]
    match = nearest_reading_before(readings, base)
    assert match is not None
    assert match.solar_production_w == 3000.0


def test_nearest_reading_before_rejects_stale_reading():
    base = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)
    readings = [_reading(base - timedelta(minutes=10), solar_w=3000.0)]
    assert nearest_reading_before(readings, base) is None


def test_site_energy_sample_from_reading_maps_battery_sign():
    reading = _reading(datetime.now(UTC))
    reading = ReadingRecord(
        site_id=reading.site_id,
        site_slug=reading.site_slug,
        recorded_at=reading.recorded_at,
        solar_production_w=reading.solar_production_w,
        consumption_w=reading.consumption_w,
        grid_import_w=reading.grid_import_w,
        grid_export_w=reading.grid_export_w,
        battery_soc_pct=reading.battery_soc_pct,
        battery_power_w=-1500.0,
    )
    sample = site_energy_sample_from_reading(reading, duration_hours=1 / 60, electricity_price_sek_kwh=2.0)
    assert sample.battery_discharge_w == 1500.0
    assert sample.battery_charge_w == 0.0
