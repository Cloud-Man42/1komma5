"""Marketplace metadata sync orchestration (Step 5C.1.5)."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from energy_core.config import AppEnvironment, Settings
from energy_core.platform.modules.marketplace.tuf_client import (
    MarketplaceMetadataClient,
    MarketplaceMetadataError,
)
from energy_core.platform.modules.marketplace.trust_cache import MarketplaceTrustCacheRepository
from energy_core.platform.modules.marketplace.types import (
    ApplySyncResult,
    MarketplaceSyncResult,
    MetadataErrorCode,
    SyncOutcome,
    trust_metadata_listeners,
)

logger = logging.getLogger(__name__)

_sync_lock = asyncio.Lock()


class MarketplaceSyncService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def build_client(self) -> MarketplaceMetadataClient:
        pinned = MarketplaceMetadataClient.load_pinned_root(self._settings.resolved_marketplace_trusted_root_path())
        require_https = self._settings.app_env == AppEnvironment.PRODUCTION
        return MarketplaceMetadataClient(
            metadata_base_url=self._settings.marketplace_metadata_url,
            targets_base_url=self._settings.marketplace_targets_url,
            pinned_root_bytes=pinned,
            require_https=require_https,
            max_metadata_bytes=self._settings.marketplace_metadata_max_bytes,
            connect_timeout=self._settings.marketplace_connect_timeout_seconds,
            read_timeout=self._settings.marketplace_read_timeout_seconds,
            tuf_state_dir=self._settings.resolved_marketplace_tuf_state_path(),
        )

    async def sync(self, session: AsyncSession) -> tuple[MarketplaceSyncResult, ApplySyncResult | None]:
        if not self._settings.marketplace_metadata_enabled:
            return (
                MarketplaceSyncResult(
                    outcome=SyncOutcome.SKIPPED,
                    message="Marketplace metadata sync disabled",
                ),
                None,
            )
        if not self._settings.marketplace_metadata_url.strip():
            return (
                MarketplaceSyncResult(
                    outcome=SyncOutcome.SKIPPED,
                    message="Marketplace metadata URL not configured",
                ),
                None,
            )

        if _sync_lock.locked():
            return (
                MarketplaceSyncResult(
                    outcome=SyncOutcome.IN_PROGRESS,
                    message="Marketplace metadata sync already in progress",
                    error_code=MetadataErrorCode.SYNC_IN_PROGRESS,
                    error_category=MetadataErrorCode.SYNC_IN_PROGRESS.value,
                ),
                None,
            )

        async with _sync_lock:
            repo = MarketplaceTrustCacheRepository(session)
            try:
                client = self.build_client()
            except MarketplaceMetadataError as exc:
                await repo.mark_offline(enabled=True, message=str(exc))
                await session.commit()
                return (
                    MarketplaceSyncResult(
                        outcome=SyncOutcome.FAILED,
                        message=str(exc),
                        error_code=exc.error_code,
                        error_category=exc.error_code.value if exc.error_code else exc.__class__.__name__,
                    ),
                    None,
                )

            tuf_result = await asyncio.to_thread(client.sync_metadata)
            apply_result: ApplySyncResult
            _, apply_result = await repo.apply_sync_result(
                enabled=True,
                result=tuf_result,
                now=datetime.now(UTC),
            )

            final_result = tuf_result
            if tuf_result.outcome == SyncOutcome.SUCCESS and not apply_result.promoted:
                if apply_result.rollback is not None:
                    message = (
                        f"{MetadataErrorCode.METADATA_ROLLBACK_DETECTED.value}: "
                        f"{apply_result.rollback.role} "
                        f"{apply_result.rollback.incoming_version} < "
                        f"{apply_result.rollback.trusted_version}"
                    )
                else:
                    row = await repo.get_or_create()
                    message = row.last_error or "Trusted cache rejected sync result"
                final_result = MarketplaceSyncResult(
                    outcome=SyncOutcome.REJECTED,
                    message=message,
                    versions=tuf_result.versions,
                    catalog=tuf_result.catalog,
                    revocations=tuf_result.revocations,
                    metadata_expires_at=tuf_result.metadata_expires_at,
                    error_code=MetadataErrorCode.METADATA_ROLLBACK_DETECTED
                    if apply_result.rollback
                    else MetadataErrorCode.INVALID_METADATA,
                    error_category=(
                        MetadataErrorCode.METADATA_ROLLBACK_DETECTED.value
                        if apply_result.rollback
                        else MetadataErrorCode.INVALID_METADATA.value
                    ),
                )

            await session.commit()
            if apply_result.promoted and apply_result.trust_event is not None:
                trust_metadata_listeners.emit(apply_result.trust_event)
            return final_result, apply_result

    async def sync_with_session_factory(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> MarketplaceSyncResult:
        async with session_factory() as session:
            result, _ = await self.sync(session)
            return result


def marketplace_sync_interval_seconds(settings: Settings) -> float:
    return float(settings.marketplace_sync_interval_seconds)
