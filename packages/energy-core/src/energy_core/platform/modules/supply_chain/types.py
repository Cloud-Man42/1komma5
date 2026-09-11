"""Supply-chain security types (Step 5C.4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class SbomStatus(StrEnum):
    MISSING = "MISSING"
    VALID = "VALID"
    INVALID = "INVALID"
    UNVERIFIED = "UNVERIFIED"


class AdvisoryStatus(StrEnum):
    UNAVAILABLE = "UNAVAILABLE"
    TRUSTED = "TRUSTED"
    UNTRUSTED = "UNTRUSTED"
    STALE = "STALE"


class SecuritySeverity(StrEnum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class SupplyChainErrorCode(StrEnum):
    SBOM_MISSING = "SBOM_MISSING"
    SBOM_INVALID = "SBOM_INVALID"
    SBOM_DIGEST_MISMATCH = "SBOM_DIGEST_MISMATCH"
    ADVISORY_DATA_UNTRUSTED = "ADVISORY_DATA_UNTRUSTED"
    VULNERABILITY_CRITICAL = "VULNERABILITY_CRITICAL"
    VULNERABILITY_HIGH = "VULNERABILITY_HIGH"
    SUPPLY_CHAIN_REVIEW_REQUIRED = "SUPPLY_CHAIN_REVIEW_REQUIRED"


class SupplyChainError(Exception):
    def __init__(self, message: str, *, code: SupplyChainErrorCode) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class SbomComponent:
    name: str
    version: str | None
    purl: str | None = None
    cpe: str | None = None
    supplier: str | None = None
    licenses: tuple[str, ...] = ()
    hashes: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ParsedSbom:
    format: str
    spec_version: str
    components: tuple[SbomComponent, ...]
    raw_digest: str
    dependencies: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class AdvisoryEntry:
    advisory_id: str
    source: str
    severity: SecuritySeverity
    published_at: str | None
    updated_at: str | None
    status: str
    affected_purl: str | None
    affected_package: str | None
    affected_version_range: str | None
    fixed_versions: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    withdrawn: bool = False


@dataclass(frozen=True, slots=True)
class VulnerabilityMatch:
    advisory_id: str
    component_name: str
    component_version: str | None
    purl: str | None
    severity: SecuritySeverity
    matched: bool
    version_status: str


@dataclass(frozen=True, slots=True)
class ReleaseSecuritySnapshot:
    sbom_status: SbomStatus
    advisory_status: AdvisoryStatus
    highest_severity: SecuritySeverity
    vulnerability_count: int
    critical_count: int
    high_count: int
    security_review_required: bool
    reason_codes: tuple[str, ...]
    integrity_verified: bool
    policy_decision: str | None = None
    vulnerabilities: tuple[VulnerabilityMatch, ...] = ()
