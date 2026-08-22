"""Tests for shared PV extraction."""

from energy_core.heartbeat.live_overview import extract_pv_power_w, parse_live_overview


def test_extract_pv_power_w_prefers_summary_cards():
    data = {
        "liveHeroView": {"production": {"value": 1000}},
        "summaryCards": {"photovoltaic": {"production": {"value": 4500}}},
    }
    assert extract_pv_power_w(data) == 4500


def test_extract_pv_power_w_falls_back_to_hero():
    data = {"liveHeroView": {"production": {"value": 3200}}}
    assert extract_pv_power_w(data) == 3200


def test_parse_live_overview_uses_shared_pv_extractor():
    data = {
        "timestamp": "2026-08-21T10:00:00Z",
        "summaryCards": {"photovoltaic": {"production": {"value": 4500}}},
    }
    parsed = parse_live_overview(data)
    assert parsed["pv_power_w"] == 4500
