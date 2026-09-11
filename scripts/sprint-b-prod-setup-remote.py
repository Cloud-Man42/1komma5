"""Seed controlled Sprint B marketplace fixtures on production (acceptance only)."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from energy_core.config import get_settings
from energy_core.db.models.marketplace_trust_cache import MarketplaceTrustCacheModel
from energy_core.db.models.module_publisher import ModulePublisherModel
from energy_core.db.models.module_publisher_key import ModulePublisherKeyModel
from energy_core.db.session import create_engine, create_session_factory
from energy_core.platform.modules.governance.types import PublisherStatus, PublisherTier
from energy_core.platform.modules.packages.trust_store import PublisherKeyStatus

FIXTURE_DIR = Path("/app/sprint-b-fixtures")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(FIXTURE_DIR / "manifest.json"))
    parser.add_argument(
        "--fixture-base-url",
        required=True,
        help="HTTPS base for sprint-b-fixtures (e.g. https://emic.inacloud.se/sprint-b-fixtures)",
    )
    parser.add_argument(
        "--scenario",
        choices=("valid", "community", "critical"),
        default="valid",
        help="Catalog/advisory scenario for acceptance",
    )
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    publisher_id = manifest["publisher_id"]
    key_id = manifest["key_id"]
    public_key_hex = manifest["public_key_hex"]
    version = "1.0.0"
    pkg_name = os.path.basename(manifest["packages"][version])
    pkg_path = FIXTURE_DIR / pkg_name
    if not pkg_path.is_file():
        raise SystemExit(f"Fixture package missing: {pkg_path}")
    data = pkg_path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    size = len(data)
    artifact_url = f"{args.fixture_base_url.rstrip('/')}/{pkg_name}"

    catalog_publisher = publisher_id
    advisories: dict = {"bundle": {"generation": 99}, "advisories": []}
    revocation_entries: list[dict] = []
    if args.scenario == "community":
        catalog_publisher = "sprint-b-community"
    elif args.scenario == "critical":
        advisories = {
            "bundle": {"generation": 99, "generated_at": datetime.now(UTC).isoformat()},
            "advisories": [
                {
                    "advisory_id": "sprint-b-critical-prod",
                    "severity": "CRITICAL",
                    "status": "ACTIVE",
                    "affected": {"purl": "pkg:generic/demo-lib@1.0.0", "version_range": ">=1.0.0"},
                }
            ],
        }
        revocation_entries = [
            {
                "revocation_id": "sprint-b-critical-revocation",
                "action": "REVOKE",
                "severity": "CRITICAL",
                "scope": "publisher",
                "publisher_id": publisher_id,
            }
        ]

    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        if await session.scalar(
            select(ModulePublisherModel).where(ModulePublisherModel.publisher_id == publisher_id)
        ) is None:
            session.add(
                ModulePublisherModel(
                    publisher_id=publisher_id,
                    display_name="Sprint B Acceptance",
                    tier=PublisherTier.ORG_APPROVED.value,
                    status=PublisherStatus.ACTIVE.value,
                )
            )
        key = await session.scalar(
            select(ModulePublisherKeyModel).where(
                ModulePublisherKeyModel.publisher_id == publisher_id,
                ModulePublisherKeyModel.key_id == key_id,
            )
        )
        if key is None:
            session.add(
                ModulePublisherKeyModel(
                    publisher_id=publisher_id,
                    key_id=key_id,
                    public_key_hex=public_key_hex,
                    status=PublisherKeyStatus.TRUSTED.value,
                )
            )
        else:
            key.public_key_hex = public_key_hex
            key.status = PublisherKeyStatus.TRUSTED.value

        if await session.scalar(
            select(ModulePublisherModel).where(ModulePublisherModel.publisher_id == "sprint-b-community")
        ) is None:
            session.add(
                ModulePublisherModel(
                    publisher_id="sprint-b-community",
                    display_name="Sprint B Community",
                    tier=PublisherTier.COMMUNITY.value,
                    status=PublisherStatus.ACTIVE.value,
                )
            )

        catalog = {
            "artifact_source": "INTERNAL",
            "snapshot": {"version": 99, "generated_at": datetime.now(UTC).isoformat()},
            "modules": {
                "integration.demo": {
                    "publisher_id": catalog_publisher,
                    "releases": {
                        version: {
                            "release_id": f"integration.demo@{version}",
                            "publisher_id": catalog_publisher,
                            "artifact_url": artifact_url,
                            "content_sha256": digest,
                            "artifact_size": size,
                            "sbom_ref": {"embedded": args.scenario == "critical"},
                        }
                    },
                }
            },
        }
        row = await session.scalar(
            select(MarketplaceTrustCacheModel).where(MarketplaceTrustCacheModel.cache_key == "default")
        )
        if row is None:
            row = MarketplaceTrustCacheModel(cache_key="default")
            session.add(row)
        row.enabled = True
        row.catalog_json = json.dumps(catalog, sort_keys=True)
        row.advisories_json = json.dumps(advisories, sort_keys=True)
        now = datetime.now(UTC)
        revocations = {
            "bundle": {
                "schema_version": 1,
                "generation": 1,
                "generated_at": now.isoformat(),
            },
            "revocations": revocation_entries,
        }
        row.revocations_json = json.dumps(revocations, sort_keys=True)
        row.root_version = 2
        row.timestamp_version = 2
        row.snapshot_version = 2
        row.targets_version = 2
        row.cache_generation = 1
        row.revocation_generation = 1
        row.cache_state = "healthy"
        row.revocation_state = "fresh"
        row.sync_failed = False
        row.last_error = None
        row.last_success_at = now
        row.catalog_updated_at = now
        row.revocation_updated_at = now
        row.metadata_expires_at = now + timedelta(days=1)
        await session.commit()

    await engine.dispose()
    print(json.dumps({"artifact_url": artifact_url, "digest": digest, "publisher_id": publisher_id, "scenario": args.scenario}))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
