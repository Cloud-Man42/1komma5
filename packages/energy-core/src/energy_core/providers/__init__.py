import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import HeartbeatProviderKind, Settings
from energy_core.db.heartbeat_account_repo import HeartbeatAccountRepository
from energy_core.db.heartbeat_settings_repo import HeartbeatSettingsRepository
from energy_core.db.models import SiteModel
from energy_core.integrations.heartbeat.auth import HeartbeatAuthError
from energy_core.integrations.heartbeat.client_factory import create_heartbeat_client
from energy_core.integrations.heartbeat.connection import HeartbeatConnectionType

logger = logging.getLogger(__name__)
from energy_core.providers.base import HeartbeatProvider
from energy_core.providers.mock import MockHeartbeatProvider
from energy_core.providers.onekommafive import (
    HeartbeatRuntimeConfig,
    OneKommaFiveHeartbeatProvider,
    SiteHeartbeatBinding,
    SiteRuntimeInfo,
)


async def create_heartbeat_provider_from_db(session: AsyncSession) -> HeartbeatProvider:
    settings_repo = HeartbeatSettingsRepository(session)
    account_repo = HeartbeatAccountRepository(session)
    record = await settings_repo.get_record()

    if record.connection_type == HeartbeatConnectionType.MOCK.value:
        return MockHeartbeatProvider()

    sites = await session.scalars(select(SiteModel).order_by(SiteModel.name))
    bindings: list[SiteHeartbeatBinding] = []
    client_cache: dict[int, object] = {}

    for site in sites:
        system_id = account_repo.resolve_system_id(site)
        if not system_id:
            continue
        account = await account_repo.resolve_account_for_site(site)
        if account is None:
            continue
        if account.id not in client_cache:
            try:
                client = await create_heartbeat_client(session, account_id=account.id)
            except HeartbeatAuthError:
                logger.warning(
                    "Skipping Heartbeat account id=%s for site %s: authentication failed",
                    account.id,
                    site.slug,
                )
                continue
            if client is None:
                continue
            client_cache[account.id] = client
        bindings.append(
            SiteHeartbeatBinding(
                slug=site.slug,
                name=site.name,
                timezone=site.timezone,
                system_id=system_id,
                account_id=account.id,
                provider=account.provider,
                client=client_cache[account.id],
            )
        )

    if bindings:
        return OneKommaFiveHeartbeatProvider(
            HeartbeatRuntimeConfig(
                connection_type=record.connection_type,
                api_url=record.api_url,
                username="",
                password="",
                api_token="",
                site_system_ids={},
                site_bindings=tuple(bindings),
            )
        )

    api_token = await settings_repo.ensure_api_token()
    password, _ = await settings_repo.get_secrets()

    async def refresh_token() -> str:
        return await settings_repo.ensure_api_token(force=True)

    refresh = refresh_token if password and record.username else None
    legacy_sites = await settings_repo.list_site_mappings()

    runtime = HeartbeatRuntimeConfig(
        connection_type=record.connection_type,
        api_url=record.api_url,
        username=record.username,
        password=password,
        api_token=api_token,
        site_system_ids={
            site.slug: site.external_system_id
            for site in legacy_sites
            if site.external_system_id
        },
        site_info={
            site.slug: SiteRuntimeInfo(name=site.name, timezone=site.timezone)
            for site in legacy_sites
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
