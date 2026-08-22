"""One-shot collector poll for verification."""

import asyncio

from energy_core.config import get_settings
from energy_core.db.repositories import EnergyReadingRepository, SiteRepository
from energy_core.db.session import create_engine, create_session_factory
from energy_core.normalization import normalize_reading
from energy_core.providers import create_heartbeat_provider
from energy_core.seed import seed_sites


async def main() -> None:
    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    provider = create_heartbeat_provider(settings)

    async with session_factory() as session:
        await seed_sites(session)

    readings = await provider.fetch_readings()
    async with session_factory() as session:
        site_repo = SiteRepository(session)
        reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
        for raw in readings:
            normalized = normalize_reading(raw)
            site = await site_repo.get_by_slug(normalized.site_slug)
            assert site is not None
            await reading_repo.upsert_reading(site.id, normalized)
        await session.commit()

    print(f"Stored {len(readings)} readings")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
