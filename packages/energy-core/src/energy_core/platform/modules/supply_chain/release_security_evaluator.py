"""Release supply-chain security evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from energy_core.platform.modules.governance.types import PolicyDecision
from energy_core.platform.modules.supply_chain.types import (
    AdvisoryStatus,
    ReleaseSecuritySnapshot,
    SecuritySeverity,
    SbomStatus,
    SupplyChainErrorCode,
    VulnerabilityMatch,
)
from energy_core.platform.modules.supply_chain.vulnerability_matcher import highest_severity, match_vulnerabilities


@dataclass(frozen=True, slots=True)
class SupplyChainPolicy:
    require_sbom: bool = False
    deny_critical_vulnerabilities: bool = True
    max_allowed_severity: SecuritySeverity = SecuritySeverity.HIGH
    require_review_for_high: bool = True

    @classmethod
    def from_json(cls, raw: dict[str, Any] | None) -> SupplyChainPolicy:
        if not raw:
            return cls()
        max_sev = str(raw.get("max_allowed_severity", "HIGH")).upper()
        try:
            max_allowed = SecuritySeverity(max_sev)
        except ValueError:
            max_allowed = SecuritySeverity.HIGH
        return cls(
            require_sbom=bool(raw.get("require_sbom", False)),
            deny_critical_vulnerabilities=bool(raw.get("deny_critical_vulnerabilities", True)),
            max_allowed_severity=max_allowed,
            require_review_for_high=bool(raw.get("require_review_for_high", True)),
        )


class ReleaseSecurityEvaluator:
    def evaluate(
        self,
        *,
        sbom_status: SbomStatus,
        advisory_status: AdvisoryStatus,
        vulnerabilities: tuple[VulnerabilityMatch, ...],
        supply_chain_policy: SupplyChainPolicy,
        governance_decision: PolicyDecision,
        integrity_verified: bool,
    ) -> ReleaseSecuritySnapshot:
        reasons: list[str] = []
        critical = sum(1 for v in vulnerabilities if v.matched and v.severity == SecuritySeverity.CRITICAL)
        high = sum(1 for v in vulnerabilities if v.matched and v.severity == SecuritySeverity.HIGH)
        highest = highest_severity(vulnerabilities)
        review_required = False

        if not integrity_verified:
            reasons.append("INTEGRITY_NOT_VERIFIED")
        if sbom_status == SbomStatus.MISSING and supply_chain_policy.require_sbom:
            reasons.append(SupplyChainErrorCode.SBOM_MISSING.value)
            review_required = True
        if sbom_status == SbomStatus.INVALID:
            reasons.append(SupplyChainErrorCode.SBOM_INVALID.value)
        if advisory_status == AdvisoryStatus.UNTRUSTED:
            reasons.append(SupplyChainErrorCode.ADVISORY_DATA_UNTRUSTED.value)
            review_required = True
        if critical > 0:
            reasons.append(SupplyChainErrorCode.VULNERABILITY_CRITICAL.value)
        if high > 0:
            reasons.append(SupplyChainErrorCode.VULNERABILITY_HIGH.value)

        if supply_chain_policy.deny_critical_vulnerabilities and critical > 0:
            review_required = True
        if supply_chain_policy.require_review_for_high and high > 0:
            review_required = True

        sev_order = [
            SecuritySeverity.NONE,
            SecuritySeverity.LOW,
            SecuritySeverity.MEDIUM,
            SecuritySeverity.HIGH,
            SecuritySeverity.CRITICAL,
            SecuritySeverity.UNKNOWN,
        ]
        if sev_order.index(highest) > sev_order.index(supply_chain_policy.max_allowed_severity):
            review_required = True
            reasons.append(SupplyChainErrorCode.SUPPLY_CHAIN_REVIEW_REQUIRED.value)

        policy_decision = governance_decision.value
        if governance_decision == PolicyDecision.DENY:
            policy_decision = PolicyDecision.DENY.value
        elif review_required and governance_decision == PolicyDecision.ALLOW:
            policy_decision = PolicyDecision.REQUIRE_SECURITY_REVIEW.value
            reasons.append(SupplyChainErrorCode.SUPPLY_CHAIN_REVIEW_REQUIRED.value)

        return ReleaseSecuritySnapshot(
            sbom_status=sbom_status,
            advisory_status=advisory_status,
            highest_severity=highest,
            vulnerability_count=len([v for v in vulnerabilities if v.matched]),
            critical_count=critical,
            high_count=high,
            security_review_required=review_required,
            reason_codes=tuple(dict.fromkeys(reasons)),
            integrity_verified=integrity_verified,
            policy_decision=policy_decision,
            vulnerabilities=vulnerabilities,
        )

    def blocks_staging(self, snapshot: ReleaseSecuritySnapshot, policy: SupplyChainPolicy) -> bool:
        if not snapshot.integrity_verified:
            return True
        if snapshot.policy_decision == PolicyDecision.DENY.value:
            return True
        if policy.deny_critical_vulnerabilities and snapshot.critical_count > 0:
            return True
        if snapshot.sbom_status == SbomStatus.INVALID:
            return True
        return False
