"""Publisher lifecycle repository tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.platform.modules.governance.publisher_repository import PublisherGovernanceError, PublisherRepository
from energy_core.platform.modules.governance.types import GovernanceErrorCode, PublisherStatus, PublisherTier


@pytest.mark.asyncio
async def test_create_and_verify_publisher(session: AsyncSession):
    repo = PublisherRepository(session)
    row = await repo.create(publisher_id="acme", display_name="ACME Corp")
    assert row.status == PublisherStatus.PENDING_VERIFICATION.value
    verified = await repo.verify_publisher("acme", verified_by="admin")
    assert verified.status == PublisherStatus.ACTIVE.value
    assert verified.verified_at is not None


@pytest.mark.asyncio
async def test_invalid_transition_revoked_to_active(session: AsyncSession):
    repo = PublisherRepository(session)
    await repo.create(publisher_id="bad", display_name="Bad")
    await repo.transition_status("bad", PublisherStatus.ACTIVE.value)
    await repo.transition_status("bad", PublisherStatus.REVOKED.value)
    with pytest.raises(PublisherGovernanceError) as exc:
        await repo.transition_status("bad", PublisherStatus.ACTIVE.value)
    assert exc.value.code == GovernanceErrorCode.INVALID_TRANSITION


@pytest.mark.asyncio
async def test_suspend_and_reactivate(session: AsyncSession):
    repo = PublisherRepository(session)
    await repo.create(publisher_id="temp", display_name="Temp")
    await repo.transition_status("temp", PublisherStatus.ACTIVE.value)
    suspended = await repo.transition_status("temp", PublisherStatus.SUSPENDED.value)
    assert suspended.status == PublisherStatus.SUSPENDED.value
    reactivated = await repo.transition_status("temp", PublisherStatus.ACTIVE.value)
    assert reactivated.status == PublisherStatus.ACTIVE.value


@pytest.mark.asyncio
async def test_revoke_sets_revoked_tier(session: AsyncSession):
    repo = PublisherRepository(session)
    await repo.create(publisher_id="gone", display_name="Gone", tier=PublisherTier.VERIFIED.value)
    await repo.transition_status("gone", PublisherStatus.ACTIVE.value)
    revoked = await repo.transition_status("gone", PublisherStatus.REVOKED.value)
    assert revoked.tier == PublisherTier.REVOKED.value
