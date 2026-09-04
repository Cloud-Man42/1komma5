from datetime import UTC, datetime, timedelta

import pytest
from energy_core.db.models import PricePeriodModel
from energy_core.db.repositories import SiteRepository
from energy_core.price_engine.periods import current_period_start
from energy_core.price_engine.types import PriceArea


@pytest.mark.asyncio
async def test_market_prices_empty_when_no_cached_data(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/market-prices")
    assert res.status_code == 200
    body = res.json()
    assert body["points"] == []
    assert body["current_price_eur_kwh"] is None


@pytest.mark.asyncio
async def test_market_prices_404(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/unknown/market-prices")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_market_prices_success_from_price_engine(client):
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
                market_price_sek_kwh=1.10,
                import_price_sek_kwh=1.40,
                export_price_sek_kwh=0.39,
                source="heartbeat",
                quality="REAL",
                is_estimated=False,
            )
        )
        session.add(
            PricePeriodModel(
                site_id=site.id,
                period_start=start + timedelta(hours=1),
                period_end=start + timedelta(hours=1, minutes=15),
                price_area=PriceArea.SE4.value,
                currency="SEK",
                market_price_sek_kwh=1.30,
                import_price_sek_kwh=1.60,
                export_price_sek_kwh=0.39,
                source="heartbeat",
                quality="REAL",
                is_estimated=False,
            )
        )
        await session.commit()

    now = datetime.now(UTC)
    res = await ac.get(
        "/api/sites/akarp/market-prices",
        params={
            "from": (now - timedelta(hours=2)).isoformat(),
            "to": (now + timedelta(hours=2)).isoformat(),
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["current_price_eur_kwh"] is not None
    assert len(body["points"]) >= 1
    first = body["points"][0]
    assert first["spot_sek_kwh"] == pytest.approx(1.10, abs=0.01)
    assert first["import_sek_kwh"] == pytest.approx(1.40, abs=0.01)
    assert body["current_import_sek_kwh"] is not None
    assert body["current_import_sek_kwh"] >= body["current_spot_sek_kwh"]
