"""Config migration runner for package updates."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from packaging.version import Version

from energy_core.platform.modules.packages.errors import MIGRATION_FAILED, MIGRATION_REQUIRED, PackageError


def _migration_path(package_dir: Path, from_version: str, to_version: str) -> Path:
    safe_from = from_version.replace(".", "_")
    safe_to = to_version.replace(".", "_")
    return package_dir / "migrations" / f"{safe_from}_to_{safe_to}.py"


def requires_migration(from_version: str, to_version: str) -> bool:
    return Version(to_version).major > Version(from_version).major


def migrate_config(
    package_dir: Path,
    *,
    from_version: str,
    to_version: str,
    configuration: dict[str, Any],
) -> dict[str, Any]:
    if not requires_migration(from_version, to_version):
        return configuration
    script = _migration_path(package_dir, from_version, to_version)
    if not script.exists():
        raise PackageError(
            f"migration required from {from_version} to {to_version}",
            code=MIGRATION_REQUIRED,
        )
    spec = importlib.util.spec_from_file_location("pkg_migration", script)
    if spec is None or spec.loader is None:
        raise PackageError("migration script invalid", code=MIGRATION_FAILED)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    upgrade = getattr(module, "upgrade", None)
    if upgrade is None:
        raise PackageError("migration script missing upgrade()", code=MIGRATION_FAILED)
    try:
        result = upgrade(dict(configuration))
    except Exception as exc:
        raise PackageError(f"migration failed: {exc}", code=MIGRATION_FAILED) from exc
    if not isinstance(result, dict):
        raise PackageError("migration upgrade() must return dict", code=MIGRATION_FAILED)
    return result


def backup_config(configuration: dict[str, Any]) -> str:
    return json.dumps(configuration)
