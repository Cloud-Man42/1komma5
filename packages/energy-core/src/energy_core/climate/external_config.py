"""External module site configuration service."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models.climate_device_reading import ExternalModuleSiteConfigModel
from energy_core.secrets import CredentialCipher


class ExternalModuleConfigService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._cipher = CredentialCipher()

    async def get(self, *, site_id: int, module_id: str) -> ExternalModuleSiteConfigModel | None:
        return await self._session.scalar(
            select(ExternalModuleSiteConfigModel).where(
                ExternalModuleSiteConfigModel.site_id == site_id,
                ExternalModuleSiteConfigModel.module_id == module_id,
            )
        )

    async def upsert(
        self,
        *,
        site_id: int,
        module_id: str,
        credential_ref: str = "api_key",
        api_key: str | None = None,
        poll_interval_seconds: int = 300,
        selected_device_ids: list[str] | None = None,
    ) -> ExternalModuleSiteConfigModel:
        row = await self.get(site_id=site_id, module_id=module_id)
        encrypted = self._cipher.encrypt(api_key) if api_key else None
        devices_json = json.dumps(selected_device_ids or [])
        if row is None:
            row = ExternalModuleSiteConfigModel(
                site_id=site_id,
                module_id=module_id,
                credential_ref=credential_ref,
                credential_encrypted=encrypted,
                poll_interval_seconds=max(60, min(poll_interval_seconds, 3600)),
                selected_device_ids_json=devices_json,
            )
            self._session.add(row)
        else:
            row.credential_ref = credential_ref
            if encrypted is not None:
                row.credential_encrypted = encrypted
            row.poll_interval_seconds = max(60, min(poll_interval_seconds, 3600))
            if selected_device_ids is not None:
                row.selected_device_ids_json = devices_json
        await self._session.flush()
        return row

    async def credential_configured(self, *, site_id: int, module_id: str) -> bool:
        row = await self.get(site_id=site_id, module_id=module_id)
        return bool(row and row.credential_encrypted)
