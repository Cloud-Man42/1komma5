"""Ownership transfer workflow tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.platform.modules.governance.ownership_repository import OwnershipRepository
from energy_core.platform.modules.governance.publisher_repository import PublisherRepository
from energy_core.platform.modules.governance.transfer_repository import TransferRepository, TransferRepositoryError
from energy_core.platform.modules.governance.types import GovernanceErrorCode, PublisherTier, TransferStatus


@pytest.mark.asyncio
async def test_transfer_flow_no_trust_escalation(session: AsyncSession):
    publishers = PublisherRepository(session)
    ownership = OwnershipRepository(session)
    transfers = TransferRepository(session)

    await publishers.create(publisher_id="source", display_name="Source", tier=PublisherTier.OFFICIAL.value)
    await publishers.transition_status("source", "ACTIVE")
    await publishers.create(publisher_id="target", display_name="Target", tier=PublisherTier.ORG_APPROVED.value)
    await publishers.transition_status("target", "ACTIVE")
    await ownership.assign(module_id="custom.widget", publisher_id="source")

    pending = await transfers.request_transfer(
        module_id="custom.widget",
        to_publisher_id="target",
        requested_by="admin",
    )
    assert pending.status == TransferStatus.PENDING.value
    assert pending.from_tier == PublisherTier.OFFICIAL.value
    assert pending.to_tier == PublisherTier.ORG_APPROVED.value

    approved = await transfers.approve(pending.id, approved_by="admin")
    assert approved.status == TransferStatus.APPROVED.value

    completed = await transfers.complete(pending.id)
    assert completed.status == TransferStatus.COMPLETED.value
    row = await ownership.get("custom.widget")
    assert row is not None
    assert row.publisher_id == "target"


@pytest.mark.asyncio
async def test_protected_module_transfer_blocked(session: AsyncSession):
    from energy_core.db.models.module_ownership import ModuleOwnershipModel

    publishers = PublisherRepository(session)
    transfers = TransferRepository(session)

    await publishers.create(publisher_id="emic", display_name="EMIC", tier=PublisherTier.OFFICIAL.value)
    await publishers.transition_status("emic", "ACTIVE")
    await publishers.create(publisher_id="other", display_name="Other")
    await publishers.transition_status("other", "ACTIVE")
    session.add(
        ModuleOwnershipModel(module_id="core.platform", publisher_id="emic", protected=True),
    )
    await session.flush()

    with pytest.raises(TransferRepositoryError) as exc:
        await transfers.request_transfer(
            module_id="core.platform",
            to_publisher_id="other",
            requested_by="admin",
        )
    assert exc.value.code == GovernanceErrorCode.OWNERSHIP_TRANSFER_NOT_ALLOWED


@pytest.mark.asyncio
async def test_transfer_to_revoked_publisher_blocked(session: AsyncSession):
    publishers = PublisherRepository(session)
    ownership = OwnershipRepository(session)
    transfers = TransferRepository(session)

    await publishers.create(publisher_id="owner", display_name="Owner")
    await publishers.transition_status("owner", "ACTIVE")
    await publishers.create(publisher_id="revoked", display_name="Revoked")
    await publishers.transition_status("revoked", "ACTIVE")
    await publishers.transition_status("revoked", "REVOKED")
    await ownership.assign(module_id="mod.a", publisher_id="owner")

    with pytest.raises(TransferRepositoryError) as exc:
        await transfers.request_transfer(module_id="mod.a", to_publisher_id="revoked", requested_by="admin")
    assert exc.value.code == GovernanceErrorCode.PUBLISHER_REVOKED
