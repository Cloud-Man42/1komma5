"""Revocation hardening tests (M2/M3)."""

from __future__ import annotations

import pytest

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


def _policy(**kw) -> InstallationPolicySnapshot:
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
        "break_glass_enabled": True,
    }
    base.update(kw)
    return InstallationPolicySnapshot(**base)


def _publisher(**kw) -> PublisherSnapshot:
    base = {
        "publisher_id": "emic",
        "display_name": "EMIC",
        "organization": None,
        "verified_domain": None,
        "tier": PublisherTier.OFFICIAL.value,
        "status": PublisherStatus.ACTIVE.value,
    }
    base.update(kw)
    return PublisherSnapshot(**base)


def _request(**kw) -> PolicyEvaluationInput:
    base = {
        "action": PolicyAction.INSTALL,
        "module_id": "demo.mod",
        "publisher_id": "emic",
        "marketplace_metadata_enabled": True,
        "break_glass_active": True,
        "app_env_production": True,
    }
    base.update(kw)
    return PolicyEvaluationInput(**base)


@pytest.mark.parametrize("severity", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
def test_active_revocation_denied_regardless_of_break_glass(severity: str):
    engine = ModuleInstallPolicyEngine()
    revocation = RevocationContext(
        freshness="fresh",
        metadata_health="healthy",
        revocations=(
            RevocationMatch(
                revocation_id="r1",
                severity=severity,
                scope="publisher",
                publisher_id="emic",
                module_id=None,
            ),
        ),
    )
    result = engine.evaluate(
        policy=_policy(),
        publisher=_publisher(),
        revocation=revocation,
        request=_request(),
    )
    assert result.decision == PolicyDecision.DENY
    assert PolicyReasonCode.REVOCATION_ACTIVE.value in result.reason_codes


def test_expired_revocation_metadata_denies_install():
    engine = ModuleInstallPolicyEngine()
    revocation = RevocationContext(freshness="expired", metadata_health="healthy", revocations=())
    result = engine.evaluate(
        policy=_policy(),
        publisher=_publisher(),
        revocation=revocation,
        request=_request(),
    )
    assert result.decision == PolicyDecision.DENY
    assert PolicyReasonCode.REVOCATION_STATE_UNTRUSTED.value in result.reason_codes


def test_invalid_revocation_metadata_denies_install():
    engine = ModuleInstallPolicyEngine()
    revocation = RevocationContext(freshness="fresh", metadata_health="invalid", revocations=())
    result = engine.evaluate(
        policy=_policy(),
        publisher=_publisher(),
        revocation=revocation,
        request=_request(),
    )
    assert result.decision == PolicyDecision.DENY
    assert PolicyReasonCode.REVOCATION_STATE_UNTRUSTED.value in result.reason_codes


def test_stale_revocation_requires_security_review_for_install():
    engine = ModuleInstallPolicyEngine()
    revocation = RevocationContext(freshness="stale", metadata_health="healthy", revocations=())
    result = engine.evaluate(
        policy=_policy(),
        publisher=_publisher(),
        revocation=revocation,
        request=_request(action=PolicyAction.INSTALL),
    )
    assert result.decision == PolicyDecision.REQUIRE_SECURITY_REVIEW
    assert PolicyReasonCode.REVOCATION_STALE.value in result.reason_codes


def test_stale_revocation_denies_control_run():
    engine = ModuleInstallPolicyEngine()
    revocation = RevocationContext(freshness="stale", metadata_health="healthy", revocations=())
    result = engine.evaluate(
        policy=_policy(),
        publisher=_publisher(),
        revocation=revocation,
        request=_request(action=PolicyAction.RUN, permissions=("device.control",)),
    )
    assert result.decision == PolicyDecision.DENY
    assert PolicyReasonCode.REVOCATION_STALE.value in result.reason_codes


def test_marketplace_disabled_skips_revocation_trust_checks():
    engine = ModuleInstallPolicyEngine()
    revocation = RevocationContext(freshness="expired", metadata_health="invalid", revocations=())
    result = engine.evaluate(
        policy=_policy(),
        publisher=_publisher(),
        revocation=revocation,
        request=_request(marketplace_metadata_enabled=False),
    )
    assert result.decision == PolicyDecision.ALLOW
