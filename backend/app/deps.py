from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from energy_core.config import Settings
from energy_core.db.repositories import EnergyReadingRepository, SiteRepository

_session_factory: async_sessionmaker[AsyncSession] | None = None
_settings: Settings | None = None


def set_session_factory(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    global _session_factory, _settings
    _session_factory = session_factory
    _settings = settings


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        raise RuntimeError("Session factory not initialized")
    async with _session_factory() as session:
        yield session


def get_app_settings() -> Settings:
    if _settings is None:
        raise RuntimeError("Settings not initialized")
    return _settings


def get_site_repository(session: AsyncSession = Depends(get_db_session)) -> SiteRepository:
    return SiteRepository(session)


def get_reading_repository(session: AsyncSession = Depends(get_db_session)) -> EnergyReadingRepository:
    settings = get_app_settings()
    return EnergyReadingRepository(
        session,
        is_sqlite=settings.is_sqlite,
        enable_timescaledb=settings.enable_timescaledb,
    )
