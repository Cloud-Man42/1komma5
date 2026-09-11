"""Build .emicpkg fixtures for integration.demo."""

from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from energy_core.platform.modules.packages.canonical import canonical_manifest_bytes, manifest_sha256

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent


def _manifest(version: str, *, fail_health_default: bool = False, label: str = "demo") -> dict:
    schema = {
        "fields": [
            {"name": "label", "label": "Label", "type": "string", "default": label},
            {"name": "fail_health", "label": "Fail health", "type": "boolean", "default": fail_health_default},
        ]
    }
    return {
        "module_id": "integration.demo",
        "name": "Integration Demo",
        "version": version,
        "module_type": "integration",
        "description": "Safe reference module for package lifecycle tests",
        "publisher": "emic-tests",
        "entrypoint": "demo:build_module",
        "module_api_version": 1,
        "minimum_emic_version": "0.1.0",
        "provided_capabilities": ["read_status"],
        "required_capabilities": [],
        "optional_capabilities": [],
        "module_dependencies": [],
        "configuration_schema": schema,
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


def _write_package(
    version: str,
    archive_name: str,
    *,
    fail_health_default: bool = False,
    label: str = "demo",
) -> None:
    build_dir = ROOT / ".build" / version
    if build_dir.exists():
        shutil.rmtree(build_dir)
    module_dir = build_dir / "module"
    shutil.copytree(ROOT / "module", module_dir)
    schemas_dir = build_dir / "schemas"
    schemas_dir.mkdir(parents=True)
    manifest = _manifest(version, fail_health_default=fail_health_default, label=label)
    (schemas_dir / "configuration.schema.json").write_text(
        json.dumps(manifest["configuration_schema"], indent=2),
        encoding="utf-8",
    )
    (build_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    content_hash = _content_hash(build_dir)
    manifest_hash = manifest_sha256(manifest)
    manifest["integrity"] = {
        "archive_sha256": content_hash,
        "manifest_sha256": manifest_hash,
    }
    (build_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    archive_path = OUT / archive_name
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in build_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(build_dir).as_posix())
    shutil.rmtree(build_dir)


def main() -> None:
    _write_package("1.0.0", "integration.demo-1.0.0.emicpkg")
    _write_package("1.1.0", "integration.demo-1.1.0.emicpkg", label="demo-1.1")
    _write_package("2.0.0", "integration.demo-2.0.0.emicpkg", label="demo-2.0")
    _write_package("1.2.0", "integration.demo-1.2.0-bad.emicpkg", fail_health_default=True)


if __name__ == "__main__":
    main()
