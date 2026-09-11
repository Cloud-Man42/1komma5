"""Human-readable policy and security reason code explanations."""

from __future__ import annotations

from energy_core.platform.modules.governance.types import PolicyReasonCode

_REASON_EXPLANATIONS: dict[str, str] = {
    PolicyReasonCode.PUBLISHER_REVOKED.value: "The publisher has been revoked. Modules from this publisher cannot be installed.",
    PolicyReasonCode.PUBLISHER_SUSPENDED.value: "The publisher is suspended. Installation is temporarily blocked.",
    PolicyReasonCode.PUBLISHER_NOT_FOUND.value: "Publisher is not registered in governance.",
    PolicyReasonCode.TIER_NOT_ALLOWED.value: "This publisher trust tier is not permitted by organization policy.",
    PolicyReasonCode.PUBLISHER_DENIED.value: "This publisher is denied by organization policy.",
    PolicyReasonCode.MODULE_DENIED.value: "This module is denied by organization policy.",
    PolicyReasonCode.PERMISSION_BLOCKED.value: "A required permission is blocked by organization policy.",
    PolicyReasonCode.CONTROL_MODULE_ISOLATION_REQUIRED.value: (
        "This module can control physical equipment and cannot run until the control-module security gate has been approved."
    ),
    PolicyReasonCode.COMMUNITY_NOT_ALLOWED.value: "COMMUNITY modules are not permitted in production.",
    PolicyReasonCode.REVOCATION_ACTIVE.value: "An active revocation applies to this module or publisher.",
    PolicyReasonCode.REVOCATION_STALE.value: "Revocation metadata is stale — control actions denied.",
    PolicyReasonCode.REVOCATION_STATE_UNTRUSTED.value: "Revocation metadata is untrusted.",
    PolicyReasonCode.SECURITY_REVIEW_REQUIRED.value: "Security review is required before installation.",
    PolicyReasonCode.ADMIN_APPROVAL_REQUIRED.value: "Administrator approval is required.",
    PolicyReasonCode.KEY_REVOKED.value: "The publisher signing key has been revoked.",
    PolicyReasonCode.KEY_EXPIRED.value: "The publisher signing key has expired.",
    PolicyReasonCode.OWNERSHIP_MISMATCH.value: "Module ownership does not match the canonical publisher.",
    PolicyReasonCode.DEFAULT_DENY.value: "Organization policy denied this action.",
    PolicyReasonCode.VULNERABILITY_CRITICAL.value: "Critical security vulnerability detected.",
    PolicyReasonCode.SBOM_MISSING.value: "SBOM is required but missing.",
    PolicyReasonCode.SUPPLY_CHAIN_REVIEW_REQUIRED.value: "Supply-chain security review is required.",
    "INTEGRITY_NOT_VERIFIED": "Artifact integrity has not been verified.",
    "VULNERABILITY_HIGH": "High severity security vulnerability detected.",
    "VULNERABILITY_CRITICAL": "Critical security vulnerability detected.",
    "SBOM_INVALID": "SBOM data is invalid.",
    "ADVISORY_DATA_UNTRUSTED": "Advisory data is untrusted.",
    "SIGNATURE_INVALID": "Package signature is invalid or missing.",
    "INCOMPATIBLE_EMIC_VERSION": "Module is not compatible with this EMIC version.",
    "INCOMPATIBLE_MODULE_API_VERSION": "Module runtime protocol is not compatible.",
}


def explain_reason_codes(reason_codes: tuple[str, ...] | list[str], *, fallback: str = "") -> str:
    if not reason_codes:
        return fallback
    parts: list[str] = []
    for code in reason_codes:
        text = _REASON_EXPLANATIONS.get(code)
        if text and text not in parts:
            parts.append(text)
    if parts:
        return " ".join(parts)
    return fallback or reason_codes[0]
