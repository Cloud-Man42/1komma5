"""Spa energy breakdown API tests."""

from datetime import UTC, datetime, timedelta

import pytest
from energy_core.db.consumer_repo import ConsumerIntervalRepository, ConsumerRepository
from energy_core.db.repositories import SiteRepository


async def _seed_spa_intervals(session_factory):
    async with session_factory() as session:
        site_repo = SiteRepository(session)
        site = await site_repo.get_by_slug("akarp")
        assert site is not None
        repo = ConsumerRepository(session)
        consumer, _ = await repo.get_or_create_spa(site)
        interval_repo = ConsumerIntervalRepository(session)
        now = datetime.now(UTC)
        await interval_repo.insert(
            consumer_id=consumer.id,
            start_time=now - timedelta(hours=3),
            end_time=now - timedelta(hours=2),
            energy_kwh=1.0,
            average_power_w=3000.0,
            solar_direct_kwh=0.4,
            solar_battery_kwh=0.2,
            grid_battery_kwh=0.1,
            grid_direct_kwh=0.3,
            actual_cost_sek=0.6,
            reference_cost_sek=2.0,
            savings_sek=1.4,
            electricity_price_sek_kwh=2.0,
        )
        await interval_repo.insert(
            consumer_id=consumer.id,
            start_time=now - timedelta(days=1, hours=2),
            end_time=now - timedelta(days=1, hours=1),
            energy_kwh=2.0,
            average_power_w=2500.0,
            solar_direct_kwh=1.0,
            solar_battery_kwh=0.0,
            grid_battery_kwh=0.5,
            grid_direct_kwh=0.5,
            actual_cost_sek=1.0,
            reference_cost_sek=4.0,
            savings_sek=3.0,
            electricity_price_sek_kwh=2.0,
        )
        await session.commit()
        return consumer.id


@pytest.mark.asyncio
async def test_spa_energy_breakdown_and_cost_split(client):
    ac, session_factory, _ = client
    await ac.get("/api/sites/akarp/spa/status")
    await _seed_spa_intervals(session_factory)

    month = await ac.get("/api/sites/akarp/spa/energy/month")
    assert month.status_code == 200
    body = month.json()
    assert body["has_data"] is True
    assert body["energy_kwh"] == pytest.approx(3.0)
    assert body["solar_kwh"] == pytest.approx(1.6)
    assert body["battery_kwh"] == pytest.approx(0.6)
    assert body["grid_kwh"] == pytest.approx(0.8)
    assert body["grid_cost_sek"] == pytest.approx(1.6)

    breakdown = await ac.get("/api/sites/akarp/spa/energy/breakdown?period=month")
    assert breakdown.status_code == 200
    payload = breakdown.json()
    assert payload["granularity"] == "day"
    assert len(payload["rows"]) >= 1
    assert payload["total"]["energy_kwh"] == pytest.approx(3.0)

    history = await ac.get("/api/sites/akarp/spa/history?period=month")
    assert history.status_code == 200
    points = history.json()["points"]
    assert len(points) >= 1
    assert points[0]["solar_kwh"] is not None
    assert points[0]["grid_cost_sek"] is not None


@pytest.mark.asyncio
async def test_spa_history_24h_period(client):
    ac, session_factory, _ = client
    await ac.get("/api/sites/akarp/spa/status")
    await _seed_spa_intervals(session_factory)

    for period in ("24h", "day"):
        history = await ac.get(f"/api/sites/akarp/spa/history?period={period}")
        assert history.status_code == 200
        body = history.json()
        assert body["period"] == "24h"
        assert len(body["points"]) >= 1
        assert body["points"][0]["power_w"] is not None


@pytest.mark.asyncio
async def test_spa_history_invalid_period(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/spa/history?period=invalid")
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_spa_energy_breakdown_invalid_site(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/missing/spa/energy/breakdown?period=month")
    assert res.status_code == 404
