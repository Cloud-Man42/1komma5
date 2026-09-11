"""Marketplace trust cache repository (Step 5C.1.5)."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models.marketplace_trust_cache import MarketplaceTrustCacheModel
from energy_core.platform.modules.marketplace.revocation_policy import (
    RevocationPolicyError,
    bundle_content_hash,
    merge_revocation_bundles,
    parse_revocation_bundle,
    revocations_changed,
    validate_revocation_monotonicity,
)
from energy_core.platform.modules.marketplace.types import (
    ApplySyncResult,
    MarketplaceMetadataVersions,
    MarketplaceStatusView,
    MarketplaceSyncResult,
    MetadataErrorCode,
    MetadataHealth,
    RevocationFreshness,
    RollbackRejection,
    SyncOutcome,
    TrustMetadataUpdatedEvent,
)

logger = logging.getLogger(__name__)


class CacheValidationError(Exception):
    """Trusted cache payload is corrupt or inconsistent."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.error_code = MetadataErrorCode.INVALID_CACHE


class MarketplaceTrustCacheRepository:
    CACHE_KEY = "default"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self) -> MarketplaceTrustCacheModel:
        row = await self._session.scalar(
            select(MarketplaceTrustCacheModel).where(
                MarketplaceTrustCacheModel.cache_key == self.CACHE_KEY
            )
        )
        if row is None:
            row = MarketplaceTrustCacheModel(cache_key=self.CACHE_KEY)
            self._session.add(row)
            await self._session.flush()
        return row

    async def apply_sync_result(
        self,
        *,
        enabled: bool,
        result: MarketplaceSyncResult,
        now: datetime | None = None,
    ) -> tuple[MarketplaceTrustCacheModel, ApplySyncResult]:
        now = now or datetime.now(UTC)
        row = await self.get_or_create()
        row.enabled = enabled
        row.last_attempt_at = now

        if result.outcome != SyncOutcome.SUCCESS or result.versions is None:
            row.sync_failed = True
            row.last_error = result.message
            if row.last_success_at is None:
                row.cache_state = MetadataHealth.UNAVAILABLE.value
                row.revocation_state = RevocationFreshness.UNAVAILABLE.value
            else:
                try:
                    self._validate_cache_row(row)
                    row.cache_state, row.revocation_state = self._compute_states(row, now)
                except CacheValidationError as exc:
                    row.cache_state = MetadataHealth.INVALID.value
                    row.revocation_state = RevocationFreshness.UNAVAILABLE.value
                    row.last_error = str(exc)
            await self._session.flush()
            return row, ApplySyncResult(row_changed=True, promoted=False)

        self._validate_cache_row(row)
        rollback = self._detect_metadata_rollback(row, result.versions)
        if rollback is not None:
            row.sync_failed = True
            row.last_error = (
                f"{MetadataErrorCode.METADATA_ROLLBACK_DETECTED.value}: "
                f"{rollback.role} {rollback.incoming_version} < {rollback.trusted_version}"
            )
            row.cache_state, row.revocation_state = self._compute_states(row, now)
            await self._session.flush()
            return row, ApplySyncResult(row_changed=True, promoted=False, rollback=rollback)

        incoming_revocations = result.revocations or {}
        try:
            incoming_bundle = parse_revocation_bundle(incoming_revocations)
            validate_revocation_monotonicity(
                trusted_generation=row.revocation_generation,
                trusted_hash=row.revocation_content_hash,
                incoming=incoming_bundle,
            )
            merged_revocations = merge_revocation_bundles(
                trusted_raw=self.parse_revocations(row),
                incoming=incoming_bundle,
                incoming_raw=incoming_revocations,
            )
        except RevocationPolicyError as exc:
            row.sync_failed = True
            row.last_error = str(exc)
            row.cache_state, row.revocation_state = self._compute_states(row, now)
            await self._session.flush()
            rejected = ApplySyncResult(row_changed=True, promoted=False)
            if exc.error_code == MetadataErrorCode.METADATA_ROLLBACK_DETECTED:
                rejected = ApplySyncResult(
                    row_changed=True,
                    promoted=False,
                    rollback=RollbackRejection(
                        role="revocations",
                        trusted_version=row.revocation_generation or 0,
                        incoming_version=incoming_revocations.get("bundle", {}).get("generation", 0),
                    ),
                )
            return row, rejected

        incoming_advisories = result.advisories
        advisories_changed = False
        merged_advisories: dict[str, Any] | None = None
        incoming_advisory_bundle = None
        if incoming_advisories is not None:
            from energy_core.platform.modules.supply_chain.advisory_policy import (
                AdvisoryPolicyError,
                bundle_content_hash as advisory_bundle_content_hash,
                parse_advisory_bundle,
                validate_advisory_monotonicity,
            )

            try:
                incoming_advisory_bundle = parse_advisory_bundle(incoming_advisories)
                validate_advisory_monotonicity(
                    trusted_generation=row.advisories_generation,
                    trusted_hash=row.advisories_content_hash,
                    incoming=incoming_advisory_bundle,
                )
                from energy_core.platform.modules.supply_chain.advisory_policy import merge_advisory_bundles

                prev_advisories = self.parse_advisories(row)
                merged_advisories = merge_advisory_bundles(
                    trusted_raw=prev_advisories,
                    incoming=incoming_advisory_bundle,
                    incoming_raw=incoming_advisories,
                )
                advisories_changed = (prev_advisories or {}) != (merged_advisories or {})
            except AdvisoryPolicyError as exc:
                row.sync_failed = True
                row.last_error = str(exc)
                row.cache_state, row.revocation_state = self._compute_states(row, now)
                await self._session.flush()
                rejected = ApplySyncResult(row_changed=True, promoted=False)
                if exc.error_code == MetadataErrorCode.METADATA_ROLLBACK_DETECTED:
                    rejected = ApplySyncResult(
                        row_changed=True,
                        promoted=False,
                        rollback=RollbackRejection(
                            role="advisories",
                            trusted_version=row.advisories_generation or 0,
                            incoming_version=incoming_advisories.get("bundle", {}).get("generation", 0),
                        ),
                    )
                return row, rejected

        prev_revocations = self.parse_revocations(row)
        prev_root = row.root_version
        rev_changed = revocations_changed(before_raw=prev_revocations, after_raw=merged_revocations)

        row.cache_generation += 1
        row.root_version = result.versions.root_version
        row.timestamp_version = result.versions.timestamp_version
        row.snapshot_version = result.versions.snapshot_version
        row.targets_version = result.versions.targets_version
        row.catalog_json = json.dumps(result.catalog or {}, sort_keys=True)
        row.revocations_json = json.dumps(merged_revocations, sort_keys=True)
        row.revocation_generation = incoming_bundle.generation
        row.revocation_content_hash = bundle_content_hash(merged_revocations)
        if merged_advisories is not None and incoming_advisory_bundle is not None:
            row.advisories_json = json.dumps(merged_advisories, sort_keys=True)
            row.advisories_generation = incoming_advisory_bundle.generation
            row.advisories_content_hash = advisory_bundle_content_hash(merged_advisories)
            row.advisories_updated_at = now if advisories_changed else (row.advisories_updated_at or now)
        row.metadata_expires_at = result.metadata_expires_at
        row.last_success_at = now
        row.last_error = None
        row.sync_failed = False
        row.catalog_updated_at = now
        row.revocation_updated_at = now if rev_changed else (row.revocation_updated_at or now)
        row.cache_state, row.revocation_state = self._compute_states(row, now)

        trust_event = TrustMetadataUpdatedEvent(
            cache_generation=row.cache_generation,
            versions=result.versions,
            catalog=result.catalog,
            revocations=merged_revocations,
        )
        root_rotated = (
            prev_root is not None
            and result.versions.root_version > prev_root
        )
        await self._session.flush()
        return row, ApplySyncResult(
            row_changed=True,
            promoted=True,
            revocations_changed=rev_changed,
            advisories_changed=advisories_changed,
            root_rotated=root_rotated,
            trust_event=trust_event,
        )

    async def mark_offline(self, *, enabled: bool, message: str) -> MarketplaceTrustCacheModel:
        now = datetime.now(UTC)
        row = await self.get_or_create()
        row.enabled = enabled
        row.last_attempt_at = now
        row.last_error = message
        row.sync_failed = True
        try:
            self._validate_cache_row(row)
        except CacheValidationError:
            row.cache_state = MetadataHealth.INVALID.value
            row.revocation_state = RevocationFreshness.UNAVAILABLE.value
        else:
            if row.last_success_at is None:
                row.cache_state = MetadataHealth.OFFLINE.value
                row.revocation_state = RevocationFreshness.UNAVAILABLE.value
            else:
                row.cache_state = MetadataHealth.OFFLINE.value
                _, rev_state = self._compute_states(row, now)
                row.revocation_state = rev_state
        await self._session.flush()
        return row

    async def build_status_view(self, *, enabled: bool) -> MarketplaceStatusView:
        row = await self.get_or_create()
        now = datetime.now(UTC)
        if not enabled:
            return MarketplaceStatusView(
                enabled=False,
                metadata_health=MetadataHealth.DISABLED,
                revocation_freshness=RevocationFreshness.UNAVAILABLE,
                last_sync=self._ensure_utc(row.last_attempt_at) if row.last_attempt_at else None,
                last_success=self._ensure_utc(row.last_success_at) if row.last_success_at else None,
                last_error=row.last_error,
                sync_failed=row.sync_failed,
                offline=False,
                root_version=row.root_version,
                timestamp_version=row.timestamp_version,
                snapshot_version=row.snapshot_version,
                targets_version=row.targets_version,
                catalog_age_seconds=None,
                revocation_age_seconds=None,
                cache_generation=row.cache_generation,
                catalog_status=MetadataHealth.DISABLED.value,
                revocation_status=RevocationFreshness.UNAVAILABLE.value,
                revocation_generation=row.revocation_generation,
            )

        try:
            self._validate_cache_row(row)
        except CacheValidationError as exc:
            return MarketplaceStatusView(
                enabled=True,
                metadata_health=MetadataHealth.INVALID,
                revocation_freshness=RevocationFreshness.UNAVAILABLE,
                last_sync=self._ensure_utc(row.last_attempt_at) if row.last_attempt_at else None,
                last_success=self._ensure_utc(row.last_success_at) if row.last_success_at else None,
                last_error=str(exc),
                sync_failed=True,
                offline=False,
                root_version=row.root_version,
                timestamp_version=row.timestamp_version,
                snapshot_version=row.snapshot_version,
                targets_version=row.targets_version,
                catalog_age_seconds=None,
                revocation_age_seconds=None,
                cache_generation=row.cache_generation,
                catalog_status=MetadataHealth.INVALID.value,
                revocation_status=RevocationFreshness.UNAVAILABLE.value,
                revocation_generation=row.revocation_generation,
            )

        last_success = self._ensure_utc(row.last_success_at) if row.last_success_at else None
        catalog_updated = (
            self._ensure_utc(row.catalog_updated_at)
            if row.catalog_updated_at
            else last_success
        )
        revocation_updated = (
            self._ensure_utc(row.revocation_updated_at)
            if row.revocation_updated_at
            else last_success
        )
        catalog_age = (now - catalog_updated).total_seconds() if catalog_updated else None
        revocation_age = (now - revocation_updated).total_seconds() if revocation_updated else None
        metadata_health = MetadataHealth(row.cache_state)
        revocation_freshness = RevocationFreshness(row.revocation_state)
        return MarketplaceStatusView(
            enabled=enabled,
            metadata_health=metadata_health,
            revocation_freshness=revocation_freshness,
            last_sync=self._ensure_utc(row.last_attempt_at) if row.last_attempt_at else None,
            last_success=last_success,
            last_error=row.last_error,
            sync_failed=row.sync_failed,
            offline=metadata_health == MetadataHealth.OFFLINE,
            root_version=row.root_version,
            timestamp_version=row.timestamp_version,
            snapshot_version=row.snapshot_version,
            targets_version=row.targets_version,
            catalog_age_seconds=catalog_age,
            revocation_age_seconds=revocation_age,
            cache_generation=row.cache_generation,
            catalog_status=metadata_health.value,
            revocation_status=revocation_freshness.value,
            revocation_generation=row.revocation_generation,
        )

    @staticmethod
    def _detect_metadata_rollback(
        row: MarketplaceTrustCacheModel,
        incoming: MarketplaceMetadataVersions,
    ) -> RollbackRejection | None:
        if row.last_success_at is None:
            return None
        checks = (
            ("root", incoming.root_version, row.root_version),
            ("timestamp", incoming.timestamp_version, row.timestamp_version),
            ("snapshot", incoming.snapshot_version, row.snapshot_version),
            ("targets", incoming.targets_version, row.targets_version),
        )
        for role, incoming_version, trusted_version in checks:
            if trusted_version is not None and incoming_version < trusted_version:
                return RollbackRejection(
                    role=role,
                    trusted_version=trusted_version,
                    incoming_version=incoming_version,
                )
        return None

    def _validate_cache_row(self, row: MarketplaceTrustCacheModel) -> None:
        if row.last_success_at is None:
            return
        for field_name in (
            "root_version",
            "timestamp_version",
            "snapshot_version",
            "targets_version",
        ):
            value = getattr(row, field_name)
            if value is None or value < 1:
                raise CacheValidationError(f"Invalid trusted {field_name}")
        if row.catalog_json:
            try:
                json.loads(row.catalog_json)
            except json.JSONDecodeError as exc:
                raise CacheValidationError("Corrupt catalog_json") from exc
        if row.revocations_json:
            try:
                revocations = json.loads(row.revocations_json)
            except json.JSONDecodeError as exc:
                raise CacheValidationError("Corrupt revocations_json") from exc
            parse_revocation_bundle(revocations)

    @staticmethod
    def _ensure_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _compute_states(
        self, row: MarketplaceTrustCacheModel, now: datetime
    ) -> tuple[str, str]:
        now = self._ensure_utc(now)
        if row.last_success_at is None:
            return MetadataHealth.UNINITIALIZED.value, RevocationFreshness.UNAVAILABLE.value

        expires = row.metadata_expires_at
        if expires is not None:
            expires = self._ensure_utc(expires)
            if now >= expires:
                return MetadataHealth.EXPIRED.value, RevocationFreshness.EXPIRED.value

        catalog_updated = row.catalog_updated_at or row.last_success_at
        revocation_updated = row.revocation_updated_at or row.last_success_at
        catalog_updated = self._ensure_utc(catalog_updated)
        revocation_updated = self._ensure_utc(revocation_updated)
        catalog_age = (now - catalog_updated).total_seconds()
        revocation_age = (now - revocation_updated).total_seconds()

        catalog_state = MetadataHealth.HEALTHY.value
        if catalog_age > 86400:
            catalog_state = MetadataHealth.STALE.value
        elif catalog_age > 3600:
            catalog_state = MetadataHealth.STALE.value

        if revocation_age > 86400:
            revocation_state = RevocationFreshness.EXPIRED.value
        elif revocation_age > 3600:
            revocation_state = RevocationFreshness.STALE.value
        else:
            revocation_state = RevocationFreshness.FRESH.value

        return catalog_state, revocation_state

    @staticmethod
    def parse_catalog(row: MarketplaceTrustCacheModel) -> dict[str, Any] | None:
        if not row.catalog_json:
            return None
        return json.loads(row.catalog_json)

    @staticmethod
    def parse_advisories(row: MarketplaceTrustCacheModel) -> dict[str, Any] | None:
        if not row.advisories_json:
            return None
        return json.loads(row.advisories_json)

    @staticmethod
    def parse_revocations(row: MarketplaceTrustCacheModel) -> dict[str, Any] | None:
        if not row.revocations_json:
            return None
        return json.loads(row.revocations_json)

    @staticmethod
    def snapshot_row(row: MarketplaceTrustCacheModel) -> dict[str, Any]:
        return {
            "cache_generation": row.cache_generation,
            "root_version": row.root_version,
            "timestamp_version": row.timestamp_version,
            "snapshot_version": row.snapshot_version,
            "targets_version": row.targets_version,
            "catalog_json": row.catalog_json,
            "revocations_json": row.revocations_json,
            "revocation_generation": row.revocation_generation,
            "last_success_at": row.last_success_at,
        }
