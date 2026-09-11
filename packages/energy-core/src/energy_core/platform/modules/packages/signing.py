"""Ed25519 package signing and verification."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from energy_core.platform.modules.packages.canonical import manifest_sha256, signing_digest
from energy_core.platform.modules.packages.errors import SIGNATURE_INVALID, PackageError
from energy_core.platform.modules.packages.integrity import compute_package_content_sha256
from energy_core.platform.modules.packages.types import SignatureStatus


@dataclass(frozen=True, slots=True)
class SignaturePayload:
    algorithm: str
    publisher: str
    key_id: str
    content_sha256: str
    manifest_sha256: str
    signature: str


def _load_signature(path: Path) -> SignaturePayload:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PackageError("invalid signature.json", code=SIGNATURE_INVALID) from exc
    for key in ("algorithm", "publisher", "key_id", "content_sha256", "manifest_sha256", "signature"):
        if key not in raw:
            raise PackageError(f"signature.json missing {key}", code=SIGNATURE_INVALID)
    return SignaturePayload(
        algorithm=str(raw["algorithm"]),
        publisher=str(raw["publisher"]),
        key_id=str(raw["key_id"]),
        content_sha256=str(raw["content_sha256"]).lower(),
        manifest_sha256=str(raw["manifest_sha256"]).lower(),
        signature=str(raw["signature"]),
    )


def verify_signature_file(
    *,
    package_dir: Path,
    manifest_raw: dict[str, Any],
    archive_path: Path | None = None,
    public_key_pem: bytes,
) -> SignatureStatus:
    signature_path = package_dir / "integrity" / "signature.json"
    if not signature_path.exists():
        return SignatureStatus.UNSIGNED

    payload = _load_signature(signature_path)
    if payload.algorithm != "ed25519":
        raise PackageError("unsupported signature algorithm", code=SIGNATURE_INVALID)

    if archive_path is not None:
        content_hash = compute_package_content_sha256(archive_path)
    else:
        content_hash = compute_package_content_sha256_from_dir(package_dir)
    manifest_hash = manifest_sha256(manifest_raw)

    if payload.content_sha256 != content_hash or payload.manifest_sha256 != manifest_hash:
        raise PackageError("signature digest mismatch", code=SIGNATURE_INVALID)

    digest = signing_digest(content_sha256=content_hash, manifest_sha256_hex=manifest_hash)
    try:
        signature_bytes = base64.b64decode(payload.signature)
        public_key = Ed25519PublicKey.from_public_bytes(public_key_pem)
        public_key.verify(signature_bytes, digest)
    except (InvalidSignature, ValueError) as exc:
        raise PackageError("invalid ed25519 signature", code=SIGNATURE_INVALID) from exc
    return SignatureStatus.VALID


def compute_package_content_sha256_from_dir(package_dir: Path) -> str:
    import hashlib
    import zipfile
    import io

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(package_dir.rglob("*")):
            if path.is_file():
                rel = path.relative_to(package_dir).as_posix()
                zf.writestr(rel, path.read_bytes())
    buffer.seek(0)
    tmp = package_dir.parent / ".verify-tmp.zip"
    tmp.write_bytes(buffer.getvalue())
    try:
        return compute_package_content_sha256(tmp)
    finally:
        tmp.unlink(missing_ok=True)


def sign_package_dir(
    *,
    package_dir: Path,
    publisher: str,
    key_id: str,
    private_key_pem: bytes,
) -> None:
    manifest_path = package_dir / "manifest.json"
    manifest_raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    integrity_dir = package_dir / "integrity"
    integrity_dir.mkdir(parents=True, exist_ok=True)

    buffer_zip = _dir_to_zip_bytes(package_dir)
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".emicpkg", delete=False) as handle:
        tmp = Path(handle.name)
        tmp.write_bytes(buffer_zip)
    try:
        content_hash = compute_package_content_sha256(tmp)
    finally:
        tmp.unlink(missing_ok=True)

    manifest_hash = manifest_sha256(manifest_raw)
    digest = signing_digest(content_sha256=content_hash, manifest_sha256_hex=manifest_hash)
    private_key = Ed25519PrivateKey.from_private_bytes(private_key_pem)
    signature = base64.b64encode(private_key.sign(digest)).decode("ascii")

    manifest_raw["integrity"] = {
        "archive_sha256": content_hash,
        "manifest_sha256": manifest_hash,
    }
    manifest_path.write_text(json.dumps(manifest_raw, indent=2), encoding="utf-8")

    signature_payload = {
        "algorithm": "ed25519",
        "publisher": publisher,
        "key_id": key_id,
        "content_sha256": content_hash,
        "manifest_sha256": manifest_hash,
        "signature": signature,
    }
    (integrity_dir / "signature.json").write_text(json.dumps(signature_payload, indent=2), encoding="utf-8")


def _dir_to_zip_bytes(package_dir: Path) -> bytes:
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(package_dir.rglob("*")):
            if path.is_file() and path.name != "signature.json":
                rel = path.relative_to(package_dir).as_posix()
                if rel.startswith("integrity/signature"):
                    continue
                zf.writestr(rel, path.read_bytes())
    return buffer.getvalue()


def generate_ed25519_keypair() -> tuple[bytes, bytes]:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key.private_bytes_raw(), public_key.public_bytes_raw()
