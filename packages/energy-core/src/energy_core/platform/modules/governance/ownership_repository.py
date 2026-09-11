"""Module ownership repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models.module_ownership import ModuleOwnershipModel
from energy_core.platform.modules.governance.types import GovernanceErrorCode
from energy_core.platform.modules.packages.paths import is_protected_module_id


class OwnershipRepositoryError(Exception):
    def __init__(self, message: str, *, code: GovernanceErrorCode) -> None:
        super().__init__(message)
        self.code = code


class OwnershipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, module_id: str) -> ModuleOwnershipModel | None:
        return await self._session.get(ModuleOwnershipModel, module_id)

    async def list_for_publisher(self, publisher_id: str) -> list[ModuleOwnershipModel]:
        return list(
            await self._session.scalars(
                select(ModuleOwnershipModel).where(ModuleOwnershipModel.publisher_id == publisher_id)
            )
        )

    async def list_all(self) -> list[ModuleOwnershipModel]:
        return list(await self._session.scalars(select(ModuleOwnershipModel).order_by(ModuleOwnershipModel.module_id)))

    async def assign(
        self,
        *,
        module_id: str,
        publisher_id: str,
        protected: bool | None = None,
    ) -> ModuleOwnershipModel:
        if is_protected_module_id(module_id):
            raise OwnershipRepositoryError(
                f"Protected module cannot be assigned: {module_id}",
                code=GovernanceErrorCode.OWNERSHIP_TRANSFER_NOT_ALLOWED,
            )
        row = await self.get(module_id)
        if row is None:
            row = ModuleOwnershipModel(
                module_id=module_id,
                publisher_id=publisher_id,
                protected=protected or False,
            )
            self._session.add(row)
        else:
            row.publisher_id = publisher_id
            if protected is not None:
                row.protected = protected
        await self._session.flush()
        return row

    async def transfer_ownership(self, *, module_id: str, to_publisher_id: str) -> ModuleOwnershipModel:
        row = await self.get(module_id)
        if row is None:
            raise OwnershipRepositoryError(
                f"Ownership not found for module: {module_id}",
                code=GovernanceErrorCode.OWNERSHIP_TRANSFER_NOT_ALLOWED,
            )
        if row.protected or is_protected_module_id(module_id):
            raise OwnershipRepositoryError(
                f"Protected module ownership cannot be transferred: {module_id}",
                code=GovernanceErrorCode.OWNERSHIP_TRANSFER_NOT_ALLOWED,
            )
        row.publisher_id = to_publisher_id
        await self._session.flush()
        return row
