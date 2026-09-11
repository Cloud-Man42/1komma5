"""Policy engine unit tests."""

from __future__ import annotations

from energy_core.platform.modules.governance.policy_engine import ModuleInstallPolicyEngine
from energy_core.platform.modules.governance.revocation_reader import RevocationContext
from energy_core.platform.modules.governance.types import (
    InstallationPolicySnapshot,
    PolicyAction,
    PolicyDecision,
    PolicyEvaluationInput,
    PolicyReasonCode,
    PublisherSnapshot,
    PublisherStatus,
    PublisherTier,
    RevocationMatch,
)


def _policy(**overrides) -> InstallationPolicySnapshot:
    base = {
        "policy_scope": "installation",
        "policy_version": 1,
        "allowed_tiers": ("OFFICIAL", "VERIFIED", "ORG_APPROVED"),
        "publisher_allowlist": (),
        "publisher_denylist": (),
        "module_allowlist": (),
        "module_denylist": (),
        "blocked_permissions": (),
        "control_module_policy": "VERIFIED_OK",
        "break_glass_enabled": False,
        "updated_by": None,
        "updated_at": None,
    }
    base.update(overrides)
    return InstallationPolicySnapshot(**base)


def _publisher(**overrides) -> PublisherSnapshot:
    base = {
        "publisher_id": "emic",
        "display_name": "EMIC",
        "organization": None,
        "verified_domain": None,
        "tier": PublisherTier.OFFICIAL.value,
        "status": PublisherStatus.ACTIVE.value,
    }
    base.update(overrides)
    return PublisherSnapshot(**base)


def _request(**overrides) -> PolicyEvaluationInput:
    base = {
        "action": PolicyAction.INSTALL,
        "module_id": "demo.module",
        "publisher_id": "emic",
        "permissions": (),
        "provided_capabilities": (),
        "app_env_production": True,
        "break_glass_active": False,
    }
    base.update(overrides)
    return PolicyEvaluationInput(**base)


def test_official_publisher_allowed():
    engine = ModuleInstallPolicyEngine()
    result = engine.evaluate(
        policy=_policy(),
        publisher=_publisher(),
        revocation=None,
        request=_request(),
    )
    assert result.decision == PolicyDecision.ALLOW
    assert PolicyReasonCode.TIER_ALLOWED.value in result.reason_codes


def test_community_denied_in_production():
    engine = ModuleInstallPolicyEngine()
    result = engine.evaluate(
        policy=_policy(),
        publisher=_publisher(publisher_id="community", tier=PublisherTier.COMMUNITY.value),
        revocation=None,
        request=_request(publisher_id="community"),
    )
    assert result.decision == PolicyDecision.DENY
    assert PolicyReasonCode.COMMUNITY_NOT_ALLOWED.value in result.reason_codes


def test_revoked_publisher_denied():
    engine = ModuleInstallPolicyEngine()
    result = engine.evaluate(
        policy=_policy(),
        publisher=_publisher(tier=PublisherTier.REVOKED.value, status=PublisherStatus.REVOKED.value),
        revocation=None,
        request=_request(),
    )
    assert result.decision == PolicyDecision.DENY
    assert PolicyReasonCode.PUBLISHER_REVOKED.value in result.reason_codes


def test_module_denylist_precedence_over_allowlist():
    engine = ModuleInstallPolicyEngine()
    result = engine.evaluate(
        policy=_policy(module_denylist=("demo.module",), module_allowlist=("demo.module",)),
        publisher=_publisher(),
        revocation=None,
        request=_request(),
    )
    assert result.decision == PolicyDecision.DENY
    assert PolicyReasonCode.MODULE_DENIED.value in result.reason_codes


def test_control_run_denied_before_isolation_gate():
    engine = ModuleInstallPolicyEngine()
    result = engine.evaluate(
        policy=_policy(),
        publisher=_publisher(),
        revocation=None,
        request=_request(action=PolicyAction.RUN, permissions=("device.control",)),
    )
    assert result.decision == PolicyDecision.DENY
    assert PolicyReasonCode.CONTROL_MODULE_ISOLATION_REQUIRED.value in result.reason_codes


def test_critical_revocation_denied_even_with_break_glass():
    engine = ModuleInstallPolicyEngine()
    revocation = RevocationContext(
        freshness="fresh",
        metadata_health="healthy",
        revocations=(
            RevocationMatch(
                revocation_id="r1",
                severity="CRITICAL",
                scope="publisher",
                publisher_id="emic",
                module_id=None,
            ),
        ),
    )
    result = engine.evaluate(
        policy=_policy(break_glass_enabled=True),
        publisher=_publisher(),
        revocation=revocation,
        request=_request(break_glass_active=True, marketplace_metadata_enabled=True),
    )
    assert result.decision == PolicyDecision.DENY
    assert PolicyReasonCode.REVOCATION_ACTIVE.value in result.reason_codes


def test_break_glass_allows_community_when_enabled():
    engine = ModuleInstallPolicyEngine()
    result = engine.evaluate(
        policy=_policy(break_glass_enabled=True),
        publisher=_publisher(publisher_id="community", tier=PublisherTier.COMMUNITY.value),
        revocation=None,
        request=_request(publisher_id="community", break_glass_active=True),
    )
    assert result.decision == PolicyDecision.ALLOW
