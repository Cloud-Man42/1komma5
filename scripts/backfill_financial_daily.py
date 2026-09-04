"""Backfill financial_daily aggregates for a site."""

from __future__ import annotations

import argparse
import asyncio

from energy_core.config import get_settings
from energy_core.db.repositories import SiteRepository
from energy_core.db.session import create_engine, create_session_factory
from energy_core.financial.service import FinancialAggregationService


async def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill financial_daily aggregates")
    parser.add_argument("--site", default="akarp")
    parser.add_argument("--days", type=int, default=365)
    args = parser.parse_args()

    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    service = FinancialAggregationService(settings)

    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug(args.site)
        if site is None:
            raise SystemExit(f"Site not found: {args.site}")
        await service.rollup_site(session, site, days_back=args.days)
        await session.commit()
        print(f"Backfilled financial_daily for {args.site} ({args.days} days window)")


if __name__ == "__main__":
    asyncio.run(main())
