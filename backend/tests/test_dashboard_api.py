"""Dashboard aggregation API tests."""

import json
from datetime import UTC, datetime

import pytest
from energy_core.db.energy_balance_repo import EnergyBalanceRepository
from energy_core.db.ev_charger_repo import EvChargerRepository
from helpers import create_charger, seed_readings, seed_recent_readings


@pytest.mark.asyncio
async def test_dashboard_returns_site_overview(client):
    ac, session_factory, settings = client
    await seed_recent_readings(
        session_factory,
        settings,
        "akarp",
        [
            (2000, 1500, 0, 500, 80),
            (2500, 1600, 0, 700, 81),
            (3000, 1700, 0, 900, 82),
        ],
    )
    response = await ac.get("/api/sites/akarp/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["site"]["slug"] == "akarp"
    assert body["freshness"]["updated_at"] is not None
    assert body["live"]["solar_production_w"] == 3000
    assert body["today"]["produced_kwh"] is not None


@pytest.mark.asyncio
async def test_dashboard_starts_with_an_empty_section_cache(client):
    """The cache is module-level; a leftover entry would answer for another test's database."""
    from app.api.dashboard import _CACHE

    ac, _, _ = client
    assert _CACHE == {}
    response = await ac.get("/api/sites/akarp/dashboard")
    assert response.status_code == 200
    assert _CACHE != {}


@pytest.mark.asyncio
async def test_dashboard_unknown_site_returns_404(client):
    ac, _, _ = client
    response = await ac.get("/api/sites/unknown/dashboard")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_dashboard_marks_stale_data(client):
    ac, session_factory, settings = client
    await seed_readings(
        session_factory,
        settings,
        "akarp",
        [(6, 0, 1000, 800, 0, 0, 70)],
        day=21,
    )
    response = await ac.get("/api/sites/akarp/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["freshness"]["stale"] is True
    assert any("Mätdata" in alert["message_sv"] for alert in body["alerts"])


@pytest.mark.asyncio
async def test_dashboard_solar_unavailable_without_config(client):
    ac, _, _ = client
    response = await ac.get("/api/sites/akarp/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["solar"]["unavailable_reason"] is not None


@pytest.mark.asyncio
async def test_dashboard_price_unavailable_without_heartbeat(client):
    ac, _, _ = client
    response = await ac.get("/api/sites/akarp/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["price"]["unavailable_reason"] is not None


@pytest.mark.asyncio
async def test_dashboard_ev_section_without_charger(client):
    ac, _, _ = client
    response = await ac.get("/api/sites/akarp/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["ev"]["available"] is False


@pytest.mark.asyncio
async def test_dashboard_ev_section_with_energy_balance(client):
    ac, session_factory, settings = client
    charger = await create_charger(ac, "akarp", name="Dashboard EV", bridge_enabled=True)

    async with session_factory() as session:
        site = await EvChargerRepository(session).get_site_by_slug("akarp")
        assert site is not None
        repo = EnergyBalanceRepository(session, is_sqlite=settings.is_sqlite)
        await repo.insert_snapshot(
            site_id=site.id,
            charger_id=charger["id"],
            recorded_at=datetime.now(UTC),
            status="OK",
            flags=[],
            payload=json.dumps(
                {
                    "sungrow_grid_import_w": 500.0,
                    "heartbeat_home_consumption_w": 2000.0,
                    "heartbeat_observed_ev_power_w": 7000.0,
                }
            ),
        )
        await session.commit()

    response = await ac.get("/api/sites/akarp/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["ev"]["available"] is True
    assert body["ev"]["charging"] is True
    assert body["optimization"]["strategy_sv"] is not None
    assert isinstance(body["optimization"]["reasoning_steps"], list)
    assert len(body["optimization"]["reasoning_steps"]) >= 1

    await ac.delete(f"/api/sites/akarp/ev-chargers/{charger['id']}")


@pytest.mark.asyncio
async def test_dashboard_optimization_without_bridge(client):
    ac, _, _ = client
    response = await ac.get("/api/sites/akarp/dashboard")
    assert response.status_code == 200
    body = response.json()
    optimization = body["optimization"]
    assert optimization["strategy_sv"] == "Ingen SmartLaddning aktiv"
    assert optimization["reasoning_steps"]
    assert "bridge" in optimization["explanation_sv"].lower()
