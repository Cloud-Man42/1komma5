"""Generate TEST ONLY TUF metadata fixtures for Step 5C.1 / 5C.1.5 / Sprint B tests.

Run: python generate_fixtures.py
"""

from __future__ import annotations

import datetime
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from securesystemslib.signer import CryptoSigner
from tuf.api.metadata import Metadata, MetaFile, Role, Root, Snapshot, TargetFile, Targets, Timestamp

FIXTURE_DIR = Path(__file__).resolve().parent
METADATA_DIR = FIXTURE_DIR / "repository" / "metadata"
TARGETS_DIR = FIXTURE_DIR / "repository" / "targets" / "emic"
ARTIFACTS_DIR = FIXTURE_DIR / "repository" / "artifacts"
ROLLBACK_DIR = FIXTURE_DIR / "repository" / "rollback_v1" / "metadata"
MODULE_FIXTURE = FIXTURE_DIR.parent / "modules" / "integration.demo-1.0.0.emicpkg"

# TEST ONLY keys — never use in production
ROOT_SIGNER = CryptoSigner.generate_ed25519()
TS_SIGNER = CryptoSigner.generate_ed25519()
SNAP_SIGNER = CryptoSigner.generate_ed25519()
TGT_SIGNER = CryptoSigner.generate_ed25519()

ARTIFACT_SHA256 = hashlib.sha256(MODULE_FIXTURE.read_bytes()).hexdigest()
ARTIFACT_SIZE = MODULE_FIXTURE.stat().st_size
ARTIFACT_NAME = "integration.demo-1.0.0.emicpkg"


@dataclass
class RepoVersion:
    version: int
    catalog: dict
    revocations: dict
    advisories: dict


def _hashed_target_path(path: str, data: bytes) -> str:
    digest = hashlib.sha256(data).hexdigest()
    directory, filename = path.rsplit("/", 1)
    return f"{directory}/{digest}.{filename}"


def _write_target_files(path: str, data: bytes) -> None:
    target_path = TARGETS_DIR.parent / path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(data)
    hashed_path = TARGETS_DIR.parent / _hashed_target_path(path, data)
    hashed_path.parent.mkdir(parents=True, exist_ok=True)
    hashed_path.write_bytes(data)


def _target_file(path: str, data: bytes) -> TargetFile:
    digest = hashlib.sha256(data).hexdigest()
    return TargetFile(path=path, length=len(data), hashes={"sha256": digest})


def _expiry(days: int = 365) -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=days)


def _catalog(version: int, *, artifact_base: str = "http://127.0.0.1:8765/artifacts") -> dict:
    return {
        "snapshot": {"version": version, "generated_at": f"2026-09-0{version}T12:00:00Z"},
        "modules": {
            "integration.demo": {
                "latest_stable": "1.0.0",
                "release_sequence": version,
                "publisher_id": "emic-tests",
                "releases": {
                    "1.0.0": {
                        "release_id": "integration.demo@1.0.0",
                        "publisher_id": "emic-tests",
                        "artifact_url": f"{artifact_base}/{ARTIFACT_NAME}",
                        "content_sha256": ARTIFACT_SHA256,
                        "artifact_size": ARTIFACT_SIZE,
                        "published_at": "2026-09-07T12:00:00Z",
                        "sbom_ref": {"embedded": True},
                    }
                },
            }
        },
    }


def _revocations(generation: int, *, include_revocation: bool = False) -> dict:
    revocations: list[dict] = []
    if include_revocation:
        revocations.append(
            {
                "revocation_id": "rev-demo-001",
                "scope": "module",
                "publisher_id": "emic-tests",
                "module_id": "integration.demo",
                "version": "1.0.0",
                "reason": "test revocation",
                "severity": "high",
                "effective_at": "2026-09-07T12:00:00Z",
                "action": "REVOKE",
            }
        )
    return {
        "bundle": {
            "schema_version": 1,
            "generation": generation,
            "generated_at": f"2026-09-0{generation}T12:00:00Z",
        },
        "revocations": revocations,
    }


def _advisories(generation: int, *, include_critical: bool = False) -> dict:
    entries: list[dict] = []
    if include_critical:
        entries.append(
            {
                "advisory_id": "emic-adv-demo-001",
                "source": "emic-tests",
                "severity": "CRITICAL",
                "published_at": "2026-09-07T12:00:00Z",
                "status": "ACTIVE",
                "affected": {
                    "package": "demo-lib",
                    "version_range": ">=0.0.0",
                },
            }
        )
    return {
        "bundle": {
            "schema_version": 1,
            "generation": generation,
            "generated_at": f"2026-09-0{generation}T12:00:00Z",
        },
        "advisories": entries,
    }


def _write_role_metadata(
    *,
    version: int,
    exp: datetime.datetime,
    catalog_bytes: bytes,
    revoc_bytes: bytes,
    advisory_bytes: bytes,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    targets_signed = Targets(
        version=version,
        expires=exp,
        targets={
            "emic/catalog.json": _target_file("emic/catalog.json", catalog_bytes),
            "emic/revocations.json": _target_file("emic/revocations.json", revoc_bytes),
            "emic/advisories.json": _target_file("emic/advisories.json", advisory_bytes),
        },
    )
    targets_md = Metadata(targets_signed)
    targets_md.sign(TGT_SIGNER)
    targets_path = output_dir / "targets.json"
    targets_md.to_file(str(targets_path))

    targets_data = targets_path.read_bytes()
    targets_hash = hashlib.sha256(targets_data).hexdigest()

    snapshot_signed = Snapshot(
        version=version,
        expires=exp,
        meta={
            "targets.json": MetaFile(
                version=version,
                length=len(targets_data),
                hashes={"sha256": targets_hash},
            )
        },
    )
    snapshot_md = Metadata(snapshot_signed)
    snapshot_md.sign(SNAP_SIGNER)
    snapshot_path = output_dir / "snapshot.json"
    snapshot_md.to_file(str(snapshot_path))

    snapshot_data = snapshot_path.read_bytes()
    snapshot_hash = hashlib.sha256(snapshot_data).hexdigest()

    timestamp_signed = Timestamp(
        version=version,
        expires=exp,
        snapshot_meta=MetaFile(
            version=version,
            length=len(snapshot_data),
            hashes={"sha256": snapshot_hash},
        ),
    )
    timestamp_md = Metadata(timestamp_signed)
    timestamp_md.sign(TS_SIGNER)
    timestamp_path = output_dir / "timestamp.json"
    timestamp_md.to_file(str(timestamp_path))

    targets_md.to_file(str(output_dir / f"{version}.targets.json"))
    snapshot_md.to_file(str(output_dir / f"{version}.snapshot.json"))
    timestamp_md.to_file(str(output_dir / f"{version}.timestamp.json"))


def build_repo() -> None:
    if METADATA_DIR.exists():
        shutil.rmtree(METADATA_DIR.parent)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MODULE_FIXTURE, ARTIFACTS_DIR / ARTIFACT_NAME)
    TARGETS_DIR.mkdir(parents=True, exist_ok=True)
    exp = _expiry()

    v1_catalog = _catalog(1)
    v1_revocations = _revocations(1)
    v1_advisories = _advisories(1)
    v1_catalog_bytes = json.dumps(v1_catalog, sort_keys=True, separators=(",", ":")).encode("utf-8")
    v1_revoc_bytes = json.dumps(v1_revocations, sort_keys=True, separators=(",", ":")).encode("utf-8")
    v1_advisory_bytes = json.dumps(v1_advisories, sort_keys=True, separators=(",", ":")).encode("utf-8")
    _write_target_files("emic/catalog.json", v1_catalog_bytes)
    _write_target_files("emic/revocations.json", v1_revoc_bytes)
    _write_target_files("emic/advisories.json", v1_advisory_bytes)

    root_v1 = Root(
        version=1,
        expires=exp,
        consistent_snapshot=True,
        keys={
            ROOT_SIGNER.public_key.keyid: ROOT_SIGNER.public_key,
            TS_SIGNER.public_key.keyid: TS_SIGNER.public_key,
            SNAP_SIGNER.public_key.keyid: SNAP_SIGNER.public_key,
            TGT_SIGNER.public_key.keyid: TGT_SIGNER.public_key,
        },
        roles={
            "root": Role([ROOT_SIGNER.public_key.keyid], 1),
            "timestamp": Role([TS_SIGNER.public_key.keyid], 1),
            "snapshot": Role([SNAP_SIGNER.public_key.keyid], 1),
            "targets": Role([TGT_SIGNER.public_key.keyid], 1),
        },
    )
    root_md_v1 = Metadata(root_v1)
    root_md_v1.sign(ROOT_SIGNER)
    root_md_v1.to_file(str(METADATA_DIR / "root.json"))
    root_md_v1.to_file(str(METADATA_DIR / "1.root.json"))

    _write_role_metadata(
        version=1,
        exp=exp,
        catalog_bytes=v1_catalog_bytes,
        revoc_bytes=v1_revoc_bytes,
        advisory_bytes=v1_advisory_bytes,
        output_dir=ROLLBACK_DIR,
    )

    v2_catalog = _catalog(2)
    v2_revocations = _revocations(2, include_revocation=True)
    v2_advisories = _advisories(2, include_critical=True)
    v2_catalog_bytes = json.dumps(v2_catalog, sort_keys=True, separators=(",", ":")).encode("utf-8")
    v2_revoc_bytes = json.dumps(v2_revocations, sort_keys=True, separators=(",", ":")).encode("utf-8")
    v2_advisory_bytes = json.dumps(v2_advisories, sort_keys=True, separators=(",", ":")).encode("utf-8")
    _write_target_files("emic/catalog.json", v2_catalog_bytes)
    _write_target_files("emic/revocations.json", v2_revoc_bytes)
    _write_target_files("emic/advisories.json", v2_advisory_bytes)

    _write_role_metadata(
        version=2,
        exp=exp,
        catalog_bytes=v2_catalog_bytes,
        revoc_bytes=v2_revoc_bytes,
        advisory_bytes=v2_advisory_bytes,
        output_dir=METADATA_DIR,
    )

    root_v2 = Root(
        version=2,
        expires=exp,
        consistent_snapshot=True,
        keys={
            ROOT_SIGNER.public_key.keyid: ROOT_SIGNER.public_key,
            TS_SIGNER.public_key.keyid: TS_SIGNER.public_key,
            SNAP_SIGNER.public_key.keyid: SNAP_SIGNER.public_key,
            TGT_SIGNER.public_key.keyid: TGT_SIGNER.public_key,
        },
        roles={
            "root": Role([ROOT_SIGNER.public_key.keyid], 1),
            "timestamp": Role([TS_SIGNER.public_key.keyid], 1),
            "snapshot": Role([SNAP_SIGNER.public_key.keyid], 1),
            "targets": Role([TGT_SIGNER.public_key.keyid], 1),
        },
    )
    root_md_v2 = Metadata(root_v2)
    root_md_v2.sign(ROOT_SIGNER)
    root_md_v2.to_file(str(METADATA_DIR / "2.root.json"))

    pinned = (METADATA_DIR / "root.json").read_bytes()
    (FIXTURE_DIR / "pinned_root.json").write_bytes(pinned)
    (FIXTURE_DIR / "artifact_manifest.json").write_text(
        json.dumps(
            {
                "artifact_name": ARTIFACT_NAME,
                "content_sha256": ARTIFACT_SHA256,
                "artifact_size": ARTIFACT_SIZE,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (FIXTURE_DIR / "TEST_ONLY.txt").write_text(
        "TEST ONLY TUF keys and metadata. Never use in production.\n", encoding="utf-8"
    )


if __name__ == "__main__":
    build_repo()
    print(f"Generated TUF fixtures in {FIXTURE_DIR}")
