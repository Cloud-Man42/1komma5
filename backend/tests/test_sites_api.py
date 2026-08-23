from datetime import UTC, datetime

import pytest
from energy_core.db.repositories import EnergyReadingRepository, SiteRepository
from energy_core.domain import NormalizedEnergyReading
from helpers import seed_readings


@pytest.mark.asyncio
async def test_list_sites_empty_readings(client):
    ac, _, _ = client
    res = await ac.get("/api/sites")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    slugs = {s["slug"] for s in data}
    assert slugs == {"akarp", "summer-house-denmark"}


@pytest.mark.asyncio
async def test_site_readings_404(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/unknown/readings")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_site_readings_success(client):
    ac, session_factory, settings = client
    await seed_readings(
        session_factory,
        settings,
        "akarp",
        [(10, 0, 5000, 1200, 0, 3800, 55), (10, 5, 5200, 1300, 0, 3900, 56)],
    )
    res = await ac.get(
        "/api/sites/akarp/readings",
        params={
            "from": "2026-08-18T09:00:00Z",
            "to": "2026-08-18T12:00:00Z",
            "bucket": 5,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body["readings"]) >= 1
    assert body["readings"][0]["solar_production_w"] > 0


@pytest.mark.asyncio
async def test_site_readings_empty_range(client):
    ac, _, _ = client
    res = await ac.get(
        "/api/sites/akarp/readings",
        params={"from": "2020-01-01T00:00:00Z", "to": "2020-01-01T01:00:00Z"},
    )
    assert res.status_code == 200
    assert res.json()["readings"] == []


@pytest.mark.asyncio
async def test_update_site_success(client):
    ac, _, _ = client
    res = await ac.put(
        "/api/sites/akarp",
        json={"name": "Åkarp Updated", "main_fuse_a": 25},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Åkarp Updated"
    assert res.json()["main_fuse_a"] == 25


@pytest.mark.asyncio
async def test_update_site_404(client):
    ac, _, _ = client
    res = await ac.put("/api/sites/missing", json={"name": "X"})
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_site_peaks_returns_daily_power_maxima(client):
    ac, session_factory, settings = client
    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
        for hour, solar, battery in [(10, 7800, 1200), (11, 7000, -3100)]:
            await reading_repo.upsert_reading(
                site.id,
                NormalizedEnergyReading(
                    site_slug="akarp",
                    recorded_at=datetime(2026, 8, 18, hour, tzinfo=UTC),
                    solar_production_w=solar,
                    consumption_w=1000,
                    grid_import_w=0,
                    grid_export_w=0,
                    battery_soc_pct=50,
                    battery_power_w=battery,
                ),
            )
        await session.commit()

    res = await ac.get(
        "/api/sites/akarp/peaks",
        params={
            "period": "day",
            "from": "2026-08-18T00:00:00Z",
            "to": "2026-08-19T00:00:00Z",
        },
    )

    assert res.status_code == 200
    body = res.json()
    assert body["timezone"] == "Europe/Stockholm"
    assert body["peaks"] == [
        {
            "period_start": "2026-08-18",
            "solar_production_w": 7800.0,
            "battery_charge_w": 1200.0,
            "battery_discharge_w": 3100.0,
        }
    ]


@pytest.mark.asyncio
async def test_site_peaks_rejects_invalid_period_and_range(client):
    ac, _, _ = client

    invalid_period = await ac.get("/api/sites/akarp/peaks?period=week")
    invalid_range = await ac.get(
        "/api/sites/akarp/peaks",
        params={"from": "2026-08-19T00:00:00Z", "to": "2026-08-18T00:00:00Z"},
    )

    assert invalid_period.status_code == 422
    assert invalid_range.status_code == 422


@pytest.mark.asyncio
async def test_site_financial_stats_returns_savings_and_export_revenue(client):
    ac, session_factory, settings = client
    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
        for minute in (0, 5):
            await reading_repo.upsert_reading(
                site.id,
                NormalizedEnergyReading(
                    site_slug="akarp",
                    recorded_at=datetime(2026, 8, 18, 10, minute, tzinfo=UTC),
                    solar_production_w=1000,
                    consumption_w=1000,
                    grid_import_w=250,
                    grid_export_w=500,
                    battery_soc_pct=50,
                    battery_power_w=0,
                ),
            )
        await session.commit()

    response = await ac.get(
        "/api/sites/akarp/financial-stats",
        params={"period": "day", "year": 2026},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["fallback_purchase_price_sek_kwh"] == 2.0
    assert body["export_compensation_sek_kwh"] == 0.8
    assert body["stats"][0]["solar_savings_sek"] == 0.17
    assert body["stats"][0]["export_revenue_sek"] == 0.03
    assert body["stats"][0]["imported_kwh"] == 0.021
    assert body["stats"][0]["grid_import_cost_sek"] == 0.04


@pytest.mark.asyncio
async def test_site_financial_price_settings_validate_non_negative_values(client):
    ac, _, _ = client

    invalid = await ac.put(
        "/api/sites/akarp",
        json={"fallback_purchase_price_sek_kwh": -1},
    )

    assert invalid.status_code == 422


@pytest.mark.asyncio
async def test_site_forecast_projects_next_year_from_history(client):
    ac, session_factory, settings = client
    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
        for minute in (0, 5):
            await reading_repo.upsert_reading(
                site.id,
                NormalizedEnergyReading(
                    site_slug="akarp",
                    recorded_at=datetime(2026, 8, 18, 10, minute, tzinfo=UTC),
                    solar_production_w=2000,
                    consumption_w=1500,
                    grid_import_w=200,
                    grid_export_w=500,
                    battery_soc_pct=50,
                    battery_power_w=-300,
                ),
            )
        await session.commit()

    response = await ac.get("/api/sites/akarp/forecast?year=2027")

    assert response.status_code == 200
    body = response.json()
    assert body["year"] == 2027
    assert len(body["months"]) == 12
    assert body["actual"]["solar_self_consumed_kwh"] == 0
    assert body["forecast"]["solar_self_consumed_kwh"] > 0
    assert body["forecast"]["imported_kwh"] == pytest.approx(22960.1, abs=0.01)
    assert body["import_baseline_year"] == 2025
    assert body["import_baseline_source"] == "Tibber Historik 2025 (bild)"
    assert body["import_baseline_estimated"] is True
    assert body["import_baseline_kwh"] == 22960.1
    assert body["uncertainty_pct"] == 45


@pytest.mark.asyncio
async def test_site_forecast_validates_year_and_site(client):
    ac, _, _ = client

    invalid_year = await ac.get("/api/sites/akarp/forecast?year=1999")
    missing_site = await ac.get("/api/sites/missing/forecast?year=2027")

    assert invalid_year.status_code == 422
    assert missing_site.status_code == 404


@pytest.mark.asyncio
async def test_historical_monthly_energy_calibrates_import_forecast(client):
    ac, _, _ = client
    monthly_kwh = [2600, 2700, 2300, 1800, 1700, 1400, 800, 1600, 1800, 1900, 2200, 2160.1]
    payload = {
        "source": "Tibber Historik 2025",
        "estimated": True,
        "months": [
            {"month": month, "imported_kwh": value}
            for month, value in enumerate(monthly_kwh, start=1)
        ],
    }

    saved = await ac.put("/api/sites/akarp/historical-energy/2025", json=payload)
    fetched = await ac.get("/api/sites/akarp/historical-energy/2025")
    forecast = await ac.get("/api/sites/akarp/forecast?year=2027")

    assert saved.status_code == 200
    assert saved.json()["total_imported_kwh"] == 22960.1
    assert fetched.status_code == 200
    assert fetched.json()["estimated"] is True
    assert forecast.status_code == 200
    assert forecast.json()["import_baseline_year"] == 2025
    assert forecast.json()["import_baseline_estimated"] is True
    assert forecast.json()["import_baseline_kwh"] == 22960.1
    assert forecast.json()["forecast"]["imported_kwh"] == pytest.approx(22960.1, abs=0.01)


@pytest.mark.asyncio
async def test_historical_monthly_energy_requires_every_month(client):
    ac, _, _ = client
    duplicate_months = {
        "months": [{"month": 1, "imported_kwh": 100} for _ in range(12)],
    }

    response = await ac.put(
        "/api/sites/akarp/historical-energy/2025",
        json=duplicate_months,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_historical_energy_404_missing_year(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/historical-energy/1999")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_create_and_delete_site(client):
    ac, _, _ = client
    create = await ac.post(
        "/api/sites",
        json={
            "slug": "test-site",
            "name": "Test Site",
            "timezone": "Europe/Stockholm",
        },
    )
    assert create.status_code == 201

    delete = await ac.delete("/api/sites/test-site")
    assert delete.status_code == 204
