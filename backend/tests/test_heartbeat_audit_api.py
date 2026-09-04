"""API tests for heartbeat audit routes."""

from datetime import UTC, datetime, timedelta

import pytest
from energy_core.db.models import EnergyReadingModel, PricePeriodModel, VirtualChargerDecisionModel
from energy_core.db.repositories import SiteRepository
from energy_core.price_engine.periods import current_period_start
from energy_core.price_engine.types import PriceArea


@pytest.mark.asyncio
async def test_heartbeat_audit_today_404(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/unknown/heartbeat-audit/today")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_heartbeat_audit_today_503_without_data(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/heartbeat-audit/today")
    assert res.status_code == 503


@pytest.mark.asyncio
async def test_heartbeat_audit_today_with_data(client):
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
        t0 = datetime.now(UTC) - timedelta(minutes=5)
        session.add(
            EnergyReadingModel(
                site_id=site.id,
                recorded_at=t0,
                solar_production_w=2000.0,
                consumption_w=3000.0,
                grid_import_w=1000.0,
                grid_export_w=0.0,
                battery_soc_pct=70.0,
                battery_power_w=0.0,
            )
        )
        session.add(
            EnergyReadingModel(
                site_id=site.id,
                recorded_at=t0 + timedelta(minutes=2),
                solar_production_w=2500.0,
                consumption_w=3500.0,
                grid_import_w=1000.0,
                grid_export_w=0.0,
                battery_soc_pct=69.0,
                battery_power_w=-200.0,
            )
        )
        session.add(
            VirtualChargerDecisionModel(
                site_id=site.id,
                bridge_state="SIMULATION",
                heartbeat_mode="SMART_CHARGE",
                ai_decision="charge_cheap",
                decision_json="{}",
                reason="Heartbeat cheap window",
                recorded_at=t0,
            )
        )
        await session.commit()

    res = await ac.get("/api/sites/akarp/heartbeat-audit/today")
    assert res.status_code == 200
    data = res.json()
    assert data["slug"] == "akarp"
    assert data["rollup"]["actual_energy_cost_sek"] is not None
    assert len(data["periods"]) >= 1
    assert data["periods"][0]["emic_strategy_state"] is not None


@pytest.mark.asyncio
async def test_heartbeat_audit_month(client):
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
        t0 = datetime.now(UTC) - timedelta(minutes=3)
        session.add(
            EnergyReadingModel(
                site_id=site.id,
                recorded_at=t0,
                solar_production_w=2000.0,
                consumption_w=3000.0,
                grid_import_w=1000.0,
                grid_export_w=0.0,
                battery_soc_pct=70.0,
                battery_power_w=0.0,
            )
        )
        session.add(
            EnergyReadingModel(
                site_id=site.id,
                recorded_at=t0 + timedelta(minutes=1),
                solar_production_w=2200.0,
                consumption_w=3200.0,
                grid_import_w=1000.0,
                grid_export_w=0.0,
                battery_soc_pct=69.0,
                battery_power_w=0.0,
            )
        )
        await session.commit()

    res = await ac.get("/api/sites/akarp/heartbeat-audit/month")
    assert res.status_code == 200
    data = res.json()
    assert data["month"]
    assert data["days_with_data"] >= 1
