"""Ownership enforcement in policy evaluation (M1)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.platform.modules.governance.evaluation_service import GovernanceEvaluationService
from energy_core.platform.modules.governance.ownership_repository import OwnershipRepository
from energy_core.platform.modules.governance.policy_engine import ModuleInstallPolicyEngine
from energy_core.platform.modules.governance.publisher_repository import PublisherRepository
from energy_core.platform.modules.governance.transfer_repository import TransferRepository
from energy_core.platform.modules.governance.types import (
    InstallationPolicySnapshot,
    PolicyAction,
    PolicyDecision,
    PolicyEvaluationInput,
    PolicyReasonCode,
    PublisherSnapshot,
    PublisherStatus,
    PublisherTier,
)


def _policy() -> InstallationPolicySnapshot:
    return InstallationPolicySnapshot(
        policy_scope="installation",
        policy_version=1,
        allowed_tiers=("OFFICIAL", "VERIFIED", "ORG_APPROVED"),
        publisher_allowlist=(),
        publisher_denylist=(),
        module_allowlist=(),
        module_denylist=(),
        blocked_permissions=(),
        control_module_policy="VERIFIED_OK",
        break_glass_enabled=False,
    )


def _publisher(**kw) -> PublisherSnapshot:
    base = {
        "publisher_id": "owner-a",
        "display_name": "Owner A",
        "organization": None,
        "verified_domain": None,
        "tier": PublisherTier.ORG_APPROVED.value,
        "status": PublisherStatus.ACTIVE.value,
    }
    base.update(kw)
    return PublisherSnapshot(**base)


def test_matching_owner_allows_normal_evaluation():
    engine = ModuleInstallPolicyEngine()
    result = engine.evaluate(
        policy=_policy(),
        publisher=_publisher(),
        revocation=None,
        request=PolicyEvaluationInput(
            action=PolicyAction.INSTALL,
            module_id="mod.widget",
            publisher_id="owner-a",
            canonical_owner_publisher_id="owner-a",
            app_env_production=True,
        ),
    )
    assert result.decision == PolicyDecision.ALLOW


def test_mismatch_denies_with_reason():
    engine = ModuleInstallPolicyEngine()
    result = engine.evaluate(
        policy=_policy(),
        publisher=_publisher(publisher_id="owner-b", tier=PublisherTier.OFFICIAL.value),
        revocation=None,
        request=PolicyEvaluationInput(
            action=PolicyAction.INSTALL,
            module_id="mod.widget",
            publisher_id="owner-b",
            canonical_owner_publisher_id="owner-a",
            app_env_production=True,
        ),
    )
    assert result.decision == PolicyDecision.DENY
    assert PolicyReasonCode.OWNERSHIP_MISMATCH.value in result.reason_codes


def test_no_canonical_owner_uses_manifest_publisher():
    engine = ModuleInstallPolicyEngine()
    result = engine.evaluate(
        policy=_policy(),
        publisher=_publisher(publisher_id="manifest-only"),
        revocation=None,
        request=PolicyEvaluationInput(
            action=PolicyAction.INSTALL,
            module_id="mod.new",
            publisher_id="manifest-only",
            canonical_owner_publisher_id=None,
            app_env_production=True,
        ),
    )
    assert result.decision == PolicyDecision.ALLOW


@pytest.mark.asyncio
async def test_transfer_changes_canonical_owner(session: AsyncSession):
    publishers = PublisherRepository(session)
    ownership = OwnershipRepository(session)
    transfers = TransferRepository(session)
    service = GovernanceEvaluationService(session)

    await publishers.create(publisher_id="owner-a", display_name="A", tier=PublisherTier.ORG_APPROVED.value)
    await publishers.transition_status("owner-a", "ACTIVE")
    await publishers.create(publisher_id="owner-b", display_name="B", tier=PublisherTier.ORG_APPROVED.value)
    await publishers.transition_status("owner-b", "ACTIVE")
    await ownership.assign(module_id="transfer.mod", publisher_id="owner-a")

    before = await service.evaluate(
        action=PolicyAction.INSTALL,
        module_id="transfer.mod",
        publisher_id="owner-a",
        app_env_production=True,
    )
    assert before.decision == PolicyDecision.ALLOW

    old_owner = await service.evaluate(
        action=PolicyAction.INSTALL,
        module_id="transfer.mod",
        publisher_id="owner-a",
        app_env_production=True,
    )
    assert old_owner.decision == PolicyDecision.ALLOW

    pending = await transfers.request_transfer(
        module_id="transfer.mod",
        to_publisher_id="owner-b",
        requested_by="admin",
    )
    await transfers.approve(pending.id, approved_by="admin")
    await transfers.complete(pending.id)

    mismatch = await service.evaluate(
        action=PolicyAction.INSTALL,
        module_id="transfer.mod",
        publisher_id="owner-a",
        app_env_production=True,
    )
    assert mismatch.decision == PolicyDecision.DENY
    assert PolicyReasonCode.OWNERSHIP_MISMATCH.value in mismatch.reason_codes

    new_owner = await service.evaluate(
        action=PolicyAction.INSTALL,
        module_id="transfer.mod",
        publisher_id="owner-b",
        app_env_production=True,
    )
    assert new_owner.decision == PolicyDecision.ALLOW
