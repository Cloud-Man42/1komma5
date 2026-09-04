from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db_session, get_site_repository
from app.schemas import MarketPricePointResponse, MarketPricesResponse
from energy_core.db.repositories import SiteRepository
from energy_core.market_prices.currency import sek_to_eur
from energy_core.price_engine.engine import EmicPriceEngine
from energy_core.price_engine.periods import align_period_start
from energy_core.price_engine.types import PricePeriod

router = APIRouter(tags=["prices"])


async def _engine(session: AsyncSession) -> EmicPriceEngine:
    from energy_core.config import get_settings

    settings = get_settings()
    return EmicPriceEngine(session, is_sqlite=settings.is_sqlite)


def _period_to_point(period: PricePeriod) -> MarketPricePointResponse | None:
    if period.market_price_sek_kwh is None:
        return None
    spot_eur = sek_to_eur(period.market_price_sek_kwh)
    all_in_eur = (
        sek_to_eur(period.import_price_sek_kwh) if period.import_price_sek_kwh is not None else None
    )
    return MarketPricePointResponse(
        timestamp=period.period_start,
        spot_eur_kwh=spot_eur,
        all_in_eur_kwh=all_in_eur,
        spot_sek_kwh=period.market_price_sek_kwh,
        import_sek_kwh=period.import_price_sek_kwh,
        export_sek_kwh=period.export_price_sek_kwh,
    )


def _rollup_hourly(periods: tuple[PricePeriod, ...]) -> list[MarketPricePointResponse]:
    """Average 15-minute rows into hourly points for legacy 1h resolution."""
    buckets: dict[datetime, list[PricePeriod]] = {}
    for period in periods:
        hour_start = align_period_start(period.period_start, interval_minutes=60)
        buckets.setdefault(hour_start, []).append(period)

    points: list[MarketPricePointResponse] = []
    for hour_start in sorted(buckets):
        bucket = buckets[hour_start]
        spots = [p.market_price_sek_kwh for p in bucket if p.market_price_sek_kwh is not None]
        imports = [p.import_price_sek_kwh for p in bucket if p.import_price_sek_kwh is not None]
        exports = [p.export_price_sek_kwh for p in bucket if p.export_price_sek_kwh is not None]
        if not spots:
            continue
        spot_sek = sum(spots) / len(spots)
        import_sek = sum(imports) / len(imports) if imports else None
        export_sek = sum(exports) / len(exports) if exports else None
        points.append(
            MarketPricePointResponse(
                timestamp=hour_start,
                spot_eur_kwh=sek_to_eur(spot_sek),
                all_in_eur_kwh=sek_to_eur(import_sek) if import_sek is not None else None,
                spot_sek_kwh=spot_sek,
                import_sek_kwh=import_sek,
                export_sek_kwh=export_sek,
            )
        )
    return points


def _as_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def _closest_point(
    points: list[MarketPricePointResponse], now: datetime
) -> MarketPricePointResponse | None:
    if not points:
        return None
    return min(points, key=lambda point: abs((_as_utc(point.timestamp) - now).total_seconds()))


def _summarize_eur(
    points: list[MarketPricePointResponse], *, now: datetime
) -> tuple[float | None, float | None, float | None, float | None]:
    if not points:
        return None, None, None, None
    current_point = _closest_point(points, now)
    current = current_point.spot_eur_kwh if current_point else points[0].spot_eur_kwh
    all_ins = [p.all_in_eur_kwh for p in points if p.all_in_eur_kwh is not None]
    if not all_ins:
        return current, None, None, None
    return current, sum(all_ins) / len(all_ins), max(all_ins), min(all_ins)


def _summarize_sek(
    points: list[MarketPricePointResponse], *, now: datetime
) -> tuple[float | None, float | None, float | None, float | None]:
    if not points:
        return None, None, None, None
    current_point = _closest_point(points, now)
    if current_point is None:
        return None, None, None, None
    current_spot = current_point.spot_sek_kwh
    current_import = current_point.import_sek_kwh or current_spot
    imports = [p.import_sek_kwh for p in points if p.import_sek_kwh is not None]
    if not imports:
        return current_spot, current_import, None, None
    return current_spot, current_import, max(imports), min(imports)


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

    now = datetime.now(UTC)
    if from_time is None:
        from_time = now - timedelta(hours=1)
    if to_time is None:
        to_time = now + timedelta(hours=23)

    if from_time.tzinfo is None:
        from_time = from_time.replace(tzinfo=UTC)
    if to_time.tzinfo is None:
        to_time = to_time.replace(tzinfo=UTC)

    engine = await _engine(session)
    periods = await engine.get_range(site.id, start=from_time, end=to_time)

    if resolution == "1h":
        points = _rollup_hourly(periods)
    else:
        points = [p for period in periods if (p := _period_to_point(period)) is not None]

    current_price, avg_all_in, highest_all_in, lowest_all_in = _summarize_eur(points, now=now)
    current_spot, current_import, highest_import, lowest_import = _summarize_sek(points, now=now)
    import_values = [p.import_sek_kwh for p in points if p.import_sek_kwh is not None]
    average_import = sum(import_values) / len(import_values) if import_values else None

    return MarketPricesResponse(
        slug=slug,
        timezone=site.timezone,
        resolution=resolution,
        current_price_eur_kwh=current_price,
        average_all_in_eur_kwh=avg_all_in,
        highest_all_in_eur_kwh=highest_all_in,
        lowest_all_in_eur_kwh=lowest_all_in,
        current_spot_sek_kwh=current_spot,
        current_import_sek_kwh=current_import,
        average_import_sek_kwh=average_import,
        highest_import_sek_kwh=highest_import,
        lowest_import_sek_kwh=lowest_import,
        points=points,
    )
