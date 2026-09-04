"""Apply TimescaleDB retention and compression policies (idempotent)."""

from __future__ import annotations

import asyncio

from energy_core.config import get_settings
from energy_core.db.session import create_engine, create_session_factory
from energy_core.db.timescale_retention import ensure_timescale_compression, ensure_timescale_retention


async def main() -> None:
    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        retention = await ensure_timescale_retention(session, settings)
        compression = await ensure_timescale_compression(session, settings)
        await session.commit()
        print({"retention": retention, "compression": compression})


if __name__ == "__main__":
    asyncio.run(main())
