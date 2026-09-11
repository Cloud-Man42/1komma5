"""Quarantine handling for broken package state."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.installed_package_repo import InstalledPackageRepository
from energy_core.platform.modules.packages.types import InstalledPackageRecord, PackageState, SignatureStatus


async def quarantine_package(
    session: AsyncSession,
    record: InstalledPackageRecord,
    *,
    reason: str,
    last_error: str | None = None,
) -> InstalledPackageRecord:
    metadata = dict(record.metadata)
    metadata.update(
        {
            "quarantine_reason": reason,
            "quarantined_at": datetime.now(UTC).isoformat(),
            "last_error": last_error or reason,
            "detected_version": record.installed_version,
        }
    )
    updated = InstalledPackageRecord(
        module_id=record.module_id,
        installed_version=record.installed_version,
        package_state=PackageState.QUARANTINED,
        package_path=record.package_path,
        staging_path=record.staging_path,
        publisher=record.publisher,
        source=record.source,
        checksum_sha256=record.checksum_sha256,
        signature_status=record.signature_status,
        rollback_version=record.rollback_version,
        previous_package_path=record.previous_package_path,
        module_api_version=record.module_api_version,
        restart_required=True,
        metadata=metadata,
    )
    repo = InstalledPackageRepository(session)
    await repo.upsert(updated)
    await session.commit()
    return updated
