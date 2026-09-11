"""Publisher public key trust store."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.platform.modules.packages.errors import SIGNATURE_INVALID, PackageError

PUBLISHER_UNKNOWN = "PUBLISHER_UNKNOWN"
PUBLISHER_REVOKED = "PUBLISHER_REVOKED"


class PublisherKeyStatus(StrEnum):
    TRUSTED = "trusted"
    REVOKED = "revoked"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class PublisherKeyRecord:
    publisher_id: str
    key_id: str
    public_key: bytes
    status: PublisherKeyStatus


class PublisherTrustStore:
    def __init__(self, session: AsyncSession | None = None, *, config_path: str | None = None) -> None:
        self._session = session
        self._config_path = config_path
        self._memory: dict[tuple[str, str], PublisherKeyRecord] = {}

    def register_memory_key(self, record: PublisherKeyRecord) -> None:
        self._memory[(record.publisher_id, record.key_id)] = record

    async def load_config_keys(self, path: str | None = None) -> None:
        resolved = path or self._config_path
        if not resolved:
            return
        raw = json.loads(Path(resolved).read_text(encoding="utf-8"))
        for item in raw.get("publishers", []):
            public_key = bytes.fromhex(str(item["public_key_hex"]))
            self.register_memory_key(
                PublisherKeyRecord(
                    publisher_id=str(item["publisher_id"]),
                    key_id=str(item["key_id"]),
                    public_key=public_key,
                    status=PublisherKeyStatus(str(item.get("status", "trusted"))),
                )
            )

    async def get_public_key(self, publisher_id: str, key_id: str) -> PublisherKeyRecord:
        cached = self._memory.get((publisher_id, key_id))
        if cached is not None:
            return cached
        if self._session is not None:
            from energy_core.db.models.module_publisher_key import ModulePublisherKeyModel

            row = await self._session.scalar(
                select(ModulePublisherKeyModel).where(
                    ModulePublisherKeyModel.publisher_id == publisher_id,
                    ModulePublisherKeyModel.key_id == key_id,
                )
            )
            if row is not None:
                record = PublisherKeyRecord(
                    publisher_id=row.publisher_id,
                    key_id=row.key_id,
                    public_key=bytes.fromhex(row.public_key_hex),
                    status=PublisherKeyStatus(row.status),
                )
                self._memory[(publisher_id, key_id)] = record
                return record
        raise PackageError(f"unknown publisher key {publisher_id}/{key_id}", code=PUBLISHER_UNKNOWN)

    async def assert_trusted(self, publisher_id: str, key_id: str) -> bytes:
        record = await self.get_public_key(publisher_id, key_id)
        if record.status == PublisherKeyStatus.REVOKED:
            raise PackageError(f"revoked publisher key {publisher_id}/{key_id}", code=PUBLISHER_REVOKED)
        if record.status == PublisherKeyStatus.DISABLED:
            raise PackageError(f"disabled publisher key {publisher_id}/{key_id}", code=PUBLISHER_UNKNOWN)
        return record.public_key
