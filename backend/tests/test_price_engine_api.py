"""API tests for price engine routes."""

from datetime import UTC, datetime, timedelta

import pytest
from energy_core.db.models import EnergyReadingModel, EvChargerModel, PricePeriodModel
from energy_core.db.repositories import SiteRepository
from energy_core.price_engine.periods import current_period_start
from energy_core.price_engine.types import PriceArea


@pytest.mark.asyncio
async def test_price_engine_current_404(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/unknown/price-engine/current")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_price_engine_current_empty(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/price-engine/current")
    assert res.status_code == 200
    data = res.json()
    assert data["slug"] == "akarp"
    assert data["period"] is None


@pytest.mark.asyncio
async def test_price_engine_current_with_period(client):
    ac, session_factory, _ = client
    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        start = current_period_start(timezone=site.timezone)
        session.add(
            PricePeriodModel(
                site_id=site.id,
                period_start=start,
                period_end=start + timedelta(minutes=15),
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
        await session.commit()

    res = await ac.get("/api/sites/akarp/price-engine/current")
    assert res.status_code == 200
    period = res.json()["period"]
    assert period is not None
    assert period["market_price_sek_kwh"] == pytest.approx(0.32)
    assert period["import_price_sek_kwh"] == pytest.approx(1.21)
    assert period["export_price_sek_kwh"] == pytest.approx(0.39)


@pytest.mark.asyncio
async def test_energy_strategy_current(client):
    ac, session_factory, _ = client
    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        start = current_period_start(timezone=site.timezone)
        session.add(
            PricePeriodModel(
                site_id=site.id,
                period_start=start,
                period_end=start + timedelta(minutes=15),
                price_area=PriceArea.SE4.value,
                currency="SEK",
                market_price_sek_kwh=0.32,
                import_price_sek_kwh=1.05,
                export_price_sek_kwh=0.39,
                source="heartbeat",
                quality="REAL",
                is_estimated=False,
            )
        )
        session.add(
            PricePeriodModel(
                site_id=site.id,
                period_start=start + timedelta(hours=6),
                period_end=start + timedelta(hours=6, minutes=15),
                price_area=PriceArea.SE4.value,
                currency="SEK",
                market_price_sek_kwh=0.80,
                import_price_sek_kwh=3.16,
                export_price_sek_kwh=0.39,
                source="heartbeat",
                quality="REAL",
                is_estimated=False,
            )
        )
        await session.commit()

    res = await ac.get("/api/sites/akarp/energy-strategy/current")
    assert res.status_code == 200
    data = res.json()
    assert data["optimization_mode"] == "MONITOR_ONLY"
    assert data["import_price_sek_kwh"] == pytest.approx(1.05)
    assert data["strategy_state"] in {"PEAK_AHEAD", "NORMAL_SELF_USE", "SAVE_BATTERY", "EXPORT"}
    assert data.get("recommended_action") is not None


@pytest.mark.asyncio
async def test_energy_strategy_peak_protection(client):
    ac, session_factory, _ = client
    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        site.main_fuse_a = 25.0
        start = current_period_start(timezone=site.timezone)
        session.add(
            PricePeriodModel(
                site_id=site.id,
                period_start=start,
                period_end=start + timedelta(minutes=15),
                price_area=PriceArea.SE4.value,
                currency="SEK",
                market_price_sek_kwh=0.32,
                import_price_sek_kwh=1.05,
                export_price_sek_kwh=0.39,
                source="heartbeat",
                quality="REAL",
                is_estimated=False,
            )
        )
        session.add(
            EnergyReadingModel(
                site_id=site.id,
                recorded_at=datetime.now(UTC),
                solar_production_w=0.0,
                consumption_w=18000.0,
                grid_import_w=17000.0,
                grid_export_w=0.0,
                battery_soc_pct=70.0,
                battery_power_w=0.0,
            )
        )
        await session.commit()

    res = await ac.get("/api/sites/akarp/energy-strategy/current")
    assert res.status_code == 200
    data = res.json()
    assert data["strategy_state"] == "PEAK_PROTECTION"
    assert data["fuse_utilization_pct"] is not None
    assert data["grid_surcharge_sek_kwh"] == pytest.approx(0.73)


@pytest.mark.asyncio
async def test_energy_strategy_ev_recommendations(client):
    ac, session_factory, _ = client
    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        start = current_period_start(timezone=site.timezone)
        session.add(
            PricePeriodModel(
                site_id=site.id,
                period_start=start,
                period_end=start + timedelta(minutes=15),
                price_area=PriceArea.SE4.value,
                currency="SEK",
                market_price_sek_kwh=0.32,
                import_price_sek_kwh=2.0,
                export_price_sek_kwh=0.39,
                source="heartbeat",
                quality="REAL",
                is_estimated=False,
            )
        )
        for i in range(1, 9):
            pstart = start + timedelta(minutes=15 * i)
            session.add(
                PricePeriodModel(
                    site_id=site.id,
                    period_start=pstart,
                    period_end=pstart + timedelta(minutes=15),
                    price_area=PriceArea.SE4.value,
                    currency="SEK",
                    market_price_sek_kwh=0.15,
                    import_price_sek_kwh=0.55,
                    export_price_sek_kwh=0.39,
                    source="heartbeat",
                    quality="REAL",
                    is_estimated=False,
                )
            )
        session.add(
            EvChargerModel(
                site_id=site.id,
                name="Halo",
                manufacturer="ChargeAmps",
                model="Halo",
                bridge_enabled=True,
                charging_mode="SMART_CHARGE",
                last_vehicle_connected=True,
            )
        )
        session.add(
            EnergyReadingModel(
                site_id=site.id,
                recorded_at=datetime.now(UTC),
                solar_production_w=3000.0,
                consumption_w=4000.0,
                grid_import_w=1000.0,
                grid_export_w=0.0,
                battery_soc_pct=70.0,
                battery_power_w=0.0,
            )
        )
        await session.commit()

    res = await ac.get("/api/sites/akarp/energy-strategy/current")
    assert res.status_code == 200
    data = res.json()
    assert data["strategy_state"] == "CHARGE_VEHICLE"
    assert len(data["ev_recommendations"]) >= 1
    assert data["ev_recommendations"][0]["charger_name"] == "Halo"


@pytest.mark.asyncio
async def test_price_engine_range_validation(client):
    ac, _, _ = client
    now = datetime.now(UTC)
    res = await ac.get(
        "/api/sites/akarp/price-engine/range",
        params={"from": now.isoformat(), "to": (now - timedelta(hours=1)).isoformat()},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_price_engine_current_uses_cache_on_second_request(client):
    from unittest.mock import AsyncMock, patch

    from energy_core.cache.service import reset_cache_service

    ac, _, _ = client
    reset_cache_service()
    cached_payload = {
        "slug": "akarp",
        "timezone": "Europe/Stockholm",
        "period": None,
    }
    cache = AsyncMock()
    cache.get = AsyncMock(side_effect=[None, cached_payload])
    cache.get_or_set = AsyncMock(return_value=cached_payload)

    with patch("app.api.price_engine.get_cache_service", return_value=cache):
        first = await ac.get("/api/sites/akarp/price-engine/current")
        second = await ac.get("/api/sites/akarp/price-engine/current")

    assert first.status_code == 200
    assert second.status_code == 200
    assert cache.get.await_count == 2
    cache.get_or_set.assert_awaited_once()


@pytest.mark.asyncio
async def test_price_engine_status(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/price-engine/status")
    assert res.status_code == 200
    data = res.json()
    assert data["optimization_mode"] == "MONITOR_ONLY"
    assert data["missing_periods_count"] == 0
