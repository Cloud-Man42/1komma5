"""Publisher verification records repository."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models.module_publisher_verification import ModulePublisherVerificationModel
from energy_core.platform.modules.governance.types import VerificationStatus


class VerificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_publisher(self, publisher_id: str) -> list[ModulePublisherVerificationModel]:
        return list(
            await self._session.scalars(
                select(ModulePublisherVerificationModel)
                .where(ModulePublisherVerificationModel.publisher_id == publisher_id)
                .order_by(ModulePublisherVerificationModel.created_at.desc())
            )
        )

    async def create_manual(
        self,
        *,
        publisher_id: str,
        verified_by: str,
        verified_domain: str | None = None,
        verified_organization: str | None = None,
        expires_at: datetime | None = None,
        notes: str | None = None,
    ) -> ModulePublisherVerificationModel:
        row = ModulePublisherVerificationModel(
            publisher_id=publisher_id,
            verification_type="manual",
            verified_domain=verified_domain,
            verified_organization=verified_organization,
            status=VerificationStatus.APPROVED.value,
            verified_by=verified_by,
            verified_at=datetime.now(UTC),
            expires_at=expires_at,
            notes=notes,
        )
        self._session.add(row)
        await self._session.flush()
        return row
