"""Adversarial governance security tests."""

from __future__ import annotations

from energy_core.platform.modules.governance.policy_engine import ModuleInstallPolicyEngine
from energy_core.platform.modules.governance.types import (
    InstallationPolicySnapshot,
    PolicyAction,
    PolicyDecision,
    PolicyEvaluationInput,
    PolicyReasonCode,
    PublisherSnapshot,
    PublisherStatus,
    PublisherTier,
)


def _policy(**kwargs) -> InstallationPolicySnapshot:
    defaults = dict(
        policy_scope="installation",
        policy_version=1,
        allowed_tiers=("OFFICIAL", "VERIFIED", "ORG_APPROVED"),
        publisher_allowlist=("trusted-pub",),
        publisher_denylist=("evil-pub",),
        module_allowlist=("trusted.mod",),
        module_denylist=("evil.mod",),
        blocked_permissions=("energy.control",),
        control_module_policy="OFFICIAL_ONLY",
        break_glass_enabled=True,
        updated_by=None,
        updated_at=None,
    )
    defaults.update(kwargs)
    return InstallationPolicySnapshot(**defaults)


def _publisher(**kwargs) -> PublisherSnapshot:
    defaults = dict(
        publisher_id="trusted-pub",
        display_name="Trusted",
        organization=None,
        verified_domain=None,
        tier=PublisherTier.VERIFIED.value,
        status=PublisherStatus.ACTIVE.value,
    )
    defaults.update(kwargs)
    return PublisherSnapshot(**defaults)


def test_denylist_beats_allowlist():
    engine = ModuleInstallPolicyEngine()
    result = engine.evaluate(
        policy=_policy(),
        publisher=_publisher(publisher_id="evil-pub", tier=PublisherTier.VERIFIED.value),
        revocation=None,
        request=PolicyEvaluationInput(
            action=PolicyAction.INSTALL,
            module_id="any.mod",
            publisher_id="evil-pub",
            app_env_production=True,
        ),
    )
    assert result.decision == PolicyDecision.DENY
    assert PolicyReasonCode.PUBLISHER_DENIED.value in result.reason_codes


def test_tier_from_target_publisher_after_transfer():
    """Effective tier is evaluated from target publisher, not source OFFICIAL snapshot."""
    engine = ModuleInstallPolicyEngine()
    target = _publisher(publisher_id="target", tier=PublisherTier.ORG_APPROVED.value)
    result = engine.evaluate(
        policy=_policy(allowed_tiers=("OFFICIAL", "VERIFIED", "ORG_APPROVED")),
        publisher=target,
        revocation=None,
        request=PolicyEvaluationInput(
            action=PolicyAction.INSTALL,
            module_id="transferred.mod",
            publisher_id="target",
            app_env_production=True,
        ),
    )
    assert result.decision == PolicyDecision.ALLOW
    assert result.publisher_tier == PublisherTier.ORG_APPROVED.value


def test_break_glass_cannot_override_revoked_publisher():
    engine = ModuleInstallPolicyEngine()
    result = engine.evaluate(
        policy=_policy(break_glass_enabled=True),
        publisher=_publisher(tier=PublisherTier.REVOKED.value, status=PublisherStatus.REVOKED.value),
        revocation=None,
        request=PolicyEvaluationInput(
            action=PolicyAction.INSTALL,
            module_id="mod",
            publisher_id="trusted-pub",
            break_glass_active=True,
            app_env_production=True,
        ),
    )
    assert result.decision == PolicyDecision.DENY
    assert PolicyReasonCode.PUBLISHER_REVOKED.value in result.reason_codes
