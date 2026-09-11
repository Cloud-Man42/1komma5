"""Installation policy repository."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models.module_installation_policy import (
    ModuleInstallationPolicyModel,
    ModulePolicyHistoryModel,
)
from energy_core.platform.modules.governance.types import (
    DEFAULT_ALLOWED_TIERS,
    GovernanceErrorCode,
    InstallationPolicySnapshot,
    POLICY_SCOPE_INSTALLATION,
    PublisherTier,
)


class PolicyRepositoryError(Exception):
    def __init__(self, message: str, *, code: GovernanceErrorCode) -> None:
        super().__init__(message)
        self.code = code


def _default_policy_payload() -> dict[str, object]:
    return {
        "allowed_tiers": [tier.value for tier in DEFAULT_ALLOWED_TIERS],
        "publisher_allowlist": [],
        "publisher_denylist": [],
        "module_allowlist": [],
        "module_denylist": [],
        "blocked_permissions": [],
        "control_module_policy": "VERIFIED_OK",
        "break_glass_enabled": False,
        "supply_chain_policy": {},
    }


class PolicyRepository:
    POLICY_SCOPE = POLICY_SCOPE_INSTALLATION

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self) -> ModuleInstallationPolicyModel:
        row = await self._session.scalar(
            select(ModuleInstallationPolicyModel).where(
                ModuleInstallationPolicyModel.policy_scope == self.POLICY_SCOPE
            )
        )
        if row is None:
            defaults = _default_policy_payload()
            row = ModuleInstallationPolicyModel(
                policy_scope=self.POLICY_SCOPE,
                policy_version=1,
                allowed_tiers_json=json.dumps(defaults["allowed_tiers"]),
                publisher_allowlist_json=json.dumps(defaults["publisher_allowlist"]),
                publisher_denylist_json=json.dumps(defaults["publisher_denylist"]),
                module_allowlist_json=json.dumps(defaults["module_allowlist"]),
                module_denylist_json=json.dumps(defaults["module_denylist"]),
                blocked_permissions_json=json.dumps(defaults["blocked_permissions"]),
                control_module_policy=str(defaults["control_module_policy"]),
                break_glass_enabled=bool(defaults["break_glass_enabled"]),
                supply_chain_policy_json=json.dumps(defaults["supply_chain_policy"]),
            )
            self._session.add(row)
            await self._session.flush()
        return row

    async def update(
        self,
        *,
        expected_version: int,
        updated_by: str,
        allowed_tiers: list[str] | None = None,
        publisher_allowlist: list[str] | None = None,
        publisher_denylist: list[str] | None = None,
        module_allowlist: list[str] | None = None,
        module_denylist: list[str] | None = None,
        blocked_permissions: list[str] | None = None,
        control_module_policy: str | None = None,
        break_glass_enabled: bool | None = None,
    ) -> ModuleInstallationPolicyModel:
        row = await self.get_or_create()
        if row.policy_version != expected_version:
            raise PolicyRepositoryError(
                f"Policy version conflict: expected {expected_version}, current {row.policy_version}",
                code=GovernanceErrorCode.POLICY_CONFLICT,
            )
        history = ModulePolicyHistoryModel(
            policy_scope=row.policy_scope,
            policy_version=row.policy_version,
            snapshot_json=json.dumps(
                {
                    "policy_scope": row.policy_scope,
                    "policy_version": row.policy_version,
                    "allowed_tiers": json.loads(row.allowed_tiers_json),
                    "publisher_allowlist": json.loads(row.publisher_allowlist_json),
                    "publisher_denylist": json.loads(row.publisher_denylist_json),
                    "module_allowlist": json.loads(row.module_allowlist_json),
                    "module_denylist": json.loads(row.module_denylist_json),
                    "blocked_permissions": json.loads(row.blocked_permissions_json),
                    "control_module_policy": row.control_module_policy,
                    "break_glass_enabled": row.break_glass_enabled,
                }
            ),
            updated_by=updated_by,
        )
        self._session.add(history)
        if allowed_tiers is not None:
            row.allowed_tiers_json = json.dumps(allowed_tiers)
        if publisher_allowlist is not None:
            row.publisher_allowlist_json = json.dumps(publisher_allowlist)
        if publisher_denylist is not None:
            row.publisher_denylist_json = json.dumps(publisher_denylist)
        if module_allowlist is not None:
            row.module_allowlist_json = json.dumps(module_allowlist)
        if module_denylist is not None:
            row.module_denylist_json = json.dumps(module_denylist)
        if blocked_permissions is not None:
            row.blocked_permissions_json = json.dumps(blocked_permissions)
        if control_module_policy is not None:
            row.control_module_policy = control_module_policy
        if break_glass_enabled is not None:
            row.break_glass_enabled = break_glass_enabled
        row.policy_version += 1
        row.updated_by = updated_by
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        return row

    @staticmethod
    def to_snapshot(row: ModuleInstallationPolicyModel) -> InstallationPolicySnapshot:
        return InstallationPolicySnapshot(
            policy_scope=row.policy_scope,
            policy_version=row.policy_version,
            allowed_tiers=tuple(json.loads(row.allowed_tiers_json)),
            publisher_allowlist=tuple(json.loads(row.publisher_allowlist_json)),
            publisher_denylist=tuple(json.loads(row.publisher_denylist_json)),
            module_allowlist=tuple(json.loads(row.module_allowlist_json)),
            module_denylist=tuple(json.loads(row.module_denylist_json)),
            blocked_permissions=tuple(json.loads(row.blocked_permissions_json)),
            control_module_policy=row.control_module_policy,
            break_glass_enabled=row.break_glass_enabled,
            supply_chain_policy=json.loads(getattr(row, "supply_chain_policy_json", None) or "{}"),
            updated_by=row.updated_by,
            updated_at=row.updated_at,
        )

    async def impact_summary(self) -> dict[str, int]:
        row = await self.get_or_create()
        snapshot = self.to_snapshot(row)
        from energy_core.db.models.module_publisher import ModulePublisherModel
        from energy_core.db.models.module_ownership import ModuleOwnershipModel

        publishers = list(await self._session.scalars(select(ModulePublisherModel)))
        ownership = list(await self._session.scalars(select(ModuleOwnershipModel)))
        affected_publishers = sum(
            1
            for p in publishers
            if p.tier not in snapshot.allowed_tiers
            or p.publisher_id in snapshot.publisher_denylist
        )
        affected_modules = sum(1 for o in ownership if o.module_id in snapshot.module_denylist)
        return {
            "publishers_total": len(publishers),
            "publishers_affected": affected_publishers,
            "modules_total": len(ownership),
            "modules_affected": affected_modules,
        }

    async def list_history(self, *, policy_scope: str = POLICY_SCOPE_INSTALLATION) -> list[ModulePolicyHistoryModel]:
        return list(
            await self._session.scalars(
                select(ModulePolicyHistoryModel)
                .where(ModulePolicyHistoryModel.policy_scope == policy_scope)
                .order_by(ModulePolicyHistoryModel.created_at.desc())
            )
        )
