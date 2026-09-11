"""Advisory withdrawal semantics (Sprint B.5 / Sprint C R-3)."""

from __future__ import annotations

import pytest

from energy_core.platform.modules.supply_chain.advisory_policy import (
    merge_advisory_bundles,
    parse_advisory_bundle,
)
from energy_core.platform.modules.supply_chain.types import SecuritySeverity
from energy_core.platform.modules.supply_chain.vulnerability_matcher import match_vulnerabilities
from energy_core.platform.modules.supply_chain.types import AdvisoryEntry, SbomComponent


def test_withdrawn_advisory_does_not_match():
    bundle = parse_advisory_bundle(
        {
            "bundle": {"generation": 2, "generated_at": "2026-09-08T12:00:00Z"},
            "advisories": [
                {
                    "advisory_id": "adv-w1",
                    "severity": "CRITICAL",
                    "status": "WITHDRAWN",
                    "withdrawn": True,
                    "affected": {"purl": "pkg:generic/demo-lib@1.0.0", "version_range": ">=1.0.0"},
                }
            ],
        }
    )
    components = (SbomComponent(name="demo-lib", version="1.0.0", purl="pkg:generic/demo-lib@1.0.0"),)
    matches = match_vulnerabilities(components, bundle.advisories)
    assert matches == ()


def test_merge_keeps_prior_advisory_when_missing_from_new_bundle():
    trusted = {
        "bundle": {"generation": 2, "generated_at": "2026-09-07T12:00:00Z"},
        "advisories": [
            {
                "advisory_id": "adv-a1",
                "severity": "HIGH",
                "status": "ACTIVE",
                "affected": {"purl": "pkg:generic/demo-lib@1.0.0", "version_range": ">=1.0.0"},
            }
        ],
    }
    incoming = parse_advisory_bundle(
        {
            "bundle": {"generation": 3, "generated_at": "2026-09-08T12:00:00Z"},
            "advisories": [
                {
                    "advisory_id": "adv-a2",
                    "severity": "LOW",
                    "status": "ACTIVE",
                    "affected": {"purl": "pkg:generic/other@1.0.0", "version_range": ">=1.0.0"},
                }
            ],
        }
    )
    merged = merge_advisory_bundles(trusted_raw=trusted, incoming=incoming, incoming_raw=trusted)
    ids = {item["advisory_id"] for item in merged["advisories"]}
    assert "adv-a1" in ids
    assert "adv-a2" in ids


def test_fixed_version_not_treated_as_vulnerable():
    adv = AdvisoryEntry(
        advisory_id="adv-f1",
        source="emic",
        severity=SecuritySeverity.HIGH,
        published_at=None,
        updated_at=None,
        status="ACTIVE",
        affected_purl="pkg:generic/demo-lib@2.0.0",
        affected_package=None,
        affected_version_range=">=1.0.0",
        fixed_versions=("2.0.0",),
    )
    components = (SbomComponent(name="demo-lib", version="2.0.0", purl="pkg:generic/demo-lib@2.0.0"),)
    matches = match_vulnerabilities(components, (adv,))
    assert matches == ()
