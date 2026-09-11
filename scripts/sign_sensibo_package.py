"""Sign integration.sensibo fixture package for Store/trust tests."""

from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from energy_core.platform.modules.packages.signing import generate_ed25519_keypair, sign_package_dir

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "packages" / "energy-core" / "tests" / "fixtures" / "modules" / "integration.sensibo-1.0.0.emicpkg"


def main() -> None:
    key_info_path = ROOT / "scripts" / "integration.sensibo-signing.json"
    if key_info_path.exists():
        existing = json.loads(key_info_path.read_text(encoding="utf-8"))
        private_key = bytes.fromhex(str(existing["private_key_hex"]))
        public_key = bytes.fromhex(str(existing["public_key_hex"]))
    else:
        private_key, public_key = generate_ed25519_keypair()
    with tempfile.TemporaryDirectory(prefix="emic-sensibo-sign-") as tmp:
        extract = Path(tmp) / "pkg"
        extract.mkdir()
        with zipfile.ZipFile(ARCHIVE, "r") as zf:
            zf.extractall(extract)
        sign_package_dir(
            package_dir=extract,
            publisher="emic-official",
            key_id="sensibo-2026-09",
            private_key_pem=private_key,
        )
        backup = ARCHIVE.with_suffix(".emicpkg.unsigned.bak")
        if not backup.exists():
            shutil.copy2(ARCHIVE, backup)
        with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in extract.rglob("*"):
                if path.is_file():
                    zf.write(path, path.relative_to(extract).as_posix())
    key_info = ROOT / "packages" / "energy-core" / "tests" / "fixtures" / "modules" / "integration.sensibo-signing.json"
    key_info.write_text(
        json.dumps(
            {
                "publisher_id": "emic-official",
                "key_id": "sensibo-2026-09",
                "public_key_hex": public_key.hex(),
                "private_key_hex": private_key.hex(),
                "note": "TEST FIXTURE ONLY",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(ARCHIVE)
    print(key_info)


if __name__ == "__main__":
    main()
