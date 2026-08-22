"""Tests for Sungrow Heartbeat proxy mapper."""

from datetime import UTC, datetime, timedelta

from energy_core.sungrow.heartbeat_provider import map_heartbeat_to_sungrow


def _overview(**overrides):
    data = {
        "timestamp": "2026-08-21T10:00:00Z",
        "status": "ONLINE",
        "liveHeroView": {
            "production": {"value": 5000},
            "consumption": {"value": 3000},
            "gridConsumption": {"value": 500},
            "gridFeedIn": {"value": 0},
            "totalStateOfCharge": 55,
        },
        "summaryCards": {
            "battery": {"power": {"value": 800}, "stateOfCharge": 55},
            "photovoltaic": {"production": {"value": 5000}},
        },
    }
    data.update(overrides)
    return data


def test_map_heartbeat_to_sungrow_normalizes_signs():
    now = datetime(2026, 8, 21, 10, 0, 30, tzinfo=UTC)
    snap = map_heartbeat_to_sungrow(_overview(), max_age_seconds=60, now=now)
    assert snap.pv_power_w == 5000
    assert snap.load_power_w == 3000
    assert snap.grid_import_w == 500
    assert snap.grid_export_w == 0
    assert snap.battery_charge_w == 800
    assert snap.battery_discharge_w == 0
    assert snap.battery_soc_pct == 55
    assert snap.fresh is True
    assert snap.source == "heartbeat"


def test_map_heartbeat_to_sungrow_stale():
    now = datetime(2026, 8, 21, 10, 5, 0, tzinfo=UTC)
    snap = map_heartbeat_to_sungrow(_overview(), max_age_seconds=60, now=now)
    assert snap.fresh is False


def test_map_heartbeat_missing_pv_is_null_not_zero():
    data = _overview(
        liveHeroView={"consumption": {"value": 1000}},
        summaryCards={"battery": {"stateOfCharge": 55}},
    )
    snap = map_heartbeat_to_sungrow(data)
    assert snap.pv_power_w is None
