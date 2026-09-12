"""GridX live payload parsing tests."""

from __future__ import annotations

import pytest

from energy_core.domain import reading_is_actionable
from energy_core.integrations.heartbeat.gridx_readings import gridx_live_to_raw_reading


def test_gridx_live_to_raw_reading_maps_power_fields():
    reading = gridx_live_to_raw_reading(
        "summer-house-denmark",
        {
            "measuredAt": "2026-09-12T07:56:49Z",
            "grid": 1495.494,
            "photovoltaic": 490.0,
            "consumption": 1902.7,
            "battery": {"power": -200.0, "stateOfCharge": 0.03},
        },
    )
    assert reading.site_slug == "summer-house-denmark"
    assert reading.grid_import_w == 1495.494
    assert reading.solar_production_w == 490.0
    assert reading.consumption_w == 1902.7
    assert reading.battery_soc_pct == pytest.approx(3.0)
    # GridX negative power = charging → EMIC positive
    assert reading.battery_power_w == 200.0
    assert reading.present_fields == frozenset(
        {
            "grid_import_w",
            "solar_production_w",
            "consumption_w",
            "battery_soc_pct",
            "battery_power_w",
        }
    )
    assert reading_is_actionable(reading) is True


def test_gridx_live_to_raw_reading_inverts_battery_discharge_sign():
    reading = gridx_live_to_raw_reading(
        "summer-house-denmark",
        {"battery": {"power": 350.0, "stateOfCharge": 0.55}},
    )
    # GridX positive power = discharging → EMIC negative
    assert reading.battery_power_w == -350.0


def test_gridx_live_to_raw_reading_export_grid():
    reading = gridx_live_to_raw_reading(
        "summer-house-denmark",
        {"grid": -500.0, "photovoltaic": 1000.0, "consumption": 400.0},
    )
    assert reading.grid_export_w == 500.0
    assert reading.grid_import_w == 0.0
