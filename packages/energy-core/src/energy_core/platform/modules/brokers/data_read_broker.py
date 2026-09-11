"""Scoped data read broker."""

from __future__ import annotations

from energy_core.config import Settings


class DataReadBroker:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._data: dict[tuple[int, str, str], dict] = {}

    def seed(self, *, site_id: int, capability: str, payload: dict) -> None:
        self._data[(site_id, capability, capability)] = payload

    async def read(
        self,
        *,
        runtime_instance_id: str,
        module_id: str,
        site_id: int,
        capability: str,
        params: dict,
        permissions: tuple[str, ...],
        capabilities: tuple[str, ...] = (),
    ) -> dict:
        requested_site = int(params.get("site_id", site_id))
        if requested_site != site_id:
            raise PermissionError("cross-site read denied")
        if capability in capabilities:
            pass
        elif capability.endswith(".read") or capability.startswith("device.read"):
            pass
        elif capability not in permissions:
            raise PermissionError(f"capability denied: {capability}")
        payload = self._data.get((site_id, capability, capability), {"value": None})
        return {"data": payload}
