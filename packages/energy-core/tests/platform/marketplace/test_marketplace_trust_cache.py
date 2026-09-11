"""Step 5C.1.5 trust cache hardening tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from energy_core.db.models.base import Base
from energy_core.platform.modules.marketplace.trust_cache import (
    MarketplaceTrustCacheRepository,
)
from energy_core.platform.modules.marketplace.types import (
    MarketplaceMetadataVersions,
    MarketplaceSyncResult,
    MetadataErrorCode,
    MetadataHealth,
    RevocationFreshness,
    SyncOutcome,
)


@pytest.fixture
async def cache_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def _success(
    *,
    versions: MarketplaceMetadataVersions,
    catalog: dict | None = None,
    revocations: dict | None = None,
) -> MarketplaceSyncResult:
    return MarketplaceSyncResult(
        outcome=SyncOutcome.SUCCESS,
        message="ok",
        versions=versions,
        catalog=catalog or {"modules": {}},
        revocations=revocations
        or {
            "bundle": {"schema_version": 1, "generation": versions.snapshot_version, "generated_at": "2026-09-07T12:00:00Z"},
            "revocations": [],
        },
        metadata_expires_at=datetime.now(UTC) + timedelta(days=1),
    )


@pytest.mark.asyncio
async def test_apply_success_increments_generation(cache_session: AsyncSession):
    repo = MarketplaceTrustCacheRepository(cache_session)
    result = _success(versions=MarketplaceMetadataVersions(1, 1, 1, 1))
    row, apply = await repo.apply_sync_result(enabled=True, result=result)
    assert apply.promoted is True
    assert row.cache_generation == 1
    assert row.cache_state == MetadataHealth.HEALTHY.value


@pytest.mark.asyncio
async def test_snapshot_rollback_rejected(cache_session: AsyncSession):
    repo = MarketplaceTrustCacheRepository(cache_session)
    v2 = _success(
        versions=MarketplaceMetadataVersions(2, 2, 2, 2),
        revocations={
            "bundle": {"schema_version": 1, "generation": 2, "generated_at": "2026-09-07T12:00:00Z"},
            "revocations": [{"revocation_id": "r1", "scope": "module", "action": "REVOKE"}],
        },
    )
    row_v2, _ = await repo.apply_sync_result(enabled=True, result=v2)
    before = MarketplaceTrustCacheRepository.snapshot_row(row_v2)

    v1 = _success(
        versions=MarketplaceMetadataVersions(2, 2, 1, 1),
        revocations={
            "bundle": {"schema_version": 1, "generation": 1, "generated_at": "2026-09-07T12:00:00Z"},
            "revocations": [],
        },
    )
    row_after, apply = await repo.apply_sync_result(enabled=True, result=v1)
    assert apply.promoted is False
    assert apply.rollback is not None
    assert apply.rollback.role == "snapshot"
    after = MarketplaceTrustCacheRepository.snapshot_row(row_after)
    assert after["cache_generation"] == before["cache_generation"]
    assert after["snapshot_version"] == before["snapshot_version"]
    assert "r1" in (after["revocations_json"] or "")


@pytest.mark.asyncio
async def test_targets_rollback_rejected(cache_session: AsyncSession):
    repo = MarketplaceTrustCacheRepository(cache_session)
    await repo.apply_sync_result(
        enabled=True,
        result=_success(versions=MarketplaceMetadataVersions(2, 2, 2, 2)),
    )
    row, apply = await repo.apply_sync_result(
        enabled=True,
        result=_success(versions=MarketplaceMetadataVersions(2, 2, 2, 1)),
    )
    assert apply.promoted is False
    assert apply.rollback is not None
    assert apply.rollback.role == "targets"
    assert row.targets_version == 2


@pytest.mark.asyncio
async def test_root_rollback_rejected(cache_session: AsyncSession):
    repo = MarketplaceTrustCacheRepository(cache_session)
    await repo.apply_sync_result(
        enabled=True,
        result=_success(versions=MarketplaceMetadataVersions(2, 2, 2, 2)),
    )
    _, apply = await repo.apply_sync_result(
        enabled=True,
        result=_success(versions=MarketplaceMetadataVersions(1, 2, 2, 2)),
    )
    assert apply.promoted is False
    assert apply.rollback is not None
    assert apply.rollback.role == "root"


@pytest.mark.asyncio
async def test_revocation_wipe_rejected(cache_session: AsyncSession):
    repo = MarketplaceTrustCacheRepository(cache_session)
    gen2 = _success(
        versions=MarketplaceMetadataVersions(2, 2, 2, 2),
        revocations={
            "bundle": {"schema_version": 1, "generation": 2, "generated_at": "2026-09-07T12:00:00Z"},
            "revocations": [
                {
                    "revocation_id": "rev-demo-001",
                    "scope": "module",
                    "action": "REVOKE",
                }
            ],
        },
    )
    row, _ = await repo.apply_sync_result(enabled=True, result=gen2)
    before = row.revocations_json

    gen1 = _success(
        versions=MarketplaceMetadataVersions(2, 2, 3, 3),
        revocations={
            "bundle": {"schema_version": 1, "generation": 1, "generated_at": "2026-09-07T12:00:00Z"},
            "revocations": [],
        },
    )
    row_after, apply = await repo.apply_sync_result(enabled=True, result=gen1)
    assert apply.promoted is False
    assert row_after.revocations_json == before


@pytest.mark.asyncio
async def test_revocation_supersession_keeps_monotonic_generation(cache_session: AsyncSession):
    repo = MarketplaceTrustCacheRepository(cache_session)
    gen2 = _success(
        versions=MarketplaceMetadataVersions(2, 2, 2, 2),
        revocations={
            "bundle": {"schema_version": 1, "generation": 2, "generated_at": "2026-09-07T12:00:00Z"},
            "revocations": [
                {"revocation_id": "rev-a", "scope": "module", "action": "REVOKE"},
            ],
        },
    )
    await repo.apply_sync_result(enabled=True, result=gen2)
    gen3 = _success(
        versions=MarketplaceMetadataVersions(2, 3, 3, 3),
        revocations={
            "bundle": {"schema_version": 1, "generation": 3, "generated_at": "2026-09-08T12:00:00Z"},
            "revocations": [
                {
                    "revocation_id": "rev-b",
                    "scope": "module",
                    "action": "SUPERSEDE",
                    "supersedes_revocation_id": "rev-a",
                }
            ],
        },
    )
    row, apply = await repo.apply_sync_result(enabled=True, result=gen3)
    assert apply.promoted is True
    assert row.revocation_generation == 3
    revocations = repo.parse_revocations(row) or {}
    ids = {item["revocation_id"] for item in revocations.get("revocations", [])}
    assert "rev-a" not in ids


@pytest.mark.asyncio
async def test_failed_sync_keeps_prior_cache(cache_session: AsyncSession):
    repo = MarketplaceTrustCacheRepository(cache_session)
    ok = _success(
        versions=MarketplaceMetadataVersions(1, 1, 1, 1),
        catalog={"modules": {"a": {}}},
    )
    await repo.apply_sync_result(enabled=True, result=ok)
    bad = MarketplaceSyncResult(outcome=SyncOutcome.REJECTED, message="bad sig")
    row, _ = await repo.apply_sync_result(enabled=True, result=bad)
    assert row.catalog_json is not None
    assert "a" in row.catalog_json
    assert row.sync_failed is True


@pytest.mark.asyncio
async def test_corrupt_cache_reports_invalid(cache_session: AsyncSession):
    repo = MarketplaceTrustCacheRepository(cache_session)
    await repo.apply_sync_result(enabled=True, result=_success(versions=MarketplaceMetadataVersions(1, 1, 1, 1)))
    row = await repo.get_or_create()
    row.revocations_json = "{not-json"
    view = await repo.build_status_view(enabled=True)
    assert view.metadata_health == MetadataHealth.INVALID


@pytest.mark.asyncio
async def test_separate_revocation_freshness(cache_session: AsyncSession):
    repo = MarketplaceTrustCacheRepository(cache_session)
    now = datetime.now(UTC)
    row = await repo.get_or_create()
    row.last_success_at = now
    row.catalog_updated_at = now - timedelta(hours=5)
    row.revocation_updated_at = now - timedelta(minutes=10)
    row.metadata_expires_at = now + timedelta(days=1)
    row.cache_state, row.revocation_state = repo._compute_states(row, now)
    assert row.cache_state == MetadataHealth.STALE.value
    assert row.revocation_state == RevocationFreshness.FRESH.value


@pytest.mark.asyncio
async def test_offline_keeps_cached_state(cache_session: AsyncSession):
    repo = MarketplaceTrustCacheRepository(cache_session)
    await repo.apply_sync_result(
        enabled=True,
        result=_success(versions=MarketplaceMetadataVersions(2, 2, 2, 2)),
    )
    row = await repo.mark_offline(enabled=True, message="network down")
    assert row.cache_state == MetadataHealth.OFFLINE.value
    assert row.root_version == 2


@pytest.mark.asyncio
async def test_disabled_status(cache_session: AsyncSession):
    repo = MarketplaceTrustCacheRepository(cache_session)
    view = await repo.build_status_view(enabled=False)
    assert view.metadata_health == MetadataHealth.DISABLED
    assert view.revocation_freshness == RevocationFreshness.UNAVAILABLE


@pytest.mark.asyncio
async def test_rollback_error_message(cache_session: AsyncSession):
    repo = MarketplaceTrustCacheRepository(cache_session)
    await repo.apply_sync_result(enabled=True, result=_success(versions=MarketplaceMetadataVersions(2, 2, 2, 2)))
    row, _ = await repo.apply_sync_result(
        enabled=True,
        result=_success(versions=MarketplaceMetadataVersions(2, 1, 1, 1)),
    )
    assert MetadataErrorCode.METADATA_ROLLBACK_DETECTED.value in (row.last_error or "")
