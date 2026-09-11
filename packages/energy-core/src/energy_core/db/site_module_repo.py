"""Site module configuration persistence."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models.modules import SiteModuleConfigurationModel
from energy_core.secrets import CredentialCipher


def _empty_payload() -> dict:
    return {"public": {}, "_secure": {}}


class SiteModuleRepository:
    def __init__(self, session: AsyncSession, *, credential_cipher: CredentialCipher | None = None) -> None:
        self._session = session
        self._credentials = credential_cipher or CredentialCipher()

    async def get_override(self, site_id: int, module_id: str) -> SiteModuleConfigurationModel | None:
        return await self._session.scalar(
            select(SiteModuleConfigurationModel).where(
                SiteModuleConfigurationModel.site_id == site_id,
                SiteModuleConfigurationModel.module_id == module_id,
            )
        )

    async def list_for_site(self, site_id: int) -> list[SiteModuleConfigurationModel]:
        return list(
            await self._session.scalars(
                select(SiteModuleConfigurationModel).where(SiteModuleConfigurationModel.site_id == site_id)
            )
        )

    async def set_enabled(self, site_id: int, module_id: str, enabled: bool) -> SiteModuleConfigurationModel:
        row = await self.get_override(site_id, module_id)
        if row is None:
            row = SiteModuleConfigurationModel(site_id=site_id, module_id=module_id, enabled_override=enabled)
            self._session.add(row)
        else:
            row.enabled_override = enabled
        await self._session.flush()
        return row

    def _load_payload(self, row: SiteModuleConfigurationModel | None) -> dict:
        if row is None or not row.config_json:
            return _empty_payload()
        try:
            raw = json.loads(row.config_json)
        except json.JSONDecodeError:
            return _empty_payload()
        if isinstance(raw, dict) and "public" in raw:
            secure = raw.get("_secure")
            return {"public": dict(raw.get("public") or {}), "_secure": dict(secure) if isinstance(secure, dict) else {}}
        if isinstance(raw, dict):
            return {"public": raw, "_secure": {}}
        return _empty_payload()

    async def get_public_config(self, site_id: int, module_id: str) -> dict:
        row = await self.get_override(site_id, module_id)
        return dict(self._load_payload(row)["public"])

    async def get_secure_secrets(self, site_id: int, module_id: str) -> dict[str, str]:
        row = await self.get_override(site_id, module_id)
        secure = self._load_payload(row)["_secure"]
        result: dict[str, str] = {}
        for key, encrypted in secure.items():
            if encrypted:
                result[key] = self._credentials.decrypt(str(encrypted))
        return result

    async def set_config(self, site_id: int, module_id: str, config: dict) -> SiteModuleConfigurationModel:
        row = await self.get_override(site_id, module_id)
        payload = self._load_payload(row)
        payload["public"] = dict(config)
        encoded = json.dumps(payload)
        if row is None:
            row = SiteModuleConfigurationModel(site_id=site_id, module_id=module_id, config_json=encoded)
            self._session.add(row)
        else:
            row.config_json = encoded
        await self._session.flush()
        return row

    async def set_secure_secrets(self, site_id: int, module_id: str, secrets: dict[str, str]) -> SiteModuleConfigurationModel:
        row = await self.get_override(site_id, module_id)
        payload = self._load_payload(row)
        payload["_secure"] = {key: self._credentials.encrypt(value) for key, value in secrets.items() if value}
        encoded = json.dumps(payload)
        if row is None:
            row = SiteModuleConfigurationModel(site_id=site_id, module_id=module_id, config_json=encoded)
            self._session.add(row)
        else:
            row.config_json = encoded
        await self._session.flush()
        return row

    async def merge_secure_secrets(self, site_id: int, module_id: str, secrets: dict[str, str]) -> SiteModuleConfigurationModel:
        row = await self.get_override(site_id, module_id)
        payload = self._load_payload(row)
        current = dict(payload["_secure"])
        for key, value in secrets.items():
            if value:
                current[key] = self._credentials.encrypt(str(value))
        payload["_secure"] = current
        encoded = json.dumps(payload)
        if row is None:
            row = SiteModuleConfigurationModel(site_id=site_id, module_id=module_id, config_json=encoded)
            self._session.add(row)
        else:
            row.config_json = encoded
        await self._session.flush()
        return row

    async def clear_secure_secrets(self, site_id: int, module_id: str) -> None:
        row = await self.get_override(site_id, module_id)
        if row is None:
            return
        payload = self._load_payload(row)
        payload["_secure"] = {}
        row.config_json = json.dumps(payload)
        await self._session.flush()
