"""Build integration.sensibo .emicpkg artifact."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
sys.path.insert(0, str(REPO_ROOT / "packages" / "energy-core" / "src"))

from energy_core.platform.modules.packages.canonical import canonical_manifest_bytes, manifest_sha256


def _manifest(version: str = "1.0.0") -> dict:
    return {
        "module_id": "integration.sensibo",
        "name": "Sensibo Climate",
        "version": version,
        "module_type": "integration",
        "description": "Read-only Sensibo climate monitoring via isolated runtime",
        "publisher": "emic-official",
        "supports_discovery": True,
        "entrypoint": "module:build_module",
        "module_api_version": 1,
        "minimum_emic_version": "0.1.0",
        "provided_capabilities": [
            "hvac.read_temperature",
            "hvac.read_humidity",
            "hvac.read_state",
            "hvac.read_target_temperature",
            "hvac.read_status",
        ],
        "required_capabilities": [],
        "optional_capabilities": [],
        "module_dependencies": [],
        "configuration_schema": {
            "fields": [
                {"name": "credential_ref", "type": "secret_ref", "required": True},
                {"name": "poll_interval_seconds", "type": "integer", "minimum": 60, "maximum": 3600},
                {"name": "selected_device_ids", "type": "array", "items": {"type": "string"}},
            ]
        },
        "permissions": ["network.external", "secrets.read_own", "device.read"],
        "network_hosts": ["home.sensibo.com"],
        "supports_per_site_activation": True,
        "requires_restart_on_update": True,
        "can_disable": True,
        "onboardable": True,
        "onboard_handler": "sensibo",
        "device_categories": ["climate"],
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

    out_dir = REPO_ROOT / "packages" / "energy-core" / "tests" / "fixtures" / "modules"
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / f"integration.sensibo-{version}.emicpkg"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in build_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(build_dir).as_posix())
    shutil.rmtree(build_dir)
    return archive


if __name__ == "__main__":
    artifact = build()
    print(artifact)
