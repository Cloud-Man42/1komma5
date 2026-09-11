"""Sign integration.demo packages for prod acceptance (private key stays outside repo)."""

from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from energy_core.platform.modules.packages.signing import generate_ed25519_keypair, sign_package_dir

FIXTURES = Path(__file__).resolve().parents[1] / "packages" / "energy-core" / "tests" / "fixtures" / "modules"


def sign_fixture(version: str, publisher: str, key_id: str, private_key: bytes, out_dir: Path) -> Path:
    archive = FIXTURES / f"integration.demo-{version}.emicpkg"
    extract_dir = out_dir / f"extract-{version}"
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "r") as zf:
        zf.extractall(extract_dir)
    manifest_path = extract_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["publisher"] = publisher
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    sign_package_dir(
        package_dir=extract_dir,
        publisher=publisher,
        key_id=key_id,
        private_key_pem=private_key,
    )
    signed = out_dir / f"integration.demo-{version}.signed.emicpkg"
    with zipfile.ZipFile(signed, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in extract_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(extract_dir).as_posix())
    return signed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--publisher-id", default="emic-internal-test")
    parser.add_argument("--key-id", default="test-2026-01")
    parser.add_argument("--versions", nargs="+", default=["1.0.0", "1.1.0"])
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    private_key, public_key = generate_ed25519_keypair()
    out_dir = args.output_dir or Path(tempfile.mkdtemp(prefix="emic-signed-demo-"))
    out_dir.mkdir(parents=True, exist_ok=True)
    packages: dict[str, str] = {}
    for version in args.versions:
        signed = sign_fixture(version, args.publisher_id, args.key_id, private_key, out_dir)
        packages[version] = signed.name
    manifest = {
        "publisher_id": args.publisher_id,
        "key_id": args.key_id,
        "public_key_hex": public_key.hex(),
        "packages": packages,
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    key_file = out_dir / "signing-keypair.json"
    key_file.write_text(
        json.dumps(
            {
                "publisher_id": args.publisher_id,
                "key_id": args.key_id,
                "public_key_hex": public_key.hex(),
                "private_key_hex": private_key.hex(),
                "note": "TEST ONLY - delete after prod acceptance",
            }
        ),
        encoding="utf-8",
    )
    print(str(manifest_path))
    print(str(key_file))


if __name__ == "__main__":
    main()
