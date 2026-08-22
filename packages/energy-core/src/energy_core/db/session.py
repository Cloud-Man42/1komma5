from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from energy_core.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    connect_args: dict = {}
    if settings.is_sqlite:
        connect_args["check_same_thread"] = False
    return create_async_engine(
        settings.database_url,
        echo=settings.is_development and settings.log_level == "DEBUG",
        connect_args=connect_args,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session
