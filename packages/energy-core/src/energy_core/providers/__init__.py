from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import HeartbeatProviderKind, Settings
from energy_core.db.heartbeat_settings_repo import HeartbeatSettingsRepository
from energy_core.db.models import SiteModel
from energy_core.heartbeat_connection import HeartbeatConnectionType
from energy_core.providers.base import HeartbeatProvider
from energy_core.providers.mock import MockHeartbeatProvider
from energy_core.providers.onekommafive import (
    HeartbeatRuntimeConfig,
    OneKommaFiveHeartbeatProvider,
    SiteRuntimeInfo,
)


async def create_heartbeat_provider_from_db(session: AsyncSession) -> HeartbeatProvider:
    repo = HeartbeatSettingsRepository(session)
    record = await repo.get_record()
    sites = await repo.list_site_mappings()

    if record.connection_type == HeartbeatConnectionType.MOCK.value:
        return MockHeartbeatProvider()

    api_token = await repo.ensure_api_token()
    password, _ = await repo.get_secrets()

    async def refresh_token() -> str:
        return await repo.ensure_api_token(force=True)

    refresh = refresh_token if password and record.username else None

    db_sites = await session.scalars(select(SiteModel).order_by(SiteModel.name))
    site_timezones = {site.slug: site.timezone for site in db_sites}

    runtime = HeartbeatRuntimeConfig(
        connection_type=record.connection_type,
        api_url=record.api_url,
        username=record.username,
        password=password,
        api_token=api_token,
        site_system_ids={
            site.slug: site.external_system_id for site in sites if site.external_system_id
        },
        site_info={
            site.slug: SiteRuntimeInfo(
                name=site.name,
                timezone=site_timezones.get(site.slug, "UTC"),
            )
            for site in sites
            if site.external_system_id
        },
        refresh_token=refresh,
    )
    return OneKommaFiveHeartbeatProvider(runtime)


def create_heartbeat_provider(settings: Settings) -> HeartbeatProvider:
    if settings.heartbeat_provider == HeartbeatProviderKind.MOCK:
        return MockHeartbeatProvider()
    if settings.heartbeat_provider == HeartbeatProviderKind.ONEKOMMAFIVE:
        runtime = HeartbeatRuntimeConfig(
            connection_type=HeartbeatConnectionType.CLOUD.value,
            api_url=settings.heartbeat_api_url or None,
            username="",
            password="",
            api_token=settings.heartbeat_api_key,
            site_system_ids={},
        )
        return OneKommaFiveHeartbeatProvider(runtime)
    raise ValueError(f"Unknown heartbeat provider: {settings.heartbeat_provider}")
