"""Tests for DMI HARMONIE parsing and providers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from energy_core.solar_intelligence.providers.dmi_harmonie import (
    DmiHarmonieClient,
    DmiHarmonieRadiationProvider,
    DmiHarmonieWeatherProvider,
    parse_dmi_geojson,
)


SAMPLE_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [12.55, 55.71]},
            "properties": {
                "step": "2026-08-28T08:00:00.000Z",
                "temperature-2m": 293.15,
                "relative-humidity-2m": 72.0,
                "low-cloud-cover": 20.0,
                "medium-cloud-cover": 10.0,
                "high-cloud-cover": 5.0,
                "wind-speed-10m": 4.2,
                "total-precipitation": 0.0,
                "global-radiation-flux": 420.0,
                "downward-short-wave-radiation-flux-instant": 430.0,
            },
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [12.55, 55.71]},
            "properties": {
                "step": "2026-08-28T09:00:00.000Z",
                "temperature-2m": 295.15,
                "relative-humidity-2m": 68.0,
                "low-cloud-cover": 30.0,
                "medium-cloud-cover": 15.0,
                "high-cloud-cover": 10.0,
                "wind-speed-10m": 5.1,
                "total-precipitation": 0.4,
                "global-radiation-flux": 510.0,
                "downward-short-wave-radiation-flux-instant": 520.0,
            },
        },
    ],
}


def test_parse_dmi_geojson_converts_units_and_precip_diff():
    rows = parse_dmi_geojson(SAMPLE_GEOJSON)
    assert len(rows) == 2
    assert rows[0]["temperature_c"] == pytest.approx(20.0)
    assert rows[0]["ghi_wm2"] == pytest.approx(430.0)
    assert rows[0]["cloud_cover_pct"] == pytest.approx(11.7, abs=0.2)
    assert rows[0]["precipitation_mm"] is None
    assert rows[1]["precipitation_mm"] == pytest.approx(0.4)


@pytest.mark.asyncio
async def test_dmi_providers_use_shared_client(monkeypatch):
    client = DmiHarmonieClient()
    from_ts = datetime(2026, 8, 28, 8, 0, tzinfo=UTC)
    to_ts = datetime(2026, 8, 28, 10, 0, tzinfo=UTC)

    async def fake_fetch_rows(**kwargs):
        return parse_dmi_geojson(SAMPLE_GEOJSON)

    monkeypatch.setattr(client, "fetch_rows", fake_fetch_rows)

    radiation = DmiHarmonieRadiationProvider(client)
    weather = DmiHarmonieWeatherProvider(client)

    rad = await radiation.fetch_radiation(latitude=55.71, longitude=12.55, from_ts=from_ts, to_ts=to_ts)
    wx = await weather.fetch_weather(latitude=55.71, longitude=12.55, from_ts=from_ts, to_ts=to_ts)

    assert any(sample.parameter == "ghi" for sample in rad)
    assert len(wx) == 2
    assert wx[0].provider == "dmi-harmonie"


def test_parse_dmi_geojson_empty_payload():
    assert parse_dmi_geojson({}) == []
