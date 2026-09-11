"""Post-update health gate for package modules."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

from energy_core.platform.modules.packages.errors import HEALTH_GATE_FAILED, PackageError
from energy_core.platform.modules.sdk.context import EmicModuleContext
from energy_core.platform.modules.sdk.health import HealthLevel
from energy_core.platform.modules.sdk.manifest import parse_manifest_dict


def _schema_defaults(configuration_schema: dict[str, Any]) -> dict[str, Any]:
    defaults: dict[str, Any] = {}
    for field in configuration_schema.get("fields") or []:
        if isinstance(field, dict) and "name" in field and "default" in field:
            defaults[str(field["name"])] = field["default"]
    return defaults


def evaluate_package_health(package_dir: Path) -> None:
    manifest_raw = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest = parse_manifest_dict(manifest_raw)
    module_root = package_dir / "module"
    if module_root.exists() and str(module_root) not in sys.path:
        sys.path.insert(0, str(module_root))
    if not manifest.entrypoint or ":" not in manifest.entrypoint:
        raise PackageError("entrypoint missing", code=HEALTH_GATE_FAILED)
    module_name, attr = manifest.entrypoint.split(":", 1)
    imported = importlib.import_module(module_name)
    factory = getattr(imported, attr)
    configuration = _schema_defaults(manifest.configuration_schema)
    runtime = factory(
        EmicModuleContext(
            site_id=None,
            module_id=manifest.module_id,
            installed_version=manifest.version,
            configuration=configuration,
        )
    )
    if hasattr(runtime, "health"):
        status = runtime.health()
        if status.level != HealthLevel.OK:
            raise PackageError(status.message or "health gate failed", code=HEALTH_GATE_FAILED)
