"""Package security guards."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.platform.modules.packages.errors import (
    INVALID_PERMISSION,
    MODULE_ID_PROTECTED,
    PACKAGE_LOCKED,
    PackageError,
    PATH_TRAVERSAL,
    SIGNATURE_INVALID,
    VERSION_DOWNGRADE_NOT_ALLOWED,
)
from energy_core.platform.modules.packages.extractor import PackageExtractor
from energy_core.platform.modules.packages.installer import PackageInstaller
from energy_core.platform.modules.packages.package_lock import PackageMutationLock
from energy_core.platform.modules.packages.paths import ModulePackagePaths
from energy_core.platform.modules.packages.signing import generate_ed25519_keypair, sign_package_dir
from energy_core.platform.modules.packages.trust_store import PublisherKeyRecord, PublisherKeyStatus, PublisherTrustStore
from energy_core.platform.modules.packages.updater import PackageUpdater
from energy_core.platform.modules.packages.validator import PackageValidator
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "modules"


async def register_test_publisher(session, *, publisher_id: str = "emic-tests", key_id: str = "test-1"):
    private_key, public_key = generate_ed25519_keypair()
    store = PublisherTrustStore(session)
    store.register_memory_key(
        PublisherKeyRecord(
            publisher_id=publisher_id,
            key_id=key_id,
            public_key=public_key,
            status=PublisherKeyStatus.TRUSTED,
        )
    )
    return store, private_key


def test_zip_slip_rejected(tmp_path) -> None:
    archive = tmp_path / "evil.emicpkg"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../../outside.txt", "bad")
    paths = ModulePackagePaths(tmp_path / "modules")
    paths.ensure_layout()
    target = paths.staging_dir("integration.demo", "1.0.0")
    with pytest.raises(PackageError) as exc:
        PackageExtractor(paths).extract(archive, target)
    assert exc.value.code == PATH_TRAVERSAL


@pytest.mark.asyncio
async def test_unsigned_rejected_when_not_allowed(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        EMIC_MODULES_PATH=str(tmp_path / "modules"),
        EMIC_ALLOW_UNSIGNED_MODULES=False,
    )
    result = await PackageValidator(settings).validate_archive(FIXTURES / "integration.demo-1.0.0.emicpkg")
    assert result.valid is False
    assert "SIGNATURE_INVALID" in result.errors
    assert result.install_allowed is False


@pytest.mark.asyncio
async def test_install_unsigned_rejected_in_prod_mode(tmp_path) -> None:
    db_file = tmp_path / "packages.db"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        EMIC_MODULES_PATH=str(tmp_path / "modules"),
        EMIC_ALLOW_UNSIGNED_MODULES=False,
    )
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        with pytest.raises(PackageError) as exc:
            await PackageInstaller(session, settings).install(FIXTURES / "integration.demo-1.0.0.emicpkg")
        assert exc.value.code == SIGNATURE_INVALID
    await engine.dispose()


@pytest.mark.asyncio
async def test_platform_namespace_protected(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        EMIC_MODULES_PATH=str(tmp_path / "modules"),
        EMIC_ALLOW_UNSIGNED_MODULES=True,
    )
    archive = tmp_path / "platform.fake.emicpkg"
    manifest = {
        "module_id": "platform.fake",
        "name": "Fake",
        "version": "1.0.0",
        "module_type": "integration",
        "description": "bad",
        "publisher": "emic-tests",
        "entrypoint": "demo:build_module",
        "module_api_version": 1,
        "minimum_emic_version": "0.1.0",
        "provided_capabilities": [],
        "required_capabilities": [],
        "optional_capabilities": [],
        "module_dependencies": [],
        "configuration_schema": {"fields": []},
        "permissions": [],
        "supports_per_site_activation": True,
        "requires_restart_on_update": True,
        "integrity": {"archive_sha256": "00" * 32},
    }
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
    result = await PackageValidator(settings).validate_archive(archive)
    assert MODULE_ID_PROTECTED in result.errors


@pytest.mark.asyncio
async def test_invalid_permission_rejected(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        EMIC_MODULES_PATH=str(tmp_path / "modules"),
        EMIC_ALLOW_UNSIGNED_MODULES=True,
    )
    archive = tmp_path / "bad-perm.emicpkg"
    manifest = {
        "module_id": "integration.custom",
        "name": "Custom",
        "version": "1.0.0",
        "module_type": "integration",
        "description": "bad",
        "publisher": "emic-tests",
        "entrypoint": "demo:build_module",
        "module_api_version": 1,
        "minimum_emic_version": "0.1.0",
        "provided_capabilities": ["read_status"],
        "required_capabilities": [],
        "optional_capabilities": [],
        "module_dependencies": [],
        "configuration_schema": {"fields": []},
        "permissions": ["root.all"],
        "supports_per_site_activation": True,
        "requires_restart_on_update": True,
        "integrity": {"archive_sha256": "00" * 32},
    }
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
    result = await PackageValidator(settings).validate_archive(archive)
    assert INVALID_PERMISSION in result.errors


@pytest.mark.asyncio
async def test_downgrade_blocked_by_default(package_session) -> None:
    session, settings, _ = package_session
    await PackageInstaller(session, settings).install(FIXTURES / "integration.demo-1.0.0.emicpkg")
    await PackageUpdater(session, settings).update(
        "integration.demo",
        FIXTURES / "integration.demo-1.1.0.emicpkg",
    )
    with pytest.raises(PackageError) as exc:
        await PackageUpdater(session, settings).update(
            "integration.demo",
            FIXTURES / "integration.demo-1.0.0.emicpkg",
        )
    assert exc.value.code == VERSION_DOWNGRADE_NOT_ALLOWED


@pytest.mark.asyncio
async def test_concurrent_install_lock(package_session) -> None:
    session, settings, _ = package_session
    lock = PackageMutationLock(settings.resolved_modules_path())
    with lock.acquire("integration.demo"):
        with pytest.raises(PackageError) as exc:
            with lock.acquire("integration.demo", timeout_seconds=0.01):
                pass
        assert exc.value.code == PACKAGE_LOCKED
    await PackageInstaller(session, settings).install(FIXTURES / "integration.demo-1.0.0.emicpkg")


@pytest.mark.asyncio
async def test_signed_package_with_trusted_key(package_session, tmp_path) -> None:
    session, settings, _ = package_session
    store, private_key = await register_test_publisher(session)
    archive = FIXTURES / "integration.demo-1.0.0.emicpkg"
    import zipfile

    extract_dir = tmp_path / "pkg"
    with zipfile.ZipFile(archive, "r") as zf:
        zf.extractall(extract_dir)
    sign_package_dir(
        package_dir=extract_dir,
        publisher="emic-tests",
        key_id="test-1",
        private_key_pem=private_key,
    )
    signed_archive = tmp_path / "signed.emicpkg"
    with zipfile.ZipFile(signed_archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in extract_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(extract_dir).as_posix())

    validator = PackageValidator(settings, trust_store=store)
    result = await validator.validate_archive(signed_archive, installed_versions={})
    assert result.valid is True
    assert result.signature_valid is True
    assert result.publisher_trusted is True
    assert result.install_allowed is True
