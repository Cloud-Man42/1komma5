"""Secret broker for isolated modules."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime

from energy_core.config import Settings

logger = logging.getLogger(__name__)


class SecretBroker:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._secrets: dict[tuple[str, int, str], str] = {}
        self._access_counts: dict[str, list[float]] = defaultdict(list)
        self._audit_log: list[dict] = []

    def register_secret(self, *, module_id: str, site_id: int, secret_ref: str, value: str) -> None:
        self._secrets[(module_id, site_id, secret_ref)] = value

    def clear(self) -> None:
        self._secrets.clear()
        self._audit_log.clear()

    async def get_secret(
        self,
        *,
        runtime_instance_id: str,
        module_id: str,
        site_id: int,
        secret_ref: str,
        permissions: tuple[str, ...],
    ) -> str:
        if "secrets.read_own" not in permissions:
            self._audit(runtime_instance_id, module_id, site_id, secret_ref, allowed=False, reason="permission denied")
            raise PermissionError("secrets.read_own required")
        key = (module_id, site_id, secret_ref)
        if key not in self._secrets:
            self._audit(runtime_instance_id, module_id, site_id, secret_ref, allowed=False, reason="not found")
            raise PermissionError("secret not assigned to module/site")
        self._audit(runtime_instance_id, module_id, site_id, secret_ref, allowed=True)
        return self._secrets[key]

    def _audit(
        self,
        runtime_instance_id: str,
        module_id: str,
        site_id: int,
        secret_ref: str,
        *,
        allowed: bool,
        reason: str = "",
    ) -> None:
        self._audit_log.append(
            {
                "runtime_instance_id": runtime_instance_id,
                "module_id": module_id,
                "site_id": site_id,
                "secret_ref": secret_ref,
                "allowed": allowed,
                "reason": reason,
                "at": datetime.now(UTC).isoformat(),
            }
        )
        logger.info(
            "secret.access runtime=%s module=%s ref=%s allowed=%s",
            runtime_instance_id,
            module_id,
            secret_ref,
            allowed,
        )
