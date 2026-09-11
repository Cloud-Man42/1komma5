"""Module Store view-model types (Sprint D)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class StoreOrigin(StrEnum):
    BUILT_IN = "BUILT_IN"
    INTERNAL_STORE = "INTERNAL_STORE"
    ORGANIZATION = "ORGANIZATION"
    PUBLIC_MARKETPLACE = "PUBLIC_MARKETPLACE"
    INSTALLED = "INSTALLED"


class StorePrimaryAction(StrEnum):
    INSTALL = "INSTALL"
    UPDATE = "UPDATE"
    INSTALLED = "INSTALLED"
    STAGED = "STAGED"
    SECURITY_REVIEW_REQUIRED = "SECURITY_REVIEW_REQUIRED"
    BLOCKED_BY_POLICY = "BLOCKED_BY_POLICY"
    RUNTIME_NOT_PERMITTED = "RUNTIME_NOT_PERMITTED"
    REVOKED = "REVOKED"
    INCOMPATIBLE = "INCOMPATIBLE"
    NONE = "NONE"


class StoreInstallState(StrEnum):
    NOT_INSTALLED = "NOT_INSTALLED"
    FETCHING = "FETCHING"
    VERIFYING = "VERIFYING"
    STAGED = "STAGED"
    INSTALLED = "INSTALLED"
    UPDATE_AVAILABLE = "UPDATE_AVAILABLE"
    BLOCKED = "BLOCKED"
    QUARANTINED = "QUARANTINED"


class StoreSecurityBadge(StrEnum):
    VERIFIED_ARTIFACT = "VERIFIED_ARTIFACT"
    SBOM_AVAILABLE = "SBOM_AVAILABLE"
    NO_CRITICAL_ISSUES = "NO_CRITICAL_ISSUES"
    SECURITY_REVIEW_REQUIRED = "SECURITY_REVIEW_REQUIRED"
    CRITICAL_ADVISORY = "CRITICAL_ADVISORY"
    REVOKED = "REVOKED"
    UNSIGNED = "UNSIGNED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class StorePolicyView:
    decision: str
    reason_codes: tuple[str, ...]
    explanation: str
    publisher_tier: str | None = None
    control_capable: bool = False
    policy_version: int | None = None


@dataclass(frozen=True, slots=True)
class StorePermissionView:
    permission: str
    label: str
    risk_level: str
    group: str


@dataclass(frozen=True, slots=True)
class StoreCapabilityView:
    capability: str
    label: str


@dataclass(frozen=True, slots=True)
class StoreFeatureView:
    feature_id: str
    feature_name: str
    description: str
    required_capabilities: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StoreCompatibilityView:
    compatible: bool
    emic_version: str
    minimum_emic_version: str | None = None
    maximum_emic_version: str | None = None
    module_api_version: int | None = None
    required_emic_module_api_version: int | None = None
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StoreSecurityView:
    artifact_integrity: str
    signature_status: str
    publisher_trust: str
    ownership_verified: bool
    sbom_status: str
    sbom_summary: dict[str, Any] | None
    advisory_status: str
    highest_severity: str
    vulnerability_count: int
    critical_count: int
    high_count: int
    revocation_state: str
    security_decision: str
    reason_codes: tuple[str, ...]
    last_evaluated: str | None = None
    runtime_blocked: bool = True
    runtime_message: str = ""


@dataclass(frozen=True, slots=True)
class StorePublisherSummary:
    publisher_id: str
    display_name: str
    tier: str
    status: str
    module_count: int = 0


@dataclass(frozen=True, slots=True)
class StorePublisherDetail:
    publisher_id: str
    display_name: str
    legal_name: str | None
    organization: str | None
    tier: str
    status: str
    verified_domain: str | None
    verified_at: str | None
    active_keys: tuple[str, ...]
    modules: tuple[str, ...]
    recent_releases: tuple[dict[str, str], ...]
    security_status: str


@dataclass(frozen=True, slots=True)
class StoreModuleSummary:
    module_id: str
    display_name: str
    publisher_id: str
    publisher_name: str
    description: str
    category: str
    categories: tuple[str, ...]
    icon_url: str | None
    origin: str
    trust_tier: str
    trust_badge: str
    security_badge: str
    installed_state: str
    installed_version: str | None
    latest_version: str | None
    update_available: bool
    compatible: bool
    control_capable: bool
    primary_action: str
    policy: StorePolicyView
    capabilities_summary: tuple[str, ...] = ()
    published_at: str | None = None
    source_precedence: str = "PUBLIC"


@dataclass(frozen=True, slots=True)
class StoreModuleDetail:
    summary: StoreModuleSummary
    long_description: str
    capabilities: tuple[StoreCapabilityView, ...]
    permissions: tuple[StorePermissionView, ...]
    features: tuple[StoreFeatureView, ...]
    compatibility: StoreCompatibilityView
    security: StoreSecurityView
    dependencies: tuple[dict[str, str], ...]
    configuration_schema: dict[str, Any]
    supports_per_site_activation: bool
    changelog: str | None = None
    website_url: str | None = None
    support_url: str | None = None
    docs_url: str | None = None


@dataclass(frozen=True, slots=True)
class StoreReleaseItem:
    version: str
    release_id: str
    channel: str
    published_at: str | None
    compatible: bool
    security_status: str
    installed: bool
    staged: bool
    policy_decision: str
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StoreCatalogPage:
    modules: tuple[StoreModuleSummary, ...]
    page: int
    page_size: int
    total: int
    categories: tuple[dict[str, Any], ...] = ()
    marketplace_status: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StoreStatusView:
    marketplace_enabled: bool
    metadata_health: str
    revocation_freshness: str
    last_sync: str | None
    last_success: str | None
    last_error: str | None
    offline: bool
    stale: bool
    invalid: bool
    catalog_freshness_seconds: float | None
    message: str


@dataclass(frozen=True, slots=True)
class StoreSecurityCenterView:
    installed_count: int
    updates_available: int
    security_reviews_required: int
    critical_issues: int
    quarantined_count: int
    revoked_publishers: tuple[str, ...]
    quarantined: tuple[dict[str, Any], ...]
    critical_advisories: tuple[dict[str, Any], ...]
    high_advisories: tuple[dict[str, Any], ...]
    review_required_modules: tuple[str, ...]
    metadata_health: str


@dataclass(frozen=True, slots=True)
class StoreSiteOption:
    site_slug: str
    site_name: str


@dataclass(frozen=True, slots=True)
class StorePreflightResponse:
    module_id: str
    version: str
    display_name: str
    publisher_id: str
    publisher_name: str
    trust_tier: str
    publisher_status: str
    signature_valid: bool
    ownership_verified: bool
    security: StoreSecurityView
    compatibility: StoreCompatibilityView
    permissions: tuple[StorePermissionView, ...]
    capabilities: tuple[StoreCapabilityView, ...]
    features: tuple[StoreFeatureView, ...]
    sites: tuple[StoreSiteOption, ...]
    configuration_schema: dict[str, Any]
    policy: StorePolicyView
    primary_action: str
    install_allowed: bool
    stage_allowed: bool
    runtime_blocked: bool
    runtime_message: str
    config_errors: tuple[str, ...] = ()
