"""Build integration.sandbox-demo package fixture."""

from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from energy_core.platform.modules.packages.canonical import canonical_manifest_bytes, manifest_sha256

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent


def _manifest(version: str = "1.0.0") -> dict:
    return {
        "module_id": "integration.runtime-e2e",
        "name": "Runtime E2E",
        "version": version,
        "module_type": "integration",
        "description": "Benign isolated runtime demo module",
        "publisher": "emic-tests",
        "entrypoint": "sandbox_demo:build_module",
        "module_api_version": 1,
        "minimum_emic_version": "0.1.0",
        "provided_capabilities": ["read_status"],
        "required_capabilities": [],
        "optional_capabilities": [],
        "module_dependencies": [],
        "configuration_schema": {"fields": []},
        "permissions": ["device.read", "device.control", "secrets.read_own", "network.external"],
        "supports_per_site_activation": True,
        "requires_restart_on_update": False,
        "can_disable": True,
        "onboardable": False,
        "test_site_id": 1,
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


def build(version: str = "1.0.0") -> Path:
    build_dir = ROOT / ".build" / version
    if build_dir.exists():
        shutil.rmtree(build_dir)
    shutil.copytree(ROOT / "module", build_dir / "module")
    manifest = _manifest(version)
    (build_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    content_hash = _content_hash(build_dir)
    manifest_hash = manifest_sha256(manifest)
    manifest["integrity"] = {
        "archive_sha256": content_hash,
        "manifest_sha256": manifest_hash,
    }
    (build_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    archive = OUT / f"integration.runtime-e2e-{version}.emicpkg"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in build_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(build_dir).as_posix())
    shutil.rmtree(build_dir)
    return archive


if __name__ == "__main__":
    print(build())
