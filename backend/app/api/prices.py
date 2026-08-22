from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db_session, get_site_repository
from app.schemas import MarketPricePointResponse, MarketPricesResponse
from energy_core.db.repositories import SiteRepository
from energy_core.heartbeat.market_prices import parse_market_prices
from energy_core.heartbeat_client_factory import create_heartbeat_client

router = APIRouter(tags=["prices"])


@router.get("/sites/{slug}/market-prices", response_model=MarketPricesResponse)
async def get_site_market_prices(
    slug: str,
    from_time: datetime | None = Query(default=None, alias="from"),
    to_time: datetime | None = Query(default=None, alias="to"),
    resolution: str = Query(default="1h", pattern="^(1h|15m)$"),
    site_repo: SiteRepository = Depends(get_site_repository),
    session: AsyncSession = Depends(get_db_session),
) -> MarketPricesResponse:
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site '{slug}' not found")

    if not site.external_system_id:
        raise HTTPException(
            status_code=400,
            detail=f"Site '{slug}' has no Heartbeat system ID configured",
        )

    now = datetime.now(UTC)
    if from_time is None:
        from_time = now - timedelta(hours=1)
    if to_time is None:
        to_time = now + timedelta(hours=23)

    client = await create_heartbeat_client(session)
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="Heartbeat is not configured for live price data",
        )

    from_iso = from_time.astimezone(UTC).isoformat().replace("+00:00", "Z")
    to_iso = to_time.astimezone(UTC).isoformat().replace("+00:00", "Z")

    try:
        raw = await client.fetch_market_prices(
            site.external_system_id,
            from_iso=from_iso,
            to_iso=to_iso,
            resolution=resolution,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch market prices: {exc}") from exc

    parsed = parse_market_prices(raw)
    return MarketPricesResponse(
        slug=slug,
        timezone=site.timezone,
        resolution=resolution,
        current_price_eur_kwh=parsed.current_price_eur_kwh,
        average_all_in_eur_kwh=parsed.average_all_in_eur_kwh,
        highest_all_in_eur_kwh=parsed.highest_all_in_eur_kwh,
        lowest_all_in_eur_kwh=parsed.lowest_all_in_eur_kwh,
        points=[
            MarketPricePointResponse(
                timestamp=point.timestamp,
                spot_eur_kwh=point.spot_eur_kwh,
                all_in_eur_kwh=point.all_in_eur_kwh,
            )
            for point in parsed.points
        ],
    )
