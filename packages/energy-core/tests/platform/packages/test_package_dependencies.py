"""Package dependency resolution tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from energy_core.platform.modules.packages.errors import MISSING_DEPENDENCY
from energy_core.platform.modules.packages.validator import PackageValidator

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "modules"


@pytest.mark.asyncio
async def test_demo_package_has_no_dependencies(package_session) -> None:
    _, settings, _ = package_session
    result = await PackageValidator(settings).validate_archive(FIXTURES / "integration.demo-1.0.0.emicpkg")
    assert result.valid is True
    assert result.manifest is not None
    assert result.manifest.module_dependencies == ()


@pytest.mark.asyncio
async def test_missing_dependency_rejected(package_session, tmp_path) -> None:
    import json
    import zipfile

    from energy_core.platform.modules.packages.canonical import manifest_sha256
    from energy_core.platform.modules.packages.integrity import compute_package_content_sha256

    _, settings, _ = package_session
    manifest = {
        "module_id": "integration.depends",
        "name": "Depends",
        "version": "1.0.0",
        "module_type": "integration",
        "description": "needs demo",
        "publisher": "emic-tests",
        "entrypoint": "demo:build_module",
        "module_api_version": 1,
        "minimum_emic_version": "0.1.0",
        "provided_capabilities": [],
        "required_capabilities": [],
        "optional_capabilities": [],
        "module_dependencies": [{"module_id": "integration.demo", "version_range": ">=2.0.0"}],
        "configuration_schema": {"fields": []},
        "permissions": [],
        "supports_per_site_activation": True,
        "requires_restart_on_update": True,
    }
    archive = tmp_path / "depends.emicpkg"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
    # recompute integrity for validator
    manifest["integrity"] = {
        "archive_sha256": compute_package_content_sha256(archive),
        "manifest_sha256": manifest_sha256(manifest),
    }
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
    result = await PackageValidator(settings).validate_archive(archive, installed_versions={})
    assert result.valid is False
    assert MISSING_DEPENDENCY in result.errors
