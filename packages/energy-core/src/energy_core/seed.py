"""Database seed utilities."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import SiteModel
from energy_core.db.repositories import (
    HistoricalEnergyRepository,
    HistoricalMonthlyEnergy,
    SiteRepository,
)
from energy_core.providers.mock import MOCK_SITES

DEMO_2025_IMPORT_KWH = [
    2000.0,
    2100.0,
    1900.0,
    1800.0,
    1700.0,
    1500.0,
    1200.0,
    1600.0,
    1800.0,
    1900.0,
    2100.0,
    2000.0,
]
DEMO_2025_IMPORT_COST_SEK = 18000.0


async def seed_sites(session: AsyncSession) -> None:
    """Seed default sites and a demo historical import baseline."""
    count = await session.scalar(select(func.count()).select_from(SiteModel))
    repo = SiteRepository(session)
    if not count:
        for site in MOCK_SITES:
            await repo.upsert_site(
                slug=site.slug,
                name=site.name,
                timezone=site.timezone,
                external_system_id=site.external_system_id,
            )
        await session.flush()

    akarp = await repo.get_by_slug("akarp")
    if akarp is not None:
        historical_repo = HistoricalEnergyRepository(
            session,
            is_sqlite=session.bind is not None and session.bind.dialect.name == "sqlite",
        )
        if not await historical_repo.list_for_site(akarp.id):
            total_kwh = sum(DEMO_2025_IMPORT_KWH)
            allocated_cost = 0.0
            months: list[HistoricalMonthlyEnergy] = []
            for month, imported_kwh in enumerate(DEMO_2025_IMPORT_KWH, start=1):
                imported_cost = (
                    round(DEMO_2025_IMPORT_COST_SEK - allocated_cost, 2)
                    if month == 12
                    else round(DEMO_2025_IMPORT_COST_SEK * imported_kwh / total_kwh, 2)
                )
                allocated_cost += imported_cost
                months.append(
                    HistoricalMonthlyEnergy(
                        year=2025,
                        month=month,
                        imported_kwh=imported_kwh,
                        imported_cost_sek=imported_cost,
                        source="Demo import baseline 2025",
                        estimated=True,
                    )
                )
            await historical_repo.upsert_months(akarp.id, months)
    await session.commit()
