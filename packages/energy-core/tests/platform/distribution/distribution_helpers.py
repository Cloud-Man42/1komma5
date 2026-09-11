"""Helpers for distribution security matrix tests."""

from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models.marketplace_trust_cache import MarketplaceTrustCacheModel
from energy_core.db.models.module_publisher import ModulePublisherModel
from energy_core.platform.modules.governance.types import PublisherStatus, PublisherTier
from energy_core.platform.modules.packages.canonical import canonical_manifest_bytes, manifest_sha256
from energy_core.platform.modules.packages.signing import sign_package_dir

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "marketplace_tuf"
ARTIFACT_MANIFEST = json.loads((FIXTURE_ROOT / "artifact_manifest.json").read_text(encoding="utf-8"))
FIXTURE_MODULE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "modules" / "integration.demo"


async def seed_trusted_catalog(
    session: AsyncSession,
    *,
    artifact_base: str,
    advisories: dict | None = None,
    catalog_overrides: dict | None = None,
    publisher_id: str = "emic-tests",
    publisher_tier: str = PublisherTier.ORG_APPROVED.value,
    publisher_status: str = PublisherStatus.ACTIVE.value,
    artifact_name: str | None = None,
    content_sha256: str | None = None,
    artifact_size: int | None = None,
) -> MarketplaceTrustCacheModel:
    name = artifact_name or ARTIFACT_MANIFEST["artifact_name"]
    digest = content_sha256 or ARTIFACT_MANIFEST["content_sha256"]
    size = artifact_size if artifact_size is not None else ARTIFACT_MANIFEST["artifact_size"]
    catalog = catalog_overrides or {
        "snapshot": {"version": 2, "generated_at": "2026-09-07T12:00:00Z"},
        "modules": {
            "integration.demo": {
                "publisher_id": publisher_id,
                "releases": {
                    "1.0.0": {
                        "release_id": "integration.demo@1.0.0",
                        "publisher_id": publisher_id,
                        "artifact_url": f"{artifact_base}/{name}",
                        "content_sha256": digest,
                        "artifact_size": size,
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
            {
                "bundle": {"schema_version": 1, "generation": 1, "generated_at": "2026-09-07T12:00:00Z"},
                "revocations": [],
            },
            sort_keys=True,
        ),
        advisories_json=json.dumps(
            advisories or {"bundle": {"generation": 1, "generated_at": "2026-09-07T12:00:00Z"}, "advisories": []}
        ),
        revocation_generation=1,
        last_success_at=datetime.now(UTC),
    )
    session.add(row)
    session.add(
        ModulePublisherModel(
            publisher_id=publisher_id,
            display_name=publisher_id,
            tier=publisher_tier,
            status=publisher_status,
        )
    )
    await session.flush()
    return row
BASE_MANIFEST = {
    "module_id": "integration.demo",
    "name": "Integration Demo",
    "version": "1.0.0",
    "module_type": "integration",
    "description": "Distribution test package",
    "publisher": "emic-tests",
    "entrypoint": "demo:build_module",
    "module_api_version": 1,
    "minimum_emic_version": "0.1.0",
    "provided_capabilities": ["read_status"],
    "required_capabilities": [],
    "optional_capabilities": [],
    "module_dependencies": [],
    "configuration_schema": {
        "fields": [
            {"name": "label", "label": "Label", "type": "string", "default": "demo"},
            {"name": "fail_health", "label": "Fail health", "type": "boolean", "default": False},
        ]
    },
    "permissions": ["device.read"],
    "supports_per_site_activation": True,
    "requires_restart_on_update": True,
    "can_disable": True,
    "onboardable": False,
}


def _content_hash(build_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(build_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(build_dir).as_posix()
        if rel == "manifest.json":
            raw = json.loads(path.read_text(encoding="utf-8"))
            data = canonical_manifest_bytes(raw)
        else:
            data = path.read_bytes()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(data)
    return digest.hexdigest()


def build_emicpkg(
    dest: Path,
    *,
    manifest_overrides: dict | None = None,
    extra_files: dict[str, bytes] | None = None,
    private_key: bytes | None = None,
    key_id: str = "test-1",
) -> tuple[str, int]:
    """Build .emicpkg at dest; return (sha256, size)."""
    build_dir = dest.parent / f".build-{dest.stem}"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    shutil.copytree(FIXTURE_MODULE_ROOT / "module", build_dir / "module")
    schemas_dir = build_dir / "schemas"
    schemas_dir.mkdir(parents=True)
    manifest = {**BASE_MANIFEST, **(manifest_overrides or {})}
    (schemas_dir / "configuration.schema.json").write_text(
        json.dumps(manifest["configuration_schema"], indent=2),
        encoding="utf-8",
    )
    (build_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if extra_files:
        for name, data in extra_files.items():
            path = build_dir / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    content_hash = _content_hash(build_dir)
    manifest_hash = manifest_sha256(manifest)
    manifest["integrity"] = {"archive_sha256": content_hash, "manifest_sha256": manifest_hash}
    (build_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if private_key is not None:
        sign_package_dir(
            package_dir=build_dir,
            publisher=manifest["publisher"],
            key_id=key_id,
            private_key_pem=private_key,
        )
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in build_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(build_dir).as_posix())
    shutil.rmtree(build_dir)
    data = dest.read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data)


def cyclonedx_sbom(*, name: str = "demo-lib", version: str = "1.0.0", purl: str | None = None) -> bytes:
    doc = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "components": [
            {
                "name": name,
                "version": version,
                "purl": purl or f"pkg:generic/{name}@{version}",
            }
        ],
    }
    return json.dumps(doc, sort_keys=True).encode("utf-8")


def critical_advisories_bundle(*, purl: str = "pkg:generic/demo-lib@1.0.0") -> dict:
    return {
        "bundle": {"generation": 2, "generated_at": "2026-09-08T12:00:00Z"},
        "advisories": [
            {
                "advisory_id": "emic-adv-critical-001",
                "severity": "CRITICAL",
                "status": "ACTIVE",
                "affected": {"purl": purl, "version_range": ">=1.0.0"},
            }
        ],
    }


def high_advisories_bundle(*, purl: str = "pkg:generic/demo-lib@1.0.0") -> dict:
    return {
        "bundle": {"generation": 2, "generated_at": "2026-09-08T12:00:00Z"},
        "advisories": [
            {
                "advisory_id": "emic-adv-high-001",
                "severity": "HIGH",
                "status": "ACTIVE",
                "affected": {"purl": purl, "version_range": ">=1.0.0"},
            }
        ],
    }
