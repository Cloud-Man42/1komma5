"""Filesystem layout for installed module packages."""

from __future__ import annotations

import re
from pathlib import Path

MODULE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:\.[a-z][a-z0-9_-]*)+$")
PROTECTED_MODULE_PREFIXES = ("core.", "platform.")
BUILTIN_MODULE_IDS = frozenset(
    {
        "integration.heartbeat",
        "integration.chargeamps",
        "integration.mercedes",
        "integration.arctic_spa",
        "integration.chargefinder",
        "integration.smhi",
        "integration.dmi",
        "integration.open_meteo",
        "feature.smart-charging",
        "feature.vehicles",
        "feature.spa-energy",
        "feature.energy-balance",
        "feature.solar-forecast",
        "feature.price-engine",
        "feature.energy-control",
    }
)


def validate_module_id(module_id: str) -> None:
    if not MODULE_ID_PATTERN.match(module_id):
        raise ValueError(f"invalid module_id: {module_id}")
    if module_id.startswith(PROTECTED_MODULE_PREFIXES):
        raise ValueError(f"protected module_id prefix: {module_id}")
    if module_id in BUILTIN_MODULE_IDS:
        raise ValueError(f"built-in module_id protected: {module_id}")


def is_protected_module_id(module_id: str) -> bool:
    return (
        module_id in BUILTIN_MODULE_IDS
        or module_id.startswith(PROTECTED_MODULE_PREFIXES)
        or not MODULE_ID_PATTERN.match(module_id)
    )


class ModulePackagePaths:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def ensure_layout(self) -> None:
        for sub in ("installed", ".staging", "data", "backups"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)

    def staging_dir(self, module_id: str, version: str) -> Path:
        return self.root / ".staging" / module_id / version

    def installed_dir(self, module_id: str, version: str) -> Path:
        return self.root / "installed" / module_id / version

    def data_dir(self, module_id: str) -> Path:
        return self.root / "data" / module_id

    def backup_dir(self, module_id: str, version: str) -> Path:
        return self.root / "backups" / module_id / version

    @staticmethod
    def safe_join(base: Path, member: str) -> Path:
        target = (base / member).resolve()
        base_resolved = base.resolve()
        if not str(target).startswith(str(base_resolved)):
            raise ValueError("path traversal detected")
        return target
