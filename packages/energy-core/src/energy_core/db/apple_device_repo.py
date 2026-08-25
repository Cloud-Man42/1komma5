"""Apple device registration repository."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from energy_core.auth.device_tokens import GeneratedDeviceToken
from energy_core.db.models import AppleDeviceModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class AppleDeviceRecord:
    id: int
    owner_label: str
    device_name: str
    device_type: str
    token_prefix: str
    scopes: str
    default_site_slug: str | None
    created_at: datetime
    last_seen_at: datetime | None
    revoked_at: datetime | None

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None


class AppleDeviceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        owner_label: str,
        device_name: str,
        device_type: str,
        generated: GeneratedDeviceToken,
        scopes: str = "widget.read",
        default_site_slug: str | None = None,
    ) -> tuple[AppleDeviceRecord, str]:
        row = AppleDeviceModel(
            owner_label=owner_label,
            device_name=device_name,
            device_type=device_type,
            token_prefix=generated.token_prefix,
            token_hash=generated.token_hash,
            scopes=scopes,
            default_site_slug=default_site_slug,
        )
        self._session.add(row)
        await self._session.flush()
        return self._to_record(row), generated.token

    async def list_all(self) -> list[AppleDeviceRecord]:
        rows = await self._session.scalars(
            select(AppleDeviceModel).order_by(AppleDeviceModel.created_at.desc())
        )
        return [self._to_record(row) for row in rows]

    async def get_by_id(self, device_id: int) -> AppleDeviceRecord | None:
        row = await self._session.get(AppleDeviceModel, device_id)
        return self._to_record(row) if row else None

    async def get_by_prefix(self, token_prefix: str) -> AppleDeviceModel | None:
        return await self._session.scalar(
            select(AppleDeviceModel).where(AppleDeviceModel.token_prefix == token_prefix)
        )

    async def touch_last_seen(self, device_id: int) -> None:
        row = await self._session.get(AppleDeviceModel, device_id)
        if row is None:
            return
        row.last_seen_at = datetime.now(UTC)
        await self._session.flush()

    async def revoke(self, device_id: int) -> AppleDeviceRecord | None:
        row = await self._session.get(AppleDeviceModel, device_id)
        if row is None:
            return None
        row.revoked_at = datetime.now(UTC)
        await self._session.flush()
        return self._to_record(row)

    async def rename(self, device_id: int, *, device_name: str) -> AppleDeviceRecord | None:
        row = await self._session.get(AppleDeviceModel, device_id)
        if row is None:
            return None
        row.device_name = device_name
        await self._session.flush()
        return self._to_record(row)

    async def count_active(self) -> int:
        rows = await self._session.scalars(
            select(AppleDeviceModel).where(AppleDeviceModel.revoked_at.is_(None))
        )
        return len(list(rows))

    @staticmethod
    def _to_record(row: AppleDeviceModel) -> AppleDeviceRecord:
        return AppleDeviceRecord(
            id=row.id,
            owner_label=row.owner_label,
            device_name=row.device_name,
            device_type=row.device_type,
            token_prefix=row.token_prefix,
            scopes=row.scopes,
            default_site_slug=row.default_site_slug,
            created_at=row.created_at,
            last_seen_at=row.last_seen_at,
            revoked_at=row.revoked_at,
        )
