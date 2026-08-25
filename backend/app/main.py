from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api import apple_devices, chargers_catalog, dashboard, ev_chargers, ev_sessions, prices, readings, semp, sites, solar_forecast, spa, system, vehicles, widget
from app.deps import set_session_factory
from app.widget_service import configure_snapshot_cache
from energy_core.chargers.chargeamps_config import assert_chargeamps_production_safe
from energy_core.config import Settings, get_settings
from energy_core.db.session import create_engine, create_session_factory

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings: Settings = app.state.settings
    try:
        assert_chargeamps_production_safe(app_env=settings.app_env.value)
    except RuntimeError as exc:
        logger.warning("Charge Amps production guard: %s", exc)
    engine: AsyncEngine = create_engine(settings)
    session_factory: async_sessionmaker[AsyncSession] = create_session_factory(engine)
    app.state.engine = engine
    app.state.session_factory = session_factory
    set_session_factory(session_factory, settings)
    configure_snapshot_cache(settings)
    yield
    await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    app = FastAPI(title="EMIC API", description="Energy Monitoring In a Cloud", version="0.1.0", lifespan=lifespan)
    app.state.settings = resolved_settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "environment": resolved_settings.app_env.value}

    app.include_router(sites.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(readings.router, prefix="/api")
    app.include_router(prices.router, prefix="/api")
    app.include_router(system.router, prefix="/api")
    app.include_router(ev_chargers.router, prefix="/api")
    app.include_router(chargers_catalog.router, prefix="/api")
    app.include_router(ev_sessions.router, prefix="/api")
    app.include_router(solar_forecast.router, prefix="/api")
    app.include_router(spa.router, prefix="/api")
    app.include_router(vehicles.router, prefix="/api")
    app.include_router(widget.router, prefix="/api")
    app.include_router(apple_devices.router, prefix="/api")
    app.include_router(semp.router)
    return app


app = create_app()
