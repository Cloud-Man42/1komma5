"""Governance evaluation service."""

from __future__ import annotations

from energy_core.platform.modules.governance.break_glass import get_break_glass_store
from energy_core.platform.modules.governance.ownership_repository import OwnershipRepository
from energy_core.platform.modules.governance.policy_engine import ModuleInstallPolicyEngine
from energy_core.platform.modules.governance.policy_repository import PolicyRepository
from energy_core.platform.modules.governance.publisher_repository import PublisherRepository
from energy_core.platform.modules.governance.revocation_reader import RevocationReader
from energy_core.platform.modules.governance.types import (
    PolicyAction,
    PolicyEvaluationInput,
    PolicyEvaluationResult,
)
from sqlalchemy.ext.asyncio import AsyncSession


class GovernanceEvaluationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._publishers = PublisherRepository(session)
        self._policy = PolicyRepository(session)
        self._revocations = RevocationReader(session)
        self._ownership = OwnershipRepository(session)
        self._engine = ModuleInstallPolicyEngine()

    async def evaluate(
        self,
        *,
        action: PolicyAction,
        module_id: str,
        publisher_id: str,
        permissions: tuple[str, ...] = (),
        provided_capabilities: tuple[str, ...] = (),
        marketplace_enabled: bool = False,
        app_env_production: bool = True,
        break_glass_active: bool | None = None,
    ) -> PolicyEvaluationResult:
        policy_row = await self._policy.get_or_create()
        policy = PolicyRepository.to_snapshot(policy_row)
        if break_glass_active is None:
            break_glass_active = get_break_glass_store().is_active()
        publisher_row = await self._publishers.get(publisher_id)
        publisher = PublisherRepository.to_snapshot(publisher_row) if publisher_row else None
        ownership_row = await self._ownership.get(module_id)
        canonical_owner = ownership_row.publisher_id if ownership_row is not None else None
        revocation = await self._revocations.load_context(enabled=marketplace_enabled)
        request = PolicyEvaluationInput(
            action=action,
            module_id=module_id,
            publisher_id=publisher_id,
            permissions=permissions,
            provided_capabilities=provided_capabilities,
            app_env_production=app_env_production,
            break_glass_active=break_glass_active,
            canonical_owner_publisher_id=canonical_owner,
            marketplace_metadata_enabled=marketplace_enabled,
        )
        return self._engine.evaluate(
            policy=policy,
            publisher=publisher,
            revocation=revocation,
            request=request,
        )
