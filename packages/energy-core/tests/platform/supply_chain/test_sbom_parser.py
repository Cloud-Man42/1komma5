"""SBOM parser tests."""

from __future__ import annotations

import json

import pytest

from energy_core.platform.modules.supply_chain.sbom_parser import parse_sbom
from energy_core.platform.modules.supply_chain.types import SupplyChainError, SupplyChainErrorCode


def test_parse_cyclonedx_sbom():
    raw = json.dumps(
        {
            "bomFormat": "CycloneDX",
            "specVersion": "1.5",
            "components": [{"name": "demo-lib", "version": "1.0.0", "purl": "pkg:generic/demo-lib@1.0.0"}],
        }
    ).encode()
    parsed = parse_sbom(raw)
    assert parsed.format == "CycloneDX"
    assert parsed.components[0].name == "demo-lib"


def test_rejects_oversized_sbom():
    with pytest.raises(SupplyChainError) as exc:
        parse_sbom(b"x" * (5_242_881))
    assert exc.value.code == SupplyChainErrorCode.SBOM_INVALID


def test_digest_mismatch():
    raw = json.dumps({"bomFormat": "CycloneDX", "specVersion": "1.5", "components": []}).encode()
    with pytest.raises(SupplyChainError) as exc:
        parse_sbom(raw, expected_digest="0" * 64)
    assert exc.value.code == SupplyChainErrorCode.SBOM_DIGEST_MISMATCH
