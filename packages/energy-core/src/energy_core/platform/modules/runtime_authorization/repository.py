"""Runtime authorization persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models.runtime_pilot_authorization import RuntimePilotAuthorizationModel
from energy_core.platform.modules.runtime_authorization.types import RuntimeAuthorizationRecord


def _to_record(row: RuntimePilotAuthorizationModel) -> RuntimeAuthorizationRecord:
    return RuntimeAuthorizationRecord(
        id=row.id,
        module_id=row.module_id,
        version=row.version,
        artifact_sha256=row.artifact_sha256,
        publisher_id=row.publisher_id,
        site_id=row.site_id,
        approved_by=row.approved_by,
        approved_at=row.approved_at,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        reason=row.reason,
    )


class RuntimeAuthorizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        module_id: str,
        version: str,
        artifact_sha256: str,
        publisher_id: str,
        site_id: int,
        approved_by: str,
        expires_at: datetime,
        reason: str | None = None,
    ) -> RuntimeAuthorizationRecord:
        row = RuntimePilotAuthorizationModel(
            module_id=module_id,
            version=version,
            artifact_sha256=artifact_sha256.lower(),
            publisher_id=publisher_id,
            site_id=site_id,
            approved_by=approved_by,
            expires_at=expires_at,
            reason=reason,
        )
        self._session.add(row)
        await self._session.flush()
        return _to_record(row)

    async def get(self, auth_id: int) -> RuntimeAuthorizationRecord | None:
        row = await self._session.get(RuntimePilotAuthorizationModel, auth_id)
        return _to_record(row) if row else None

    async def list_all(self, *, include_revoked: bool = False) -> list[RuntimeAuthorizationRecord]:
        rows = await self._session.scalars(
            select(RuntimePilotAuthorizationModel).order_by(RuntimePilotAuthorizationModel.id.desc())
        )
        records = [_to_record(r) for r in rows.all()]
        if include_revoked:
            return records
        return [r for r in records if r.revoked_at is None]

    async def find_valid(
        self,
        *,
        module_id: str,
        version: str,
        artifact_sha256: str,
        publisher_id: str,
        site_id: int,
        now: datetime | None = None,
    ) -> RuntimeAuthorizationRecord | None:
        now = now or datetime.now(UTC)
        rows = await self._session.scalars(
            select(RuntimePilotAuthorizationModel).where(
                RuntimePilotAuthorizationModel.module_id == module_id,
                RuntimePilotAuthorizationModel.version == version,
                RuntimePilotAuthorizationModel.artifact_sha256 == artifact_sha256.lower(),
                RuntimePilotAuthorizationModel.publisher_id == publisher_id,
                RuntimePilotAuthorizationModel.site_id == site_id,
                RuntimePilotAuthorizationModel.revoked_at.is_(None),
                RuntimePilotAuthorizationModel.expires_at > now,
            )
        )
        row = rows.first()
        return _to_record(row) if row else None

    async def revoke(self, auth_id: int) -> RuntimeAuthorizationRecord | None:
        row = await self._session.get(RuntimePilotAuthorizationModel, auth_id)
        if row is None:
            return None
        row.revoked_at = datetime.now(UTC)
        await self._session.flush()
        return _to_record(row)
