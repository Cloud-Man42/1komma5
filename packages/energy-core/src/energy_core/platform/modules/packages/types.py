"""Package lifecycle types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class PackageState(StrEnum):
    AVAILABLE = "available"
    INSTALLED = "installed"
    UPDATE_AVAILABLE = "update_available"
    DISABLED = "disabled"
    BROKEN = "broken"
    QUARANTINED = "quarantined"
    REMOVING = "removing"


class SignatureStatus(StrEnum):
    VALID = "valid"
    UNSIGNED = "unsigned"
    INVALID = "invalid"
    MISSING = "missing"


class PackageSource(StrEnum):
    BUILT_IN = "built-in"
    INSTALLED = "installed"
    QUARANTINED = "quarantined"


@dataclass(frozen=True, slots=True)
class ModuleDependencySpec:
    module_id: str
    version_range: str = "*"


@dataclass(frozen=True, slots=True)
class PackageIntegritySpec:
    archive_sha256: str
    manifest_sha256: str | None = None


@dataclass(frozen=True, slots=True)
class ModuleManifest:
    module_id: str
    name: str
    version: str
    module_type: str
    description: str
    publisher: str
    entrypoint: str
    module_api_version: int
    minimum_emic_version: str
    provided_capabilities: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    optional_capabilities: tuple[str, ...]
    module_dependencies: tuple[ModuleDependencySpec, ...]
    configuration_schema: dict[str, Any]
    permissions: tuple[str, ...]
    supports_per_site_activation: bool
    requires_restart_on_update: bool
    integrity: PackageIntegritySpec
    maximum_emic_version: str | None = None
    license: str | None = None
    supports_multiple_devices: bool = False
    onboard_handler: str | None = None
    supports_discovery: bool = False
    can_disable: bool = True
    onboardable: bool = False
    device_categories: tuple[str, ...] = ()
    connection_types: tuple[str, ...] = ()
    features: tuple[dict[str, Any], ...] = ()
    network_hosts: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ModuleFeatureSpec:
    feature_id: str
    feature_name: str
    description: str
    required_capabilities: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ValidationResult:
    valid: bool
    manifest: ModuleManifest | None = None
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    signed: bool = False
    signature_valid: bool = False
    publisher_trusted: bool = False
    publisher_identity_valid: bool = False
    install_allowed: bool = False
    policy_decision: str | None = None
    policy_reason_codes: tuple[str, ...] = ()
    policy_explanation: str | None = None
    publisher_tier: str | None = None
    control_capable: bool = False
    policy_version: int | None = None


@dataclass(frozen=True, slots=True)
class PackageImpactReport:
    module_id: str
    affected_modules: tuple[str, ...] = ()
    affected_sites: tuple[str, ...] = ()
    capabilities_added: tuple[str, ...] = ()
    capabilities_removed: tuple[str, ...] = ()
    affected_devices: tuple[str, ...] = ()
    restart_required: bool = False
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PackageMutationResult:
    module_id: str
    success: bool
    message: str
    package_state: str
    installed_version: str | None = None
    restart_required: bool = False
    rollback_version: str | None = None


@dataclass(slots=True)
class InstalledPackageRecord:
    module_id: str
    installed_version: str
    package_state: PackageState
    package_path: str
    publisher: str
    source: str
    checksum_sha256: str
    signature_status: SignatureStatus
    rollback_version: str | None
    previous_package_path: str | None
    module_api_version: int
    restart_required: bool
    staging_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
