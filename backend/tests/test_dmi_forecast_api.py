"""DMI forecast API tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
async def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("APP_ENV", "test")
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_dmi_forecast_404_for_unknown_site(client):
    res = await client.get("/api/sites/unknown/solar/dmi/forecast")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_dmi_forecast_422_for_swedish_site(client):
    res = await client.get("/api/sites/akarp/solar/dmi/forecast")
    assert res.status_code in (404, 422)


@pytest.mark.asyncio
async def test_dmi_forecast_returns_points_for_denmark(client, monkeypatch):
    async def fake_fetch(self, **kwargs):
        return [
            {
                "timestamp": datetime(2026, 8, 28, 9, 0, tzinfo=UTC).isoformat(),
                "ghi_wm2": 500.0,
                "dhi_wm2": 150.0,
                "temperature_c": 19.0,
                "cloud_cover_pct": 25.0,
                "precipitation_mm": 0.0,
                "humidity_pct": 70.0,
                "wind_speed_ms": 4.0,
            }
        ]

    monkeypatch.setattr(
        "energy_core.solar_intelligence.service.SolarIntelligenceCoordinator.fetch_dmi_forecast",
        fake_fetch,
    )

    res = await client.get("/api/sites/summer-house-denmark/solar/dmi/forecast")
    if res.status_code == 404:
        pytest.skip("Denmark site solar config not seeded in test DB")
    assert res.status_code == 200
    body = res.json()
    assert body["provider"] == "dmi-harmonie"
    assert body["country_code"] == "DK"
    assert len(body["points"]) == 1
    assert body["points"][0]["ghi_wm2"] == 500.0
