"""Provision network/secret brokers from manifest + site config."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings
from energy_core.db.models.modules import SiteModuleConfigurationModel
from energy_core.platform.modules.isolation.rpc.gateway import ModuleRpcGateway
from energy_core.secrets import CredentialCipher

logger = logging.getLogger(__name__)


class RuntimeBrokerProvisioner:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._cipher = CredentialCipher()

    async def provision_for_runtime(
        self,
        *,
        gateway: ModuleRpcGateway,
        module_id: str,
        site_id: int,
        package_path: Path,
    ) -> dict:
        manifest = self._load_manifest(package_path)
        for host in manifest.get("network_hosts") or []:
            if isinstance(host, str) and host.strip():
                gateway.network_broker.allow_host(module_id=module_id, site_id=site_id, host=host.strip())

        config = await self._load_site_config(module_id=module_id, site_id=site_id)
        ext = await self._load_external_config(module_id=module_id, site_id=site_id)
        merged = {**config, **ext}
        credential_ref = merged.get("credential_ref") or "api_key"
        encrypted = merged.get("credential_encrypted")
        if encrypted:
            try:
                value = self._cipher.decrypt(str(encrypted))
                gateway.secret_broker.register_secret(
                    module_id=module_id,
                    site_id=site_id,
                    secret_ref=str(credential_ref),
                    value=value,
                )
            except Exception:
                logger.warning("Failed to provision secret for module=%s site=%s", module_id, site_id)
        return self._sanitize_site_config(merged, credential_ref=str(credential_ref))

    @staticmethod
    def _load_manifest(package_path: Path) -> dict:
        manifest_path = package_path / "manifest.json"
        if not manifest_path.exists():
            return {}
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    @staticmethod
    def _sanitize_site_config(config: dict, *, credential_ref: str) -> dict:
        safe: dict = {
            "credential_ref": credential_ref,
            "poll_interval_seconds": int(config.get("poll_interval_seconds") or 300),
        }
        devices = config.get("selected_device_ids") or config.get("selected_devices")
        if isinstance(devices, list):
            safe["selected_device_ids"] = [str(d) for d in devices]
        return safe

    async def _load_external_config(self, *, module_id: str, site_id: int) -> dict:
        from energy_core.db.models.climate_device_reading import ExternalModuleSiteConfigModel

        row = await self._session.scalar(
            select(ExternalModuleSiteConfigModel).where(
                ExternalModuleSiteConfigModel.site_id == site_id,
                ExternalModuleSiteConfigModel.module_id == module_id,
            )
        )
        if row is None:
            return {}
        devices: list[str] = []
        if row.selected_device_ids_json:
            try:
                parsed = json.loads(row.selected_device_ids_json)
                if isinstance(parsed, list):
                    devices = [str(d) for d in parsed]
            except json.JSONDecodeError:
                pass
        return {
            "credential_ref": row.credential_ref,
            "credential_encrypted": row.credential_encrypted,
            "poll_interval_seconds": row.poll_interval_seconds,
            "selected_device_ids": devices,
        }

    async def _load_site_config(self, *, module_id: str, site_id: int) -> dict:
        row = await self._session.scalar(
            select(SiteModuleConfigurationModel).where(
                SiteModuleConfigurationModel.site_id == site_id,
                SiteModuleConfigurationModel.module_id == module_id,
            )
        )
        if row is None or not row.config_json:
            return {}
        try:
            parsed = json.loads(row.config_json)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
