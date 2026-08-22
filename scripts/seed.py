"""CLI entry point for seeding sites."""

import asyncio

from energy_core.config import get_settings
from energy_core.db.session import create_engine, create_session_factory
from energy_core.seed import seed_sites


async def main() -> None:
    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        await seed_sites(session)
    await engine.dispose()
    print("Seeded sites: akarp, summer-house-denmark")


if __name__ == "__main__":
    asyncio.run(main())
