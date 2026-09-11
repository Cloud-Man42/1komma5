"""Advisory bundle policy tests."""

from __future__ import annotations

import pytest

from energy_core.platform.modules.marketplace.types import MetadataErrorCode
from energy_core.platform.modules.supply_chain.advisory_policy import (
    AdvisoryPolicyError,
    parse_advisory_bundle,
    validate_advisory_monotonicity,
)


def _bundle(generation: int, *, advisories: list | None = None) -> dict:
    entries = [{"advisory_id": "a1", "severity": "LOW", "status": "ACTIVE"}] if advisories is None else advisories
    return {
        "bundle": {"generation": generation, "generated_at": "2026-09-07T12:00:00Z"},
        "advisories": entries,
    }


def test_parse_advisory_bundle():
    bundle = parse_advisory_bundle(_bundle(1))
    assert bundle.generation == 1
    assert len(bundle.advisories) == 1


def test_advisory_rollback_rejected():
    incoming = parse_advisory_bundle(_bundle(1))
    with pytest.raises(AdvisoryPolicyError) as exc:
        validate_advisory_monotonicity(trusted_generation=2, trusted_hash=None, incoming=incoming)
    assert exc.value.error_code == MetadataErrorCode.METADATA_ROLLBACK_DETECTED


def test_advisory_wipe_rejected():
    incoming = parse_advisory_bundle(_bundle(3, advisories=[]))
    with pytest.raises(AdvisoryPolicyError):
        validate_advisory_monotonicity(trusted_generation=2, trusted_hash=None, incoming=incoming)
