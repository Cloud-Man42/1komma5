"""Runtime authorization business logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings
from energy_core.platform.modules.runtime_authorization.repository import RuntimeAuthorizationRepository
from energy_core.platform.modules.runtime_authorization.types import RuntimeAuthorizationRecord


class RuntimeAuthorizationService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings
        self._repo = RuntimeAuthorizationRepository(session)

    async def is_authorized(
        self,
        *,
        module_id: str,
        version: str,
        artifact_sha256: str,
        publisher_id: str,
        site_id: int,
    ) -> bool:
        record = await self._repo.find_valid(
            module_id=module_id,
            version=version,
            artifact_sha256=artifact_sha256,
            publisher_id=publisher_id,
            site_id=site_id,
        )
        return record is not None

    async def grant(
        self,
        *,
        module_id: str,
        version: str,
        artifact_sha256: str,
        publisher_id: str,
        site_id: int,
        approved_by: str,
        expires_at: datetime | None = None,
        reason: str | None = None,
        ttl_days: int = 30,
    ) -> RuntimeAuthorizationRecord:
        if not module_id or not version or not artifact_sha256 or not publisher_id:
            raise ValueError("exact module identity required")
        if "*" in module_id or "*" in publisher_id:
            raise ValueError("wildcards not allowed")
        expiry = expires_at or (datetime.now(UTC) + timedelta(days=ttl_days))
        return await self._repo.create(
            module_id=module_id,
            version=version,
            artifact_sha256=artifact_sha256,
            publisher_id=publisher_id,
            site_id=site_id,
            approved_by=approved_by,
            expires_at=expiry,
            reason=reason,
        )

    async def revoke(self, auth_id: int) -> RuntimeAuthorizationRecord | None:
        return await self._repo.revoke(auth_id)

    async def list_authorizations(self, *, include_revoked: bool = False) -> list[RuntimeAuthorizationRecord]:
        return await self._repo.list_all(include_revoked=include_revoked)

    async def runtime_spawn_allowed(
        self,
        settings: Settings,
        *,
        module_id: str,
        version: str,
        artifact_sha256: str,
        publisher_id: str,
        site_id: int,
    ) -> bool:
        if settings.runtime_spawn_allowed():
            return True
        return await self.is_authorized(
            module_id=module_id,
            version=version,
            artifact_sha256=artifact_sha256,
            publisher_id=publisher_id,
            site_id=site_id,
        )
