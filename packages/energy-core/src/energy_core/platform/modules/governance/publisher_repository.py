"""Publisher governance repository."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models.module_publisher import ModulePublisherModel
from energy_core.platform.modules.governance.types import (
    GovernanceErrorCode,
    PublisherSnapshot,
    PublisherStatus,
    PublisherTier,
)


class PublisherGovernanceError(Exception):
    def __init__(self, message: str, *, code: GovernanceErrorCode) -> None:
        super().__init__(message)
        self.code = code


ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    PublisherStatus.PENDING_VERIFICATION.value: {PublisherStatus.ACTIVE.value, PublisherStatus.REVOKED.value},
    PublisherStatus.ACTIVE.value: {PublisherStatus.SUSPENDED.value, PublisherStatus.REVOKED.value},
    PublisherStatus.SUSPENDED.value: {PublisherStatus.ACTIVE.value, PublisherStatus.REVOKED.value},
    PublisherStatus.REVOKED.value: set(),
}


class PublisherRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_publishers(self) -> list[ModulePublisherModel]:
        return list(await self._session.scalars(select(ModulePublisherModel).order_by(ModulePublisherModel.publisher_id)))

    async def get(self, publisher_id: str) -> ModulePublisherModel | None:
        return await self._session.get(ModulePublisherModel, publisher_id)

    async def get_or_raise(self, publisher_id: str) -> ModulePublisherModel:
        row = await self.get(publisher_id)
        if row is None:
            raise PublisherGovernanceError(
                f"Publisher not found: {publisher_id}",
                code=GovernanceErrorCode.PUBLISHER_NOT_FOUND,
            )
        return row

    async def create(
        self,
        *,
        publisher_id: str,
        display_name: str,
        tier: str = PublisherTier.ORG_APPROVED.value,
        organization: str | None = None,
        verified_domain: str | None = None,
        legal_name: str | None = None,
    ) -> ModulePublisherModel:
        existing = await self.get(publisher_id)
        if existing is not None:
            raise PublisherGovernanceError(
                f"Publisher already exists: {publisher_id}",
                code=GovernanceErrorCode.INVALID_TRUST_TIER,
            )
        row = ModulePublisherModel(
            publisher_id=publisher_id,
            display_name=display_name,
            legal_name=legal_name,
            organization=organization,
            verified_domain=verified_domain,
            tier=tier,
            status=PublisherStatus.PENDING_VERIFICATION.value,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def update_fields(
        self,
        publisher_id: str,
        *,
        display_name: str | None = None,
        organization: str | None = None,
        verified_domain: str | None = None,
        legal_name: str | None = None,
        tier: str | None = None,
    ) -> ModulePublisherModel:
        row = await self.get_or_raise(publisher_id)
        if tier is not None:
            if tier not in {item.value for item in PublisherTier}:
                raise PublisherGovernanceError("Invalid tier", code=GovernanceErrorCode.INVALID_TRUST_TIER)
            row.tier = tier
        if display_name is not None:
            row.display_name = display_name
        if organization is not None:
            row.organization = organization
        if verified_domain is not None:
            row.verified_domain = verified_domain
        if legal_name is not None:
            row.legal_name = legal_name
        await self._session.flush()
        return row

    async def transition_status(self, publisher_id: str, new_status: str) -> ModulePublisherModel:
        row = await self.get_or_raise(publisher_id)
        if new_status not in {item.value for item in PublisherStatus}:
            raise PublisherGovernanceError("Invalid status", code=GovernanceErrorCode.INVALID_TRANSITION)
        allowed = ALLOWED_TRANSITIONS.get(row.status, set())
        if new_status not in allowed and row.status != new_status:
            raise PublisherGovernanceError(
                f"Invalid transition {row.status} -> {new_status}",
                code=GovernanceErrorCode.INVALID_TRANSITION,
            )
        now = datetime.now(UTC)
        row.status = new_status
        if new_status == PublisherStatus.ACTIVE.value:
            row.suspended_at = None
        elif new_status == PublisherStatus.SUSPENDED.value:
            row.suspended_at = now
        elif new_status == PublisherStatus.REVOKED.value:
            row.revoked_at = now
            row.tier = PublisherTier.REVOKED.value
        await self._session.flush()
        return row

    async def verify_publisher(self, publisher_id: str, *, verified_by: str) -> ModulePublisherModel:
        row = await self.transition_status(publisher_id, PublisherStatus.ACTIVE.value)
        now = datetime.now(UTC)
        row.verified_at = now
        if row.tier == PublisherTier.COMMUNITY.value:
            row.tier = PublisherTier.VERIFIED.value
        await self._session.flush()
        return row

    @staticmethod
    def to_snapshot(row: ModulePublisherModel) -> PublisherSnapshot:
        return PublisherSnapshot(
            publisher_id=row.publisher_id,
            display_name=row.display_name,
            organization=row.organization,
            verified_domain=row.verified_domain,
            tier=row.tier,
            status=row.status,
        )
