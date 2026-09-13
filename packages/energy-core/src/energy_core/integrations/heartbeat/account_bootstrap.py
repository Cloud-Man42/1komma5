"""Bootstrap Heartbeat accounts from environment (no secrets in git)."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings
from energy_core.db.heartbeat_account_repo import HeartbeatAccountRepository
from energy_core.db.models import SiteModel
from energy_core.integrations.heartbeat.auth import HeartbeatAuthError
from energy_core.integrations.heartbeat.auth_probe import probe_heartbeat_credentials
from energy_core.integrations.heartbeat.connection import HeartbeatConnectionType
from energy_core.integrations.heartbeat.discovery_service import discover_system_id_for_serial

logger = logging.getLogger(__name__)

ENV_ACCOUNT_SLUG = "denmark"
ENV_SITE_SLUG = "summer-house-denmark"


async def ensure_env_heartbeat_accounts(session: AsyncSession, settings: Settings) -> None:
    """Create/update optional accounts from env and link sites when configured."""
    repo = HeartbeatAccountRepository(session)
    username = settings.heartbeat_account_denmark_username.strip()
    password = settings.heartbeat_account_denmark_password
    if not username or not password:
        return

    account = await repo.get_by_slug(ENV_ACCOUNT_SLUG)
    if account is None:
        try:
            probe = await probe_heartbeat_credentials(username, password)
        except HeartbeatAuthError:
            logger.warning("Env Heartbeat account login failed", extra={"slug": ENV_ACCOUNT_SLUG})
            return
        record = await repo.create(
            slug=ENV_ACCOUNT_SLUG,
            name="Danmark Heartbeat Account",
            provider=probe.provider,
            connection_type=probe.connection_type,
            host=probe.host,
            port=probe.port,
            use_tls=probe.use_tls,
            api_path=probe.api_path,
            auth_domain=probe.auth_domain,
            auth_realm=probe.auth_realm,
            auth_client_id=probe.auth_client_id,
            username=username,
            password=password,
            is_enabled=True,
        )
        await repo.apply_auth_probe(record.id, probe)
        logger.info("Created Heartbeat account from env", extra={"slug": ENV_ACCOUNT_SLUG, "provider": probe.provider})
    else:
        await repo.update(account.id, username=username, password=password, is_enabled=True)
        try:
            probe = await probe_heartbeat_credentials(username, password)
            await repo.apply_auth_probe(account.id, probe)
        except HeartbeatAuthError:
            pass

    site = await session.scalar(select(SiteModel).where(SiteModel.slug == ENV_SITE_SLUG))
    account = await repo.get_by_slug(ENV_ACCOUNT_SLUG)
    if site is not None and account is not None:
        site.heartbeat_account_id = account.id
        if site.heartbeat_serial_number and not site.heartbeat_system_id:
            try:
                discovery = await discover_system_id_for_serial(session, account.id, site.heartbeat_serial_number)
                if discovery.found and discovery.resolved_system_id:
                    site.heartbeat_system_id = discovery.resolved_system_id
                    site.external_system_id = discovery.resolved_system_id
                if discovery.resolved_device_id and not site.heartbeat_device_id:
                    site.heartbeat_device_id = discovery.resolved_device_id
                if discovery.resolved_asset_id and not site.heartbeat_asset_id:
                    site.heartbeat_asset_id = discovery.resolved_asset_id
                if discovery.resolved_site_id and not site.heartbeat_site_id:
                    site.heartbeat_site_id = discovery.resolved_site_id
            except HeartbeatAuthError:
                pass
        try:
            await repo.ensure_api_token(account.id, force=False)
        except HeartbeatAuthError:
            pass
        await session.flush()
        logger.info(
            "Linked site to env Heartbeat account",
            extra={"site": ENV_SITE_SLUG, "account": ENV_ACCOUNT_SLUG},
        )
