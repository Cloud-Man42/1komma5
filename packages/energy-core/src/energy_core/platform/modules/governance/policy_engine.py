"""Deterministic module install policy engine (Step 5C.2)."""

from __future__ import annotations

from energy_core.platform.modules.governance.revocation_reader import RevocationContext
from energy_core.platform.modules.governance.risk_classifier import is_control_capable
from energy_core.platform.modules.governance.types import (
    ControlModulePolicy,
    InstallationPolicySnapshot,
    PolicyAction,
    PolicyDecision,
    PolicyEvaluationInput,
    PolicyEvaluationResult,
    PolicyReasonCode,
    PublisherSnapshot,
    PublisherStatus,
    PublisherTier,
)

_PACKAGE_GOVERNANCE_ACTIONS = frozenset(
    {PolicyAction.INSTALL, PolicyAction.UPDATE, PolicyAction.ENABLE, PolicyAction.RUN}
)


class ModuleInstallPolicyEngine:
    """Pure deterministic policy evaluation — no network I/O."""

    CONTROL_ISOLATION_GATE_OPEN = False  # Step 5C.5

    def evaluate(
        self,
        *,
        policy: InstallationPolicySnapshot,
        publisher: PublisherSnapshot | None,
        revocation: RevocationContext | None,
        request: PolicyEvaluationInput,
    ) -> PolicyEvaluationResult:
        reasons: list[str] = []
        control_capable = is_control_capable(
            permissions=request.permissions,
            provided_capabilities=request.provided_capabilities,
        )

        if publisher is None:
            return self._result(
                decision=PolicyDecision.DENY,
                reasons=[PolicyReasonCode.PUBLISHER_NOT_FOUND.value],
                publisher=None,
                request=request,
                policy=policy,
                control_capable=control_capable,
                explanation="Publisher not registered in governance.",
            )

        if request.canonical_owner_publisher_id is not None:
            if request.publisher_id != request.canonical_owner_publisher_id:
                return self._deny(
                    PolicyReasonCode.OWNERSHIP_MISMATCH,
                    publisher,
                    request,
                    policy,
                    control_capable,
                    "Manifest publisher does not match canonical module ownership.",
                )

        tier = publisher.tier
        status = publisher.status

        if revocation is not None and request.marketplace_metadata_enabled:
            untrusted = self._revocation_trust_decision(
                revocation, request, policy, publisher, control_capable
            )
            if untrusted is not None:
                return untrusted

            active = self._active_revocation(revocation, request)
            if active is not None:
                return self._deny(
                    PolicyReasonCode.REVOCATION_ACTIVE,
                    publisher,
                    request,
                    policy,
                    control_capable,
                    "Active revocation applies.",
                )

        if request.module_id in policy.module_denylist:
            return self._deny(
                PolicyReasonCode.MODULE_DENIED,
                publisher,
                request,
                policy,
                control_capable,
                "Module is on organization denylist.",
            )

        if publisher.publisher_id in policy.publisher_denylist:
            return self._deny(
                PolicyReasonCode.PUBLISHER_DENIED,
                publisher,
                request,
                policy,
                control_capable,
                "Publisher is on organization denylist.",
            )

        if status == PublisherStatus.REVOKED.value or tier == PublisherTier.REVOKED.value:
            return self._deny(
                PolicyReasonCode.PUBLISHER_REVOKED,
                publisher,
                request,
                policy,
                control_capable,
                "Publisher is revoked.",
            )

        if status == PublisherStatus.SUSPENDED.value:
            return self._deny(
                PolicyReasonCode.PUBLISHER_SUSPENDED,
                publisher,
                request,
                policy,
                control_capable,
                "Publisher is suspended.",
            )

        for perm in request.permissions:
            if perm in policy.blocked_permissions:
                return self._deny(
                    PolicyReasonCode.PERMISSION_BLOCKED,
                    publisher,
                    request,
                    policy,
                    control_capable,
                    f"Permission {perm} is blocked by organization policy.",
                )

        if control_capable and request.action in {PolicyAction.RUN, PolicyAction.ENABLE}:
            if not self.CONTROL_ISOLATION_GATE_OPEN:
                return self._result(
                    decision=PolicyDecision.DENY,
                    reasons=[PolicyReasonCode.CONTROL_MODULE_ISOLATION_REQUIRED.value],
                    publisher=publisher,
                    request=request,
                    policy=policy,
                    control_capable=True,
                    explanation="Control-capable modules cannot RUN before Step 5C.5 isolation gate.",
                )

        if tier == PublisherTier.COMMUNITY.value and request.app_env_production:
            if not (request.break_glass_active and policy.break_glass_enabled):
                return self._deny(
                    PolicyReasonCode.COMMUNITY_NOT_ALLOWED,
                    publisher,
                    request,
                    policy,
                    control_capable,
                    "COMMUNITY tier is not permitted in production.",
                )

        if tier not in policy.allowed_tiers:
            if not (request.break_glass_active and policy.break_glass_enabled):
                return self._deny(
                    PolicyReasonCode.TIER_NOT_ALLOWED,
                    publisher,
                    request,
                    policy,
                    control_capable,
                    f"Publisher tier {tier} is not in allowed tiers.",
                )

        if control_capable and policy.control_module_policy == ControlModulePolicy.OFFICIAL_ONLY.value:
            if tier != PublisherTier.OFFICIAL.value:
                if not (request.break_glass_active and policy.break_glass_enabled):
                    return self._deny(
                        PolicyReasonCode.CONTROL_MODULE_ISOLATION_REQUIRED,
                        publisher,
                        request,
                        policy,
                        control_capable=True,
                        explanation="Control modules require OFFICIAL tier under current policy.",
                    )

        if request.module_id in policy.module_allowlist:
            reasons.append(PolicyReasonCode.ALLOWLIST_MATCH.value)
            return self._allow(publisher, request, policy, control_capable, reasons, "Module allowlist match.")

        if publisher.publisher_id in policy.publisher_allowlist and tier in policy.allowed_tiers:
            reasons.append(PolicyReasonCode.ALLOWLIST_MATCH.value)
            return self._allow(publisher, request, policy, control_capable, reasons, "Publisher allowlist match.")

        if tier in policy.allowed_tiers:
            reasons.append(PolicyReasonCode.TIER_ALLOWED.value)
            return self._allow(publisher, request, policy, control_capable, reasons, f"Tier {tier} allowed by policy.")

        if request.break_glass_active and policy.break_glass_enabled:
            reasons.append(PolicyReasonCode.BREAK_GLASS_ACTIVE.value)
            return self._allow(
                publisher,
                request,
                policy,
                control_capable,
                reasons,
                "Break-glass override active for non-critical restrictions.",
            )

        return self._deny(
            PolicyReasonCode.DEFAULT_DENY,
            publisher,
            request,
            policy,
            control_capable,
            "Default deny — no matching allow rule.",
        )

    def _revocation_trust_decision(
        self,
        revocation: RevocationContext,
        request: PolicyEvaluationInput,
        policy: InstallationPolicySnapshot,
        publisher: PublisherSnapshot,
        control_capable: bool,
    ) -> PolicyEvaluationResult | None:
        if request.action not in _PACKAGE_GOVERNANCE_ACTIONS:
            return None

        if revocation.metadata_health in {"invalid", "unavailable"}:
            return self._deny(
                PolicyReasonCode.REVOCATION_STATE_UNTRUSTED,
                publisher,
                request,
                policy,
                control_capable,
                "Revocation metadata is invalid or unavailable.",
            )

        if revocation.freshness == "expired":
            return self._deny(
                PolicyReasonCode.REVOCATION_STATE_UNTRUSTED,
                publisher,
                request,
                policy,
                control_capable,
                "Revocation metadata freshness is expired.",
            )

        if revocation.freshness == "stale":
            if request.action in {PolicyAction.ENABLE, PolicyAction.RUN} and control_capable:
                return self._deny(
                    PolicyReasonCode.REVOCATION_STALE,
                    publisher,
                    request,
                    policy,
                    control_capable=True,
                    explanation="Stale revocation metadata — control actions denied.",
                )
            if request.action in {PolicyAction.INSTALL, PolicyAction.UPDATE}:
                return self._result(
                    decision=PolicyDecision.REQUIRE_SECURITY_REVIEW,
                    reasons=[
                        PolicyReasonCode.REVOCATION_STALE.value,
                        PolicyReasonCode.SECURITY_REVIEW_REQUIRED.value,
                    ],
                    publisher=publisher,
                    request=request,
                    policy=policy,
                    control_capable=control_capable,
                    explanation="Stale revocation metadata — security review required before install/update.",
                )
        return None

    @staticmethod
    def _active_revocation(context: RevocationContext, request: PolicyEvaluationInput):
        for item in context.revocations:
            if item.publisher_id and item.publisher_id == request.publisher_id:
                return item
            if item.module_id and item.module_id == request.module_id:
                return item
        return None

    @staticmethod
    def _result(
        *,
        decision: PolicyDecision,
        reasons: list[str],
        publisher: PublisherSnapshot | None,
        request: PolicyEvaluationInput,
        policy: InstallationPolicySnapshot,
        control_capable: bool,
        explanation: str,
    ) -> PolicyEvaluationResult:
        return PolicyEvaluationResult(
            decision=decision,
            reason_codes=tuple(reasons),
            publisher_tier=publisher.tier if publisher else None,
            publisher_status=publisher.status if publisher else None,
            module_id=request.module_id,
            requested_permissions=request.permissions,
            control_capable=control_capable,
            policy_version=policy.policy_version,
            explanation=explanation,
        )

    def _deny(
        self,
        code: PolicyReasonCode,
        publisher: PublisherSnapshot,
        request: PolicyEvaluationInput,
        policy: InstallationPolicySnapshot,
        control_capable: bool,
        explanation: str,
    ) -> PolicyEvaluationResult:
        return self._result(
            decision=PolicyDecision.DENY,
            reasons=[code.value],
            publisher=publisher,
            request=request,
            policy=policy,
            control_capable=control_capable,
            explanation=explanation,
        )

    def _allow(
        self,
        publisher: PublisherSnapshot,
        request: PolicyEvaluationInput,
        policy: InstallationPolicySnapshot,
        control_capable: bool,
        reasons: list[str],
        explanation: str,
    ) -> PolicyEvaluationResult:
        return self._result(
            decision=PolicyDecision.ALLOW,
            reasons=tuple(reasons),
            publisher=publisher,
            request=request,
            policy=policy,
            control_capable=control_capable,
            explanation=explanation,
        )
