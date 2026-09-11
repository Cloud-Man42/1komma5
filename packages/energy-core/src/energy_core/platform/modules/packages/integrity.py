"""Package integrity verification."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from energy_core.platform.modules.packages.canonical import canonical_manifest_bytes, manifest_sha256
from energy_core.platform.modules.packages.errors import SIGNATURE_INVALID, PackageError
from energy_core.platform.modules.packages.trust_store import PublisherTrustStore
from energy_core.platform.modules.packages.types import SignatureStatus


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _include_in_content_hash(relative_path: str) -> bool:
    if relative_path.startswith("integrity/signature.json"):
        return False
    if relative_path.endswith(".pyc"):
        return False
    if "/__pycache__/" in relative_path or relative_path.startswith("__pycache__/"):
        return False
    return True


def compute_package_content_sha256(archive_path: Path) -> str:
    digest = hashlib.sha256()
    with zipfile.ZipFile(archive_path, "r") as zf:
        for name in sorted(zf.namelist()):
            if name.endswith("/"):
                continue
            if not _include_in_content_hash(name):
                continue
            data = zf.read(name)
            if name == "manifest.json":
                raw = json.loads(data.decode("utf-8"))
                data = canonical_manifest_bytes(raw)
            digest.update(name.encode("utf-8"))
            digest.update(b"\0")
            digest.update(data)
    return digest.hexdigest()


class PackageIntegrityVerifier:
    def __init__(self, *, allow_unsigned: bool, trust_store: PublisherTrustStore | None = None) -> None:
        self._allow_unsigned = allow_unsigned
        self._trust_store = trust_store

    def verify_content_hashes(
        self,
        archive_path: Path,
        manifest_raw: dict,
        *,
        expected_content_sha256: str,
        expected_manifest_sha256: str | None,
    ) -> None:
        actual_content = compute_package_content_sha256(archive_path)
        if actual_content.lower() != expected_content_sha256.lower():
            raise PackageError(
                f"archive checksum mismatch expected={expected_content_sha256} actual={actual_content}",
                code=SIGNATURE_INVALID,
            )
        actual_manifest = manifest_sha256(manifest_raw)
        if expected_manifest_sha256 and actual_manifest.lower() != expected_manifest_sha256.lower():
            raise PackageError(
                f"manifest checksum mismatch expected={expected_manifest_sha256} actual={actual_manifest}",
                code=SIGNATURE_INVALID,
            )

    async def verify_signature(
        self,
        *,
        package_dir: Path,
        manifest_raw: dict,
        archive_path: Path | None = None,
    ) -> SignatureStatus:
        signature_path = package_dir / "integrity" / "signature.json"
        if not signature_path.exists():
            return SignatureStatus.UNSIGNED if self._allow_unsigned else SignatureStatus.MISSING

        payload = json.loads(signature_path.read_text(encoding="utf-8"))
        publisher = str(payload["publisher"])
        key_id = str(payload["key_id"])
        if self._trust_store is None:
            raise PackageError("trust store unavailable", code=SIGNATURE_INVALID)
        public_key = await self._trust_store.assert_trusted(publisher, key_id)
        from energy_core.platform.modules.packages.signing import verify_signature_file

        verify_signature_file(
            package_dir=package_dir,
            manifest_raw=manifest_raw,
            archive_path=archive_path,
            public_key_pem=public_key,
        )
        return SignatureStatus.VALID
