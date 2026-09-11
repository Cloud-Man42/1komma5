"""Installed module package persistence."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models.installed_module_package import InstalledModulePackageModel
from energy_core.platform.modules.packages.types import (
    InstalledPackageRecord,
    PackageState,
    SignatureStatus,
)


def _to_record(row: InstalledModulePackageModel) -> InstalledPackageRecord:
    metadata: dict[str, Any] = {}
    if row.metadata_json:
        try:
            parsed = json.loads(row.metadata_json)
            if isinstance(parsed, dict):
                metadata = parsed
        except json.JSONDecodeError:
            metadata = {}
    return InstalledPackageRecord(
        module_id=row.module_id,
        installed_version=row.installed_version,
        package_state=PackageState(row.package_state),
        package_path=row.package_path,
        staging_path=row.staging_path,
        publisher=row.publisher,
        source=row.source,
        checksum_sha256=row.checksum_sha256,
        signature_status=SignatureStatus(row.signature_status),
        rollback_version=row.rollback_version,
        previous_package_path=row.previous_package_path,
        module_api_version=row.module_api_version,
        restart_required=row.restart_required,
        metadata=metadata,
    )


class InstalledPackageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, module_id: str) -> InstalledPackageRecord | None:
        row = await self._session.get(InstalledModulePackageModel, module_id)
        return _to_record(row) if row else None

    async def list_all(self) -> list[InstalledPackageRecord]:
        rows = await self._session.scalars(select(InstalledModulePackageModel))
        return [_to_record(row) for row in rows]

    async def upsert(self, record: InstalledPackageRecord) -> InstalledPackageRecord:
        row = await self._session.get(InstalledModulePackageModel, record.module_id)
        metadata_json = json.dumps(record.metadata) if record.metadata else None
        if row is None:
            row = InstalledModulePackageModel(
                module_id=record.module_id,
                installed_version=record.installed_version,
                package_state=record.package_state.value,
                package_path=record.package_path,
                staging_path=record.staging_path,
                publisher=record.publisher,
                source=record.source,
                checksum_sha256=record.checksum_sha256,
                signature_status=record.signature_status.value,
                rollback_version=record.rollback_version,
                previous_package_path=record.previous_package_path,
                module_api_version=record.module_api_version,
                restart_required=record.restart_required,
                metadata_json=metadata_json,
            )
            self._session.add(row)
        else:
            row.installed_version = record.installed_version
            row.package_state = record.package_state.value
            row.package_path = record.package_path
            row.staging_path = record.staging_path
            row.publisher = record.publisher
            row.source = record.source
            row.checksum_sha256 = record.checksum_sha256
            row.signature_status = record.signature_status.value
            row.rollback_version = record.rollback_version
            row.previous_package_path = record.previous_package_path
            row.module_api_version = record.module_api_version
            row.restart_required = record.restart_required
            row.metadata_json = metadata_json
        await self._session.flush()
        return _to_record(row)

    async def delete(self, module_id: str) -> bool:
        row = await self._session.get(InstalledModulePackageModel, module_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.flush()
        return True
