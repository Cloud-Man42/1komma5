"""Tests for solar intelligence geometry (DST-safe)."""

from datetime import datetime
from zoneinfo import ZoneInfo

from energy_core.solar_intelligence.geometry import SolarGeometryService


def test_elevation_positive_at_solar_noon_stockholm_summer():
    geo = SolarGeometryService(latitude=55.6, longitude=13.2, timezone="Europe/Stockholm")
    ts = datetime(2026, 6, 21, 12, 0, tzinfo=ZoneInfo("Europe/Stockholm"))
    elev, _ = geo.elevation_azimuth(ts)
    assert elev > 50.0


def test_elevation_negative_at_midnight():
    geo = SolarGeometryService(latitude=55.6, longitude=13.2, timezone="Europe/Stockholm")
    ts = datetime(2026, 6, 21, 0, 0, tzinfo=ZoneInfo("Europe/Stockholm"))
    elev, _ = geo.elevation_azimuth(ts)
    assert elev < 0


def test_dst_transition_day_length_reasonable():
    geo = SolarGeometryService(latitude=55.6, longitude=13.2, timezone="Europe/Stockholm")
    spring = datetime(2026, 3, 29, 12, 0, tzinfo=ZoneInfo("Europe/Stockholm"))
    g = geo.geometry_at(spring)
    assert g.day_length_hours > 10.0
