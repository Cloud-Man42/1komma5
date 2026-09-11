"""Organization policy repository tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.platform.modules.governance.policy_repository import PolicyRepository, PolicyRepositoryError
from energy_core.platform.modules.governance.types import GovernanceErrorCode


@pytest.mark.asyncio
async def test_default_policy_created(session: AsyncSession):
    repo = PolicyRepository(session)
    row = await repo.get_or_create()
    snapshot = PolicyRepository.to_snapshot(row)
    assert snapshot.policy_version >= 1
    assert "OFFICIAL" in snapshot.allowed_tiers
    assert "COMMUNITY" not in snapshot.allowed_tiers


@pytest.mark.asyncio
async def test_policy_version_conflict(session: AsyncSession):
    repo = PolicyRepository(session)
    row = await repo.get_or_create()
    original_version = row.policy_version
    await repo.update(expected_version=original_version, updated_by="admin", allowed_tiers=["OFFICIAL"])
    with pytest.raises(PolicyRepositoryError) as exc:
        await repo.update(expected_version=original_version, updated_by="admin", allowed_tiers=["VERIFIED"])
    assert exc.value.code == GovernanceErrorCode.POLICY_CONFLICT


@pytest.mark.asyncio
async def test_denylist_blocks_evaluation_via_engine(session: AsyncSession):
    from energy_core.platform.modules.governance.evaluation_service import GovernanceEvaluationService
    from energy_core.platform.modules.governance.publisher_repository import PublisherRepository
    from energy_core.platform.modules.governance.types import PolicyAction, PolicyDecision

    pub = PublisherRepository(session)
    policy = PolicyRepository(session)
    await pub.create(publisher_id="blocked-pub", display_name="Blocked")
    await pub.transition_status("blocked-pub", "ACTIVE")
    row = await policy.get_or_create()
    await policy.update(
        expected_version=row.policy_version,
        updated_by="admin",
        publisher_denylist=["blocked-pub"],
    )

    result = await GovernanceEvaluationService(session).evaluate(
        action=PolicyAction.INSTALL,
        module_id="demo.mod",
        publisher_id="blocked-pub",
        app_env_production=True,
    )
    assert result.decision == PolicyDecision.DENY
