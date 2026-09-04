"""Dashboard aggregation API tests."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from energy_core.config import Settings
from energy_core.db.models import Base
from helpers import create_charger, seed_readings, seed_recent_readings
from energy_core.db.energy_balance_repo import EnergyBalanceRepository
from energy_core.db.ev_charger_repo import EvChargerRepository


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
async def test_dashboard_uses_redis_cache_on_second_request(client):
    from unittest.mock import AsyncMock, patch

    from energy_core.cache.service import reset_cache_service

    ac, session_factory, settings = client
    await seed_recent_readings(
        session_factory,
        settings,
        "akarp",
        [(3000, 1700, 0, 900, 82)],
    )
    reset_cache_service()
    cached_payload = {
        "site": {"slug": "akarp", "name": "Akarp", "timezone": "Europe/Stockholm"},
        "freshness": {"updated_at": "2026-09-03T12:00:00Z", "data_age_seconds": 0, "stale": False},
        "live": {
            "solar_production_w": 3000,
            "consumption_w": 1700,
            "grid_import_w": 0,
            "grid_export_w": 900,
            "battery_soc_pct": 82,
            "battery_power_w": 0,
            "battery_direction": "idle",
            "ev_power_w": None,
        },
        "today": {
            "produced_kwh": 1.0,
            "consumed_kwh": 1.0,
            "imported_kwh": 0.0,
            "exported_kwh": 0.0,
            "energy_cost_sek": None,
            "savings_sek": None,
        },
        "ev": {"available": False},
        "vehicle": {"available": False},
        "solar": {"unavailable_reason": "test"},
        "price": {"unavailable_reason": "test"},
        "optimization": {"strategy_sv": "test", "reasoning_steps": []},
        "alerts": [],
        "spa_integration_enabled": False,
        "vehicle_integration_enabled": False,
    }
    cache = AsyncMock()
    cache.get = AsyncMock(side_effect=[None, cached_payload])
    cache.get_or_set = AsyncMock(return_value=cached_payload)

    with patch("app.api.dashboard.get_cache_service", return_value=cache):
        first = await ac.get("/api/sites/akarp/dashboard")
        second = await ac.get("/api/sites/akarp/dashboard")

    assert first.status_code == 200
    assert second.status_code == 200
    assert cache.get.await_count == 2
    cache.get_or_set.assert_awaited_once()


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


@pytest.mark.asyncio
async def test_dashboard_includes_yesterday_fields_when_daily_rollup_exists(client):
    from datetime import date, timedelta

    ac, session_factory, settings = client
    await seed_recent_readings(
        session_factory,
        settings,
        "akarp",
        [(3000, 1700, 0, 900, 82), (3100, 1750, 0, 950, 83)],
    )
    async with session_factory() as session:
        from energy_core.db.models import EnergyDailyModel, SiteModel
        from sqlalchemy import select

        site = await session.scalar(select(SiteModel).where(SiteModel.slug == "akarp"))
        assert site is not None
        yesterday = date.today() - timedelta(days=1)
        session.add(
            EnergyDailyModel(
                site_id=site.id,
                day=yesterday,
                solar_kwh=20.0,
                consumption_kwh=18.0,
                import_kwh=5.0,
                export_kwh=2.0,
                import_cost_sek=30.0,
                export_revenue_sek=4.0,
            )
        )
        await session.commit()

    response = await ac.get("/api/sites/akarp/dashboard")
    assert response.status_code == 200
    today = response.json()["today"]
    assert today["produced_kwh_yesterday"] == 20.0


@pytest.mark.asyncio
async def test_dashboard_today_uses_energy_daily_when_aggregates_enabled(tmp_path):
    from datetime import date

    from app.deps import set_session_factory
    from app.main import create_app
    from energy_core.db.models import EnergyDailyModel, FinancialDailyModel, SiteModel
    from energy_core.db.session import create_engine, create_session_factory
    from energy_core.seed import seed_sites
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import select

    db_file = tmp_path / "dashboard-aggregates.db"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        emic_admin_token="",
        financial_aggregates_enabled=True,
    )
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        await seed_sites(session)
        site = await session.scalar(select(SiteModel).where(SiteModel.slug == "akarp"))
        assert site is not None
        today = date.today()
        yesterday = today - timedelta(days=1)
        session.add(
            EnergyDailyModel(
                site_id=site.id,
                day=today,
                solar_kwh=12.5,
                consumption_kwh=9.0,
                import_kwh=1.0,
                export_kwh=4.5,
            )
        )
        session.add(
            EnergyDailyModel(
                site_id=site.id,
                day=yesterday,
                solar_kwh=8.0,
                consumption_kwh=7.0,
                import_kwh=5.0,
                export_kwh=1.0,
                import_cost_sek=30.0,
                export_revenue_sek=4.0,
            )
        )
        session.add(
            FinancialDailyModel(
                site_id=site.id,
                day=today,
                solar_savings_sek=3.0,
                battery_savings_sek=1.5,
                grid_import_cost_sek=10.0,
                energy_sale_sek=2.0,
            )
        )
        await session.commit()

    app = create_app(settings)
    set_session_factory(session_factory, settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/sites/akarp/dashboard")
        assert response.status_code == 200
        body = response.json()["today"]
        assert body["produced_kwh"] == 12.5
        assert body["savings_sek"] == 4.5
        assert body["imported_kwh_yesterday"] == 5.0
        assert body["energy_cost_sek_yesterday"] == 26.0

    await engine.dispose()


@pytest.mark.asyncio
async def test_dashboard_peak_alert_when_fuse_near_capacity(client):
    ac, session_factory, settings = client
    await seed_recent_readings(
        session_factory,
        settings,
        "akarp",
        [(500, 48000, 47000, 0, 80)],
    )
    async with session_factory() as session:
        from energy_core.db.models import SiteModel
        from sqlalchemy import select

        site = await session.scalar(select(SiteModel).where(SiteModel.slug == "akarp"))
        assert site is not None
        site.main_fuse_a = 25.0
        await session.commit()

    response = await ac.get("/api/sites/akarp/dashboard")
    assert response.status_code == 200
    alerts = response.json()["alerts"]
    assert any("Huvudsäkring" in alert["message_sv"] for alert in alerts)
