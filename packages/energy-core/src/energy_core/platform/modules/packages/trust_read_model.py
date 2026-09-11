"""Persisted package trust read model for Store UI (no crypto revalidation)."""

from __future__ import annotations

from typing import Any

from energy_core.platform.modules.packages.types import InstalledPackageRecord, PackageState, SignatureStatus


def build_install_metadata(manifest, validation) -> dict[str, Any]:
    """Snapshot trust/permissions at install/update time for Store reads."""
    return {
        "entrypoint": manifest.entrypoint,
        "name": manifest.name,
        "signed": validation.signed,
        "signature_valid": validation.signature_valid,
        "publisher_trusted": validation.publisher_trusted,
        "publisher_status": "trusted" if validation.publisher_trusted else ("unsigned_dev" if validation.signed is False else "unknown"),
        "permissions": list(manifest.permissions),
        "provided_capabilities": list(manifest.provided_capabilities),
        "required_capabilities": list(manifest.required_capabilities),
        "optional_capabilities": list(manifest.optional_capabilities),
        "module_dependencies": [
            {"module_id": dep.module_id, "version_range": dep.version_range}
            for dep in manifest.module_dependencies
        ],
        "minimum_emic_version": manifest.minimum_emic_version,
        "maximum_emic_version": manifest.maximum_emic_version,
        "module_api_version": manifest.module_api_version,
    }


def trust_view_from_record(record: InstalledPackageRecord) -> dict[str, Any]:
    """Derive Store trust fields from persisted metadata + package state."""
    meta = record.metadata or {}
    status = record.signature_status
    signed = bool(meta.get("signed", status in {SignatureStatus.VALID, SignatureStatus.INVALID}))
    signature_valid = bool(meta.get("signature_valid", status == SignatureStatus.VALID))
    publisher_trusted = bool(meta.get("publisher_trusted", signature_valid and status == SignatureStatus.VALID))
    publisher_status = str(meta.get("publisher_status") or _default_publisher_status(status, publisher_trusted))
    install_allowed = record.package_state == PackageState.INSTALLED
    return {
        "signed": signed,
        "signature_valid": signature_valid,
        "publisher_trusted": publisher_trusted,
        "publisher_status": publisher_status,
        "install_allowed": install_allowed,
    }


def logical_package_id(module_id: str, version: str) -> str:
    return f"{module_id}@{version}"


def _default_publisher_status(status: SignatureStatus, publisher_trusted: bool) -> str:
    if publisher_trusted:
        return "trusted"
    if status == SignatureStatus.UNSIGNED:
        return "unsigned"
    if status == SignatureStatus.INVALID:
        return "invalid_signature"
    if status == SignatureStatus.MISSING:
        return "missing_signature"
    return "unknown"
