"""Publisher governance and policy types (Step 5C.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class PublisherTier(StrEnum):
    OFFICIAL = "OFFICIAL"
    VERIFIED = "VERIFIED"
    ORG_APPROVED = "ORG_APPROVED"
    COMMUNITY = "COMMUNITY"
    REVOKED = "REVOKED"


class PublisherStatus(StrEnum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class PublisherKeyGovernanceStatus(StrEnum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    DISABLED = "DISABLED"


class VerificationStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class TransferStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class PolicyDecision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_ADMIN_APPROVAL = "REQUIRE_ADMIN_APPROVAL"
    REQUIRE_SECURITY_REVIEW = "REQUIRE_SECURITY_REVIEW"


class PolicyAction(StrEnum):
    INSTALL = "INSTALL"
    UPDATE = "UPDATE"
    ENABLE = "ENABLE"
    RUN = "RUN"


class ControlModulePolicy(StrEnum):
    OFFICIAL_ONLY = "OFFICIAL_ONLY"
    VERIFIED_OK = "VERIFIED_OK"


class PolicyReasonCode(StrEnum):
    PUBLISHER_REVOKED = "PUBLISHER_REVOKED"
    PUBLISHER_SUSPENDED = "PUBLISHER_SUSPENDED"
    PUBLISHER_NOT_FOUND = "PUBLISHER_NOT_FOUND"
    TIER_NOT_ALLOWED = "TIER_NOT_ALLOWED"
    PUBLISHER_DENIED = "PUBLISHER_DENIED"
    MODULE_DENIED = "MODULE_DENIED"
    PERMISSION_BLOCKED = "PERMISSION_BLOCKED"
    CONTROL_MODULE_ISOLATION_REQUIRED = "CONTROL_MODULE_ISOLATION_REQUIRED"
    COMMUNITY_NOT_ALLOWED = "COMMUNITY_NOT_ALLOWED"
    REVOCATION_ACTIVE = "REVOCATION_ACTIVE"
    REVOCATION_STALE = "REVOCATION_STALE"
    REVOCATION_STATE_UNTRUSTED = "REVOCATION_STATE_UNTRUSTED"
    SECURITY_REVIEW_REQUIRED = "SECURITY_REVIEW_REQUIRED"
    ADMIN_APPROVAL_REQUIRED = "ADMIN_APPROVAL_REQUIRED"
    KEY_REVOKED = "KEY_REVOKED"
    KEY_EXPIRED = "KEY_EXPIRED"
    OWNERSHIP_MISMATCH = "OWNERSHIP_MISMATCH"
    DEFAULT_DENY = "DEFAULT_DENY"
    ALLOWLIST_MATCH = "ALLOWLIST_MATCH"
    TIER_ALLOWED = "TIER_ALLOWED"
    BREAK_GLASS_ACTIVE = "BREAK_GLASS_ACTIVE"
    ARTIFACT_DIGEST_MISMATCH = "ARTIFACT_DIGEST_MISMATCH"
    SBOM_MISSING = "SBOM_MISSING"
    VULNERABILITY_CRITICAL = "VULNERABILITY_CRITICAL"
    SUPPLY_CHAIN_REVIEW_REQUIRED = "SUPPLY_CHAIN_REVIEW_REQUIRED"


class GovernanceErrorCode(StrEnum):
    PUBLISHER_NOT_FOUND = "PUBLISHER_NOT_FOUND"
    PUBLISHER_REVOKED = "PUBLISHER_REVOKED"
    PUBLISHER_SUSPENDED = "PUBLISHER_SUSPENDED"
    INVALID_TRUST_TIER = "INVALID_TRUST_TIER"
    INVALID_PUBLISHER_KEY = "INVALID_PUBLISHER_KEY"
    KEY_ALREADY_EXISTS = "KEY_ALREADY_EXISTS"
    OWNERSHIP_TRANSFER_NOT_ALLOWED = "OWNERSHIP_TRANSFER_NOT_ALLOWED"
    POLICY_CONFLICT = "POLICY_CONFLICT"
    POLICY_DENIED = "POLICY_DENIED"
    SECURITY_REVIEW_REQUIRED = "SECURITY_REVIEW_REQUIRED"
    INVALID_TRANSITION = "INVALID_TRANSITION"
    TRANSFER_NOT_FOUND = "TRANSFER_NOT_FOUND"


class RiskLevel(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


POLICY_SCOPE_INSTALLATION = "installation"

DEFAULT_ALLOWED_TIERS = (
    PublisherTier.OFFICIAL,
    PublisherTier.VERIFIED,
    PublisherTier.ORG_APPROVED,
)


@dataclass(frozen=True, slots=True)
class PolicyEvaluationResult:
    decision: PolicyDecision
    reason_codes: tuple[str, ...]
    publisher_tier: str | None = None
    publisher_status: str | None = None
    module_id: str | None = None
    requested_permissions: tuple[str, ...] = ()
    control_capable: bool = False
    policy_version: int = 0
    explanation: str = ""


@dataclass(frozen=True, slots=True)
class InstallationPolicySnapshot:
    policy_scope: str
    policy_version: int
    allowed_tiers: tuple[str, ...]
    publisher_allowlist: tuple[str, ...]
    publisher_denylist: tuple[str, ...]
    module_allowlist: tuple[str, ...]
    module_denylist: tuple[str, ...]
    blocked_permissions: tuple[str, ...]
    control_module_policy: str
    break_glass_enabled: bool
    supply_chain_policy: dict[str, Any] = field(default_factory=dict)
    updated_by: str | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class PublisherSnapshot:
    publisher_id: str
    display_name: str
    organization: str | None
    verified_domain: str | None
    tier: str
    status: str


@dataclass(frozen=True, slots=True)
class RevocationMatch:
    revocation_id: str
    severity: str | None
    scope: str | None
    publisher_id: str | None
    module_id: str | None


@dataclass(frozen=True, slots=True)
class PolicyEvaluationInput:
    action: PolicyAction
    module_id: str
    publisher_id: str
    permissions: tuple[str, ...] = ()
    provided_capabilities: tuple[str, ...] = ()
    key_id: str | None = None
    signature_valid: bool = False
    publisher_trusted: bool = False
    app_env_production: bool = True
    break_glass_active: bool = False
    canonical_owner_publisher_id: str | None = None
    marketplace_metadata_enabled: bool = False


@dataclass
class BreakGlassSession:
    reason: str
    expires_at: datetime
    actor: str
    created_at: datetime = field(default_factory=lambda: datetime.now())


def json_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return []
