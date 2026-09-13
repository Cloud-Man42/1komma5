import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api import admin_audit, auth, auth_audit, apple_devices, chargefinder, chargers_catalog, climate, dashboard, devices, display, energy_control, energy_orchestration, ev_chargers, ev_sessions, external_modules, forecast_learning, heartbeat_accounts, heartbeat_audit, heartbeat_bridge, horizon_optimizer, integration_health, marketplace_distribution, marketplace_metadata, mobile, module_governance, module_packages, module_publishers, module_runtime, module_store, multi_site, operations, platform_tenants, price_engine, prices, readings, roles, semp, site_modules, sites, snapshot, solar_forecast, solar_intelligence, spa, system, tenants, user_preferences, users, vehicles, widget
from app.security_middleware import SecurityHeadersMiddleware
from app.user_auth import require_authenticated
from app.deps import set_session_factory
from app.marketplace_sync import marketplace_metadata_sync_loop
from app.widget_service import configure_snapshot_cache
from energy_core.integrations.chargeamps.config import assert_chargeamps_production_safe
from energy_core.platform.modules.bootstrap import register_default_modules
from energy_core.platform.modules.packages.builtin_adapter import BuiltInModuleAdapter
from energy_core.platform.modules.packages.loader import load_installed_module_packages
from energy_core.platform.modules.handlers import register_default_module_handlers
from energy_core.auth.bootstrap import ensure_emic_auth_bootstrap
from energy_core.config import Settings, assert_emic_admin_token_production_safe, cors_origins_list, get_settings
from energy_core.db.session import create_engine, create_session_factory
from energy_core.performance.middleware import PerformanceMiddleware
from energy_core.performance.sql_tracking import install_sql_tracking

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings: Settings = app.state.settings
    assert_chargeamps_production_safe(app_env=settings.app_env.value)
    assert_emic_admin_token_production_safe(
        app_env=settings.app_env.value,
        emic_admin_token=settings.emic_admin_token,
        emic_user_auth_enabled=settings.emic_user_auth_enabled,
    )
    register_default_modules()
    BuiltInModuleAdapter.enrich_registry()
    register_default_module_handlers()
    engine: AsyncEngine = create_engine(settings)
    session_factory: async_sessionmaker[AsyncSession] = create_session_factory(engine)
    await load_installed_module_packages(session_factory, settings=settings)
    async with session_factory() as session:
        from energy_core.integrations.heartbeat.account_bootstrap import ensure_env_heartbeat_accounts

        await ensure_env_heartbeat_accounts(session, settings)
        await ensure_emic_auth_bootstrap(session, settings)
        await session.commit()
    app.state.engine = engine
    app.state.session_factory = session_factory
    set_session_factory(session_factory, settings)
    configure_snapshot_cache(settings)
    install_sql_tracking(engine)
    logging.getLogger().addFilter(
        __import__("energy_core.performance.logging_context", fromlist=["RequestIdFilter"]).RequestIdFilter()
    )
    stop_event = asyncio.Event()
    app.state.marketplace_sync_stop = stop_event
    sync_task: asyncio.Task | None = None
    if settings.marketplace_metadata_enabled:
        sync_task = asyncio.create_task(
            marketplace_metadata_sync_loop(session_factory, settings, stop_event=stop_event)
        )
        app.state.marketplace_sync_task = sync_task
    yield
    stop_event.set()
    if sync_task is not None:
        sync_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sync_task
    await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    register_default_modules()
    BuiltInModuleAdapter.enrich_registry()
    register_default_module_handlers()
    app = FastAPI(title="EMIC API", description="Energy Monitoring In a Cloud", version="0.1.0", lifespan=lifespan)
    app.state.settings = resolved_settings

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(PerformanceMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins_list(resolved_settings),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Outermost: trust X-Forwarded-* from Caddy so request.url.scheme is https behind TLS termination.
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "environment": resolved_settings.app_env.value}

    app_deps = [Depends(require_authenticated)]

    app.include_router(auth.router, prefix="/api")
    app.include_router(tenants.router, prefix="/api", dependencies=app_deps)
    app.include_router(platform_tenants.router, prefix="/api", dependencies=app_deps)
    app.include_router(sites.router, prefix="/api", dependencies=app_deps)
    app.include_router(snapshot.router, prefix="/api", dependencies=app_deps)
    app.include_router(dashboard.router, prefix="/api", dependencies=app_deps)
    app.include_router(readings.router, prefix="/api", dependencies=app_deps)
    app.include_router(prices.router, prefix="/api", dependencies=app_deps)
    app.include_router(system.router, prefix="/api", dependencies=app_deps)
    app.include_router(ev_chargers.router, prefix="/api", dependencies=app_deps)
    app.include_router(chargers_catalog.router, prefix="/api", dependencies=app_deps)
    app.include_router(ev_sessions.router, prefix="/api", dependencies=app_deps)
    app.include_router(solar_forecast.router, prefix="/api", dependencies=app_deps)
    app.include_router(solar_intelligence.router, prefix="/api", dependencies=app_deps)
    app.include_router(spa.router, prefix="/api", dependencies=app_deps)
    app.include_router(energy_orchestration.router, prefix="/api", dependencies=app_deps)
    app.include_router(vehicles.router, prefix="/api", dependencies=app_deps)
    app.include_router(widget.router, prefix="/api")
    app.include_router(display.router, prefix="/api")
    app.include_router(apple_devices.router, prefix="/api", dependencies=app_deps)
    app.include_router(heartbeat_accounts.router, prefix="/api", dependencies=app_deps)
    app.include_router(heartbeat_bridge.router, prefix="/api", dependencies=app_deps)
    app.include_router(heartbeat_audit.router, prefix="/api", dependencies=app_deps)
    app.include_router(forecast_learning.router, prefix="/api", dependencies=app_deps)
    app.include_router(energy_control.router, prefix="/api", dependencies=app_deps)
    app.include_router(chargefinder.router, prefix="/api", dependencies=app_deps)
    app.include_router(price_engine.router, prefix="/api", dependencies=app_deps)
    app.include_router(horizon_optimizer.router, prefix="/api", dependencies=app_deps)
    app.include_router(integration_health.router, prefix="/api", dependencies=app_deps)
    app.include_router(devices.router, prefix="/api", dependencies=app_deps)
    app.include_router(climate.router, prefix="/api", dependencies=app_deps)
    app.include_router(external_modules.router, prefix="/api", dependencies=app_deps)
    app.include_router(site_modules.router, prefix="/api", dependencies=app_deps)
    app.include_router(module_packages.router, prefix="/api", dependencies=app_deps)
    app.include_router(module_store.router, prefix="/api", dependencies=app_deps)
    app.include_router(module_publishers.router, prefix="/api", dependencies=app_deps)
    app.include_router(marketplace_metadata.router, prefix="/api", dependencies=app_deps)
    app.include_router(marketplace_distribution.router, prefix="/api", dependencies=app_deps)
    app.include_router(module_governance.router, prefix="/api", dependencies=app_deps)
    app.include_router(module_runtime.router, prefix="/api", dependencies=app_deps)
    app.include_router(operations.router, prefix="/api", dependencies=app_deps)
    app.include_router(admin_audit.router, prefix="/api", dependencies=app_deps)
    app.include_router(users.router, prefix="/api", dependencies=app_deps)
    app.include_router(roles.router, prefix="/api", dependencies=app_deps)
    app.include_router(auth_audit.router, prefix="/api", dependencies=app_deps)
    app.include_router(multi_site.router, prefix="/api", dependencies=app_deps)
    app.include_router(mobile.router, prefix="/api", dependencies=app_deps)
    app.include_router(user_preferences.router, prefix="/api", dependencies=app_deps)
    app.include_router(semp.router)
    return app


app = create_app()
