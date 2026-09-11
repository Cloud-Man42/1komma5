"""Module manifest parsing."""

from __future__ import annotations

from typing import Any

from energy_core.platform.modules.packages.errors import INVALID_MANIFEST, PackageError
from energy_core.platform.modules.packages.types import (
    ModuleDependencySpec,
    ModuleManifest,
    PackageIntegritySpec,
)


def parse_manifest_dict(raw: dict[str, Any]) -> ModuleManifest:
    required = (
        "module_id",
        "name",
        "version",
        "module_type",
        "description",
        "publisher",
        "entrypoint",
        "module_api_version",
        "minimum_emic_version",
        "provided_capabilities",
        "required_capabilities",
        "optional_capabilities",
        "module_dependencies",
        "configuration_schema",
        "permissions",
        "supports_per_site_activation",
        "requires_restart_on_update",
        "integrity",
    )
    missing = [key for key in required if key not in raw]
    if missing:
        raise PackageError(
            f"manifest missing required fields: {', '.join(missing)}",
            code=INVALID_MANIFEST,
        )

    integrity_raw = raw["integrity"]
    if not isinstance(integrity_raw, dict) or "archive_sha256" not in integrity_raw:
        raise PackageError("integrity.archive_sha256 is required", code=INVALID_MANIFEST)

    deps: list[ModuleDependencySpec] = []
    for item in raw.get("module_dependencies") or []:
        if isinstance(item, str):
            deps.append(ModuleDependencySpec(module_id=item))
        elif isinstance(item, dict) and "module_id" in item:
            deps.append(
                ModuleDependencySpec(
                    module_id=str(item["module_id"]),
                    version_range=str(item.get("version_range", "*")),
                )
            )
        else:
            raise PackageError("invalid module_dependencies entry", code=INVALID_MANIFEST)

    return ModuleManifest(
        module_id=str(raw["module_id"]),
        name=str(raw["name"]),
        version=str(raw["version"]),
        module_type=str(raw["module_type"]),
        description=str(raw["description"]),
        publisher=str(raw["publisher"]),
        entrypoint=str(raw["entrypoint"]),
        module_api_version=int(raw["module_api_version"]),
        minimum_emic_version=str(raw["minimum_emic_version"]),
        provided_capabilities=tuple(str(c) for c in raw.get("provided_capabilities") or []),
        required_capabilities=tuple(str(c) for c in raw.get("required_capabilities") or []),
        optional_capabilities=tuple(str(c) for c in raw.get("optional_capabilities") or []),
        module_dependencies=tuple(deps),
        configuration_schema=dict(raw.get("configuration_schema") or {}),
        permissions=tuple(str(p) for p in raw.get("permissions") or []),
        supports_per_site_activation=bool(raw["supports_per_site_activation"]),
        requires_restart_on_update=bool(raw["requires_restart_on_update"]),
        integrity=PackageIntegritySpec(
            archive_sha256=str(integrity_raw["archive_sha256"]).lower(),
            manifest_sha256=(
                str(integrity_raw["manifest_sha256"]).lower()
                if integrity_raw.get("manifest_sha256")
                else None
            ),
        ),
        maximum_emic_version=(
            str(raw["maximum_emic_version"]) if raw.get("maximum_emic_version") else None
        ),
        license=str(raw["license"]) if raw.get("license") else None,
        supports_multiple_devices=bool(raw.get("supports_multiple_devices", False)),
        onboard_handler=str(raw["onboard_handler"]) if raw.get("onboard_handler") else None,
        supports_discovery=bool(raw.get("supports_discovery", False)),
        can_disable=bool(raw.get("can_disable", True)),
        onboardable=bool(raw.get("onboardable", False)),
        device_categories=tuple(str(c) for c in raw.get("device_categories") or []),
        connection_types=tuple(str(c) for c in raw.get("connection_types") or []),
        features=tuple(item for item in raw.get("features") or [] if isinstance(item, dict)),
        network_hosts=tuple(str(h) for h in raw.get("network_hosts") or [] if isinstance(h, str)),
    )
