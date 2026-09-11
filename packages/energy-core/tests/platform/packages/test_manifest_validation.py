"""Package manifest validation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from energy_core.config import Settings
from energy_core.platform.modules.packages.errors import MODULE_ALREADY_INSTALLED, MODULE_ID_PROTECTED
from energy_core.platform.modules.packages.validator import PackageValidator

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "modules"


@pytest.fixture
def package_settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        EMIC_MODULES_PATH=str(tmp_path / "modules"),
        EMIC_ALLOW_UNSIGNED_MODULES=True,
    )


@pytest.mark.asyncio
async def test_validate_demo_package_ok(package_settings: Settings) -> None:
    archive = FIXTURES / "integration.demo-1.0.0.emicpkg"
    result = await PackageValidator(package_settings).validate_archive(archive)
    assert result.valid is True
    assert result.manifest is not None
    assert result.manifest.module_id == "integration.demo"
    assert result.manifest.version == "1.0.0"
    assert result.install_allowed is True


@pytest.mark.asyncio
async def test_validate_rejects_builtin_module_id(package_settings: Settings) -> None:
    archive = FIXTURES / "integration.demo-1.0.0.emicpkg"
    validator = PackageValidator(package_settings)
    result = await validator.validate_archive(archive, installed_versions={"integration.demo": "1.0.0"})
    assert result.valid is False
    assert MODULE_ALREADY_INSTALLED in result.errors


@pytest.mark.asyncio
async def test_validate_rejects_protected_id(package_settings: Settings, tmp_path) -> None:
    import json
    import zipfile

    bad = tmp_path / "bad.emicpkg"
    manifest = {
        "module_id": "integration.heartbeat",
        "name": "Heartbeat",
        "version": "9.9.9",
        "module_type": "integration",
        "description": "x",
        "publisher": "x",
        "entrypoint": "demo:build_module",
        "module_api_version": 1,
        "minimum_emic_version": "0.1.0",
        "provided_capabilities": ["read_status"],
        "required_capabilities": [],
        "optional_capabilities": [],
        "module_dependencies": [],
        "configuration_schema": {"fields": []},
        "permissions": ["device.read"],
        "supports_per_site_activation": True,
        "requires_restart_on_update": True,
        "integrity": {"archive_sha256": "0" * 64},
    }
    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
    result = await PackageValidator(package_settings).validate_archive(bad)
    assert result.valid is False
    assert MODULE_ID_PROTECTED in result.errors
