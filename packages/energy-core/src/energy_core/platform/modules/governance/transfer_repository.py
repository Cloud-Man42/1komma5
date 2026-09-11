"""Ownership transfer workflow repository."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models.module_ownership_transfer import ModuleOwnershipTransferModel
from energy_core.platform.modules.governance.ownership_repository import OwnershipRepository
from energy_core.platform.modules.governance.publisher_repository import PublisherRepository
from energy_core.platform.modules.governance.types import (
    GovernanceErrorCode,
    PublisherStatus,
    PublisherTier,
    TransferStatus,
)
from energy_core.platform.modules.packages.paths import is_protected_module_id


class TransferRepositoryError(Exception):
    def __init__(self, message: str, *, code: GovernanceErrorCode) -> None:
        super().__init__(message)
        self.code = code


class TransferRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._publishers = PublisherRepository(session)
        self._ownership = OwnershipRepository(session)

    async def request_transfer(
        self,
        *,
        module_id: str,
        to_publisher_id: str,
        requested_by: str,
        reason: str | None = None,
    ) -> ModuleOwnershipTransferModel:
        if is_protected_module_id(module_id):
            raise TransferRepositoryError(
                "Official/protected module cannot be transferred",
                code=GovernanceErrorCode.OWNERSHIP_TRANSFER_NOT_ALLOWED,
            )
        ownership = await self._ownership.get(module_id)
        if ownership is None:
            raise TransferRepositoryError(
                f"No ownership record for module {module_id}",
                code=GovernanceErrorCode.OWNERSHIP_TRANSFER_NOT_ALLOWED,
            )
        from_publisher = await self._publishers.get_or_raise(ownership.publisher_id)
        to_publisher = await self._publishers.get_or_raise(to_publisher_id)
        if to_publisher.status == PublisherStatus.REVOKED.value or to_publisher.tier == PublisherTier.REVOKED.value:
            raise TransferRepositoryError(
                "Target publisher is revoked",
                code=GovernanceErrorCode.PUBLISHER_REVOKED,
            )
        pending = await self._session.scalar(
            select(ModuleOwnershipTransferModel).where(
                ModuleOwnershipTransferModel.module_id == module_id,
                ModuleOwnershipTransferModel.status == TransferStatus.PENDING.value,
            )
        )
        if pending is not None:
            raise TransferRepositoryError(
                "Pending transfer already exists",
                code=GovernanceErrorCode.OWNERSHIP_TRANSFER_NOT_ALLOWED,
            )
        row = ModuleOwnershipTransferModel(
            module_id=module_id,
            from_publisher_id=from_publisher.publisher_id,
            to_publisher_id=to_publisher.publisher_id,
            from_tier=from_publisher.tier,
            to_tier=to_publisher.tier,
            requested_by=requested_by,
            status=TransferStatus.PENDING.value,
            reason=reason,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def approve(self, transfer_id: int, *, approved_by: str) -> ModuleOwnershipTransferModel:
        row = await self._get_or_raise(transfer_id)
        if row.status != TransferStatus.PENDING.value:
            raise TransferRepositoryError("Transfer is not pending", code=GovernanceErrorCode.INVALID_TRANSITION)
        row.status = TransferStatus.APPROVED.value
        row.approved_by = approved_by
        row.approved_at = datetime.now(UTC)
        await self._session.flush()
        return row

    async def reject(self, transfer_id: int, *, approved_by: str) -> ModuleOwnershipTransferModel:
        row = await self._get_or_raise(transfer_id)
        if row.status != TransferStatus.PENDING.value:
            raise TransferRepositoryError("Transfer is not pending", code=GovernanceErrorCode.INVALID_TRANSITION)
        row.status = TransferStatus.REJECTED.value
        row.approved_by = approved_by
        row.approved_at = datetime.now(UTC)
        await self._session.flush()
        return row

    async def complete(self, transfer_id: int) -> ModuleOwnershipTransferModel:
        row = await self._get_or_raise(transfer_id)
        if row.status != TransferStatus.APPROVED.value:
            raise TransferRepositoryError("Transfer is not approved", code=GovernanceErrorCode.INVALID_TRANSITION)
        await self._ownership.transfer_ownership(module_id=row.module_id, to_publisher_id=row.to_publisher_id)
        row.status = TransferStatus.COMPLETED.value
        row.effective_at = datetime.now(UTC)
        await self._session.flush()
        return row

    async def get(self, transfer_id: int) -> ModuleOwnershipTransferModel | None:
        return await self._session.get(ModuleOwnershipTransferModel, transfer_id)

    async def _get_or_raise(self, transfer_id: int) -> ModuleOwnershipTransferModel:
        row = await self.get(transfer_id)
        if row is None:
            raise TransferRepositoryError(
                f"Transfer not found: {transfer_id}",
                code=GovernanceErrorCode.TRANSFER_NOT_FOUND,
            )
        return row
