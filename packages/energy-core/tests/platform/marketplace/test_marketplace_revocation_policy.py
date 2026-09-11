"""Revocation policy unit tests."""

from __future__ import annotations

import pytest

from energy_core.platform.modules.marketplace.revocation_policy import (
    RevocationPolicyError,
    merge_revocation_bundles,
    parse_revocation_bundle,
    validate_revocation_monotonicity,
)
from energy_core.platform.modules.marketplace.types import MetadataErrorCode


def test_parse_revocation_bundle_requires_generation():
    with pytest.raises(RevocationPolicyError):
        parse_revocation_bundle({"bundle": {}, "revocations": []})


def test_generation_rollback_rejected():
    bundle = parse_revocation_bundle(
        {
            "bundle": {"schema_version": 1, "generation": 1, "generated_at": "2026-09-07T12:00:00Z"},
            "revocations": [],
        }
    )
    with pytest.raises(RevocationPolicyError) as exc:
        validate_revocation_monotonicity(trusted_generation=2, trusted_hash="abc", incoming=bundle)
    assert exc.value.error_code == MetadataErrorCode.METADATA_ROLLBACK_DETECTED


def test_merge_keeps_prior_revocation_when_missing_from_new_bundle():
    trusted = {
        "bundle": {"schema_version": 1, "generation": 2, "generated_at": "2026-09-07T12:00:00Z"},
        "revocations": [{"revocation_id": "r1", "scope": "module", "action": "REVOKE"}],
    }
    incoming = parse_revocation_bundle(
        {
            "bundle": {"schema_version": 1, "generation": 3, "generated_at": "2026-09-08T12:00:00Z"},
            "revocations": [],
        }
    )
    merged = merge_revocation_bundles(trusted_raw=trusted, incoming=incoming, incoming_raw=trusted)
    ids = {item["revocation_id"] for item in merged["revocations"]}
    assert "r1" in ids


def test_supersede_removes_revocation():
    trusted = {
        "bundle": {"schema_version": 1, "generation": 2, "generated_at": "2026-09-07T12:00:00Z"},
        "revocations": [{"revocation_id": "r1", "scope": "module", "action": "REVOKE"}],
    }
    incoming = parse_revocation_bundle(
        {
            "bundle": {"schema_version": 1, "generation": 3, "generated_at": "2026-09-08T12:00:00Z"},
            "revocations": [
                {
                    "revocation_id": "r2",
                    "scope": "module",
                    "action": "SUPERSEDE",
                    "supersedes_revocation_id": "r1",
                }
            ],
        }
    )
    merged = merge_revocation_bundles(
        trusted_raw=trusted,
        incoming=incoming,
        incoming_raw={
            "bundle": {"schema_version": 1, "generation": 3, "generated_at": "2026-09-08T12:00:00Z"},
            "revocations": [
                {
                    "revocation_id": "r2",
                    "scope": "module",
                    "action": "SUPERSEDE",
                    "supersedes_revocation_id": "r1",
                }
            ],
        },
    )
    ids = {item["revocation_id"] for item in merged["revocations"]}
    assert "r1" not in ids
