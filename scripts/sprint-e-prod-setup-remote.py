"""Seed integration.sensibo on production marketplace trust cache (Sprint E.5)."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
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
PKG_NAME = "integration.sensibo-1.0.0.emicpkg"
SIGNING_INFO = Path("/app/packages/energy-core/tests/fixtures/modules/integration.sensibo-signing.json")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixture-base-url",
        required=True,
        help="Internal fixture base URL (e.g. http://caddy:8080)",
    )
    parser.add_argument(
        "--package-path",
        default=str(FIXTURE_DIR / PKG_NAME),
        help="Path to signed integration.sensibo .emicpkg inside backend container",
    )
    args = parser.parse_args()

    pkg_path = Path(args.package_path)
    if not pkg_path.is_file():
        raise SystemExit(f"Sensibo package missing: {pkg_path}")

    from energy_core.platform.modules.packages.integrity import compute_package_content_sha256

    data = pkg_path.read_bytes()
    digest = compute_package_content_sha256(pkg_path)
    artifact_url = f"{args.fixture_base_url.rstrip('/')}/{PKG_NAME}"

    publisher_id = "emic-official"
    key_id = "sensibo-2026-09"
    public_key_hex = ""
    for candidate in (
        Path("/app/scripts/integration.sensibo-signing.json"),
        SIGNING_INFO,
        Path(__file__).resolve().parent / "integration.sensibo-signing.json",
    ):
        if candidate.is_file():
            info = json.loads(candidate.read_text(encoding="utf-8"))
            publisher_id = str(info.get("publisher_id") or publisher_id)
            key_id = str(info.get("key_id") or key_id)
            public_key_hex = str(info.get("public_key_hex") or public_key_hex)
            break

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
                    display_name="EMIC Official",
                    tier=PublisherTier.OFFICIAL.value,
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

        row = await session.scalar(
            select(MarketplaceTrustCacheModel).where(MarketplaceTrustCacheModel.cache_key == "default")
        )
        if row is None:
            row = MarketplaceTrustCacheModel(cache_key="default")
            session.add(row)

        catalog: dict = {"snapshot": {"version": 100, "generated_at": datetime.now(UTC).isoformat()}, "modules": {}}
        if row.catalog_json:
            try:
                existing = json.loads(row.catalog_json)
                if isinstance(existing, dict):
                    catalog = existing
                    if not isinstance(catalog.get("modules"), dict):
                        catalog["modules"] = {}
            except json.JSONDecodeError:
                pass

        catalog["artifact_source"] = catalog.get("artifact_source") or "INTERNAL"
        catalog.setdefault("snapshot", {})
        catalog["snapshot"]["version"] = int(catalog["snapshot"].get("version") or 100) + 1
        catalog["snapshot"]["generated_at"] = datetime.now(UTC).isoformat()

        catalog["modules"]["integration.sensibo"] = {
            "display_name": "Sensibo Climate",
            "description": "Read-only Sensibo climate monitoring via isolated runtime",
            "publisher_id": publisher_id,
            "device_categories": ["climate"],
            "capabilities": [
                "hvac.read_temperature",
                "hvac.read_humidity",
                "hvac.read_state",
                "hvac.read_target_temperature",
                "hvac.read_status",
            ],
            "permissions": ["network.external", "secrets.read_own", "device.read"],
            "latest_stable": "1.0.0",
            "releases": {
                "1.0.0": {
                    "release_id": "integration.sensibo@1.0.0",
                    "publisher_id": publisher_id,
                    "artifact_url": artifact_url,
                    "content_sha256": digest,
                    "artifact_size": len(data),
                    "published_at": datetime.now(UTC).isoformat(),
                    "channel": "stable",
                    "sbom_ref": {"embedded": True},
                }
            },
        }

        row.enabled = True
        row.catalog_json = json.dumps(catalog, sort_keys=True)
        if not row.advisories_json:
            row.advisories_json = json.dumps({"bundle": {"generation": 1}, "advisories": []}, sort_keys=True)
        if not row.revocations_json:
            row.revocations_json = json.dumps({"bundle": {"generation": 1}, "revocations": []}, sort_keys=True)
        now = datetime.now(UTC)
        row.cache_state = "healthy"
        row.revocation_state = "fresh"
        row.sync_failed = False
        row.last_error = None
        row.last_success_at = now
        row.catalog_updated_at = now
        row.metadata_expires_at = now + timedelta(days=1)
        await session.commit()

    await engine.dispose()
    print(
        json.dumps(
            {
                "module_id": "integration.sensibo",
                "version": "1.0.0",
                "publisher_id": publisher_id,
                "artifact_url": artifact_url,
                "digest": digest,
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
