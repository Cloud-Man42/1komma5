"""API tests for forecast learning routes."""

from datetime import UTC, datetime, timedelta

import pytest
from energy_core.db.models import EnergyForecastSnapshotModel, EnergyReadingModel, PricePeriodModel
from energy_core.db.repositories import SiteRepository
from energy_core.price_engine.periods import current_period_start
from energy_core.price_engine.types import PriceArea


@pytest.mark.asyncio
async def test_forecast_learning_summary_404(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/unknown/forecast-learning/summary")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_forecast_learning_summary_empty(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/forecast-learning/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["slug"] == "akarp"
    assert len(data["metrics"]) == 3
    assert all(m["sample_count"] == 0 for m in data["metrics"])


@pytest.mark.asyncio
async def test_forecast_learning_summary_with_data(client):
    ac, session_factory, _ = client
    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        start = current_period_start(timezone=site.timezone) - timedelta(hours=1)
        session.add(
            EnergyForecastSnapshotModel(
                site_id=site.id,
                period_start=start,
                period_end=start + timedelta(minutes=15),
                forecast_kind="import_price_sek_kwh",
                predicted_value=1.20,
                actual_value=1.25,
                forecast_recorded_at=start - timedelta(hours=2),
                actual_recorded_at=start + timedelta(minutes=15),
            )
        )
        await session.commit()

    res = await ac.get("/api/sites/akarp/forecast-learning/summary?days=7")
    assert res.status_code == 200
    data = res.json()
    price_metric = next(m for m in data["metrics"] if m["kind"] == "import_price_sek_kwh")
    assert price_metric["sample_count"] == 1
    assert price_metric["mae"] == pytest.approx(0.05)


@pytest.mark.asyncio
async def test_forecast_learning_recent_invalid_kind(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/forecast-learning/recent?kind=invalid")
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_forecast_learning_service_reconcile(client):
    ac, session_factory, _ = client
    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        start = current_period_start(timezone=site.timezone) - timedelta(minutes=30)
        end = start + timedelta(minutes=15)
        session.add(
            PricePeriodModel(
                site_id=site.id,
                period_start=start,
                period_end=end,
                price_area=PriceArea.SE4.value,
                currency="SEK",
                market_price_sek_kwh=0.32,
                import_price_sek_kwh=1.21,
                export_price_sek_kwh=0.39,
                source="heartbeat",
                quality="REAL",
                is_estimated=False,
            )
        )
        session.add(
            EnergyForecastSnapshotModel(
                site_id=site.id,
                period_start=start,
                period_end=end,
                forecast_kind="import_price_sek_kwh",
                predicted_value=1.10,
                actual_value=None,
                forecast_recorded_at=start - timedelta(hours=1),
            )
        )
        session.add(
            EnergyReadingModel(
                site_id=site.id,
                recorded_at=start + timedelta(minutes=5),
                solar_production_w=1500.0,
                consumption_w=3200.0,
                grid_import_w=1700.0,
                grid_export_w=0.0,
                battery_soc_pct=65.0,
                battery_power_w=0.0,
            )
        )
        await session.commit()

        from energy_core.forecast_learning.service import ForecastLearningService

        service = ForecastLearningService(session, is_sqlite=True)
        reconciled = await service.reconcile_actuals(site.id, timezone=site.timezone)
        assert reconciled >= 1
        await session.commit()

    res = await ac.get("/api/sites/akarp/forecast-learning/recent?kind=import_price_sek_kwh")
    assert res.status_code == 200
    data = res.json()
    assert len(data["snapshots"]) >= 1
    assert data["snapshots"][0]["actual_value"] == pytest.approx(1.21)
