"""Tests for HeartBeat live-overview to RawEnergyReading mapping."""

from datetime import UTC, datetime

from energy_core.heartbeat.readings import live_overview_to_raw_reading


def _hero_overview(**overrides):
    data = {
        "timestamp": "2026-08-13T18:00:00Z",
        "status": "ONLINE",
        "liveHeroView": {
            "production": {"value": 4500},
            "consumption": {"value": 2100},
            "gridConsumption": {"value": 300},
            "gridFeedIn": {"value": 0},
            "totalStateOfCharge": 0.42,
        },
        "summaryCards": {
            "battery": {"power": {"value": -500}, "stateOfCharge": 42},
            "grid": {"power": {"value": 300}},
        },
    }
    data.update(overrides)
    return data


def test_live_overview_to_raw_reading_from_hero_view():
    reading = live_overview_to_raw_reading("akarp", _hero_overview())
    assert reading.site_slug == "akarp"
    assert reading.recorded_at == datetime(2026, 8, 13, 18, 0, tzinfo=UTC)
    assert reading.solar_production_w == 4500
    assert reading.consumption_w == 2100
    assert reading.grid_import_w == 300
    assert reading.grid_export_w == 0
    assert reading.battery_soc_pct == 42
    assert reading.battery_power_w == 500


def test_live_overview_derives_grid_from_signed_power():
    data = _hero_overview(
        liveHeroView={
            "production": {"value": 1000},
            "consumption": {"value": 500},
            "totalStateOfCharge": 0.5,
        },
        summaryCards={"grid": {"power": {"value": -800}}},
    )
    reading = live_overview_to_raw_reading("akarp", data)
    assert reading.grid_import_w == 0
    assert reading.grid_export_w == 800


def test_live_overview_handles_missing_optional_fields():
    reading = live_overview_to_raw_reading(
        "akarp",
        {"timestamp": "2026-08-13T12:00:00Z", "liveHeroView": {}},
    )
    assert reading.solar_production_w == 0
    assert reading.consumption_w == 0
    assert reading.grid_import_w == 0
    assert reading.grid_export_w == 0
    assert reading.battery_soc_pct == 0
