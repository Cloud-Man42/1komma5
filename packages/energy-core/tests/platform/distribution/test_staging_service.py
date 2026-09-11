"""Artifact staging integration tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

pytestmark = pytest.mark.integration

from energy_core.db.models.marketplace_trust_cache import MarketplaceTrustCacheModel
from energy_core.db.models.module_publisher import ModulePublisherModel
from energy_core.platform.modules.distribution.staging_service import ArtifactStagingService
from energy_core.platform.modules.distribution.types import ArtifactState, DistributionError, DistributionErrorCode
from energy_core.platform.modules.governance.types import PublisherStatus, PublisherTier

FIXTURE_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2] / "fixtures" / "marketplace_tuf"
ARTIFACT_MANIFEST = json.loads((FIXTURE_ROOT / "artifact_manifest.json").read_text(encoding="utf-8"))


async def _seed_trusted_catalog(session, *, artifact_base: str) -> MarketplaceTrustCacheModel:
    catalog = {
        "snapshot": {"version": 2, "generated_at": "2026-09-07T12:00:00Z"},
        "modules": {
            "integration.demo": {
                "publisher_id": "emic-tests",
                "releases": {
                    "1.0.0": {
                        "release_id": "integration.demo@1.0.0",
                        "publisher_id": "emic-tests",
                        "artifact_url": f"{artifact_base}/{ARTIFACT_MANIFEST['artifact_name']}",
                        "content_sha256": ARTIFACT_MANIFEST["content_sha256"],
                        "artifact_size": ARTIFACT_MANIFEST["artifact_size"],
                        "sbom_ref": {"embedded": True},
                    }
                },
            }
        },
    }
    row = MarketplaceTrustCacheModel(
        cache_key="default",
        enabled=True,
        cache_state="healthy",
        revocation_state="fresh",
        cache_generation=1,
        root_version=2,
        timestamp_version=2,
        snapshot_version=2,
        targets_version=2,
        catalog_json=json.dumps(catalog, sort_keys=True),
        revocations_json=json.dumps(
            {"bundle": {"schema_version": 1, "generation": 1, "generated_at": "2026-09-07T12:00:00Z"}, "revocations": []},
            sort_keys=True,
        ),
        advisories_json=json.dumps({"bundle": {"generation": 1, "generated_at": "2026-09-07T12:00:00Z"}, "advisories": []}),
        revocation_generation=1,
        last_success_at=datetime.now(UTC),
    )
    session.add(row)
    session.add(
        ModulePublisherModel(
            publisher_id="emic-tests",
            display_name="EMIC Tests",
            tier=PublisherTier.ORG_APPROVED.value,
            status=PublisherStatus.ACTIVE.value,
        )
    )
    await session.flush()
    return row


@pytest.mark.asyncio
async def test_fetch_release_stages_valid_artifact(distribution_session, artifact_server):
    session, settings, _ = distribution_session
    await _seed_trusted_catalog(session, artifact_base=artifact_server)
    await session.commit()

    result = await ArtifactStagingService(session, settings).fetch_release("integration.demo", "1.0.0")
    assert result.state == ArtifactState.STAGED
    assert result.artifact_id > 0


@pytest.mark.asyncio
async def test_fetch_unknown_version_rejected(distribution_session, artifact_server):
    session, settings, _ = distribution_session
    await _seed_trusted_catalog(session, artifact_base=artifact_server)
    await session.commit()

    with pytest.raises(DistributionError) as exc:
        await ArtifactStagingService(session, settings).fetch_release("integration.demo", "9.9.9")
    assert exc.value.code == DistributionErrorCode.CATALOG_ENTRY_NOT_FOUND


@pytest.mark.asyncio
async def test_digest_mismatch_rejects(distribution_session, artifact_server):
    session, settings, _ = distribution_session
    row = await _seed_trusted_catalog(session, artifact_base=artifact_server)
    catalog = json.loads(row.catalog_json)
    catalog["modules"]["integration.demo"]["releases"]["1.0.0"]["content_sha256"] = "0" * 64
    row.catalog_json = json.dumps(catalog, sort_keys=True)
    await session.commit()

    with pytest.raises(DistributionError) as exc:
        await ArtifactStagingService(session, settings).fetch_release("integration.demo", "1.0.0")
    assert exc.value.code == DistributionErrorCode.ARTIFACT_DIGEST_MISMATCH
