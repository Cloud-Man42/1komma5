"""Loader startup trust and integrity revalidation tests."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import select

from energy_core.config import Settings
from energy_core.db.installed_package_repo import InstalledPackageRepository
from energy_core.platform.modules.packages.installer import PackageInstaller
from energy_core.platform.modules.packages.loader import load_installed_module_packages
from energy_core.platform.modules.packages.signing import generate_ed25519_keypair, sign_package_dir
from energy_core.platform.modules.packages.trust_store import PublisherKeyRecord, PublisherKeyStatus, PublisherTrustStore
from energy_core.platform.modules.packages.types import PackageState
from energy_core.platform.modules.registry import default_module_registry

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "modules"
async def test_unsigned_package_quarantined_on_startup_when_prod_policy(package_session) -> None:
    session, settings, session_factory = package_session
    await PackageInstaller(session, settings).install(FIXTURES / "integration.demo-1.0.0.emicpkg")
    prod_settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=settings.database_url,
        EMIC_MODULES_PATH=settings.emic_modules_path,
        EMIC_ALLOW_UNSIGNED_MODULES=False,
    )
    default_module_registry.clear()
    with patch("energy_core.platform.modules.packages.loader.Settings", return_value=prod_settings):
        await load_installed_module_packages(session_factory, settings=prod_settings)
    repo = InstalledPackageRepository(session)
    record = await repo.get("integration.demo")
    assert record is not None
    assert record.package_state == PackageState.QUARANTINED
    assert default_module_registry.get("integration.demo") is None


@pytest.mark.asyncio
async def test_tampered_package_quarantined_on_startup(package_session) -> None:
    session, settings, session_factory = package_session
    await PackageInstaller(session, settings).install(FIXTURES / "integration.demo-1.0.0.emicpkg")
    repo = InstalledPackageRepository(session)
    record = await repo.get("integration.demo")
    manifest_path = Path(record.package_path) / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["description"] = "tampered"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    default_module_registry.clear()
    with patch("energy_core.platform.modules.packages.loader.Settings", return_value=settings):
        await load_installed_module_packages(session_factory, settings=settings)
    record = await repo.get("integration.demo")
    assert record.package_state == PackageState.QUARANTINED


@pytest.mark.asyncio
async def test_revoked_publisher_quarantines_signed_package_on_startup(package_session, tmp_path) -> None:
    session, settings, session_factory = package_session
    private_key, public_key = generate_ed25519_keypair()
    store = PublisherTrustStore(session)
    store.register_memory_key(
        PublisherKeyRecord(
            publisher_id="emic-tests",
            key_id="test-1",
            public_key=public_key,
            status=PublisherKeyStatus.TRUSTED,
        )
    )
    from energy_core.db.models.module_publisher_key import ModulePublisherKeyModel

    session.add(
        ModulePublisherKeyModel(
            publisher_id="emic-tests",
            key_id="test-1",
            public_key_hex=public_key.hex(),
            status="trusted",
        )
    )
    await session.commit()

    archive = FIXTURES / "integration.demo-1.0.0.emicpkg"
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

    from energy_core.platform.modules.packages.validator import PackageValidator

    validation = await PackageValidator(settings, trust_store=store).validate_archive(signed_archive, installed_versions={})
    assert validation.install_allowed is True
    await PackageInstaller(session, settings).install(signed_archive)

    row = await session.scalar(
        select(ModulePublisherKeyModel).where(
            ModulePublisherKeyModel.publisher_id == "emic-tests",
            ModulePublisherKeyModel.key_id == "test-1",
        )
    )
    row.status = "revoked"
    await session.commit()

    default_module_registry.clear()
    with patch("energy_core.platform.modules.packages.loader.Settings", return_value=settings):
        await load_installed_module_packages(session_factory, settings=settings)
    repo = InstalledPackageRepository(session)
    record = await repo.get("integration.demo")
    assert record.package_state == PackageState.QUARANTINED


@pytest.mark.asyncio
async def test_signed_package_survives_second_startup_after_import(package_session, tmp_path) -> None:
    session, settings, session_factory = package_session
    private_key, public_key = generate_ed25519_keypair()
    store = PublisherTrustStore(session)
    store.register_memory_key(
        PublisherKeyRecord(
            publisher_id="emic-tests",
            key_id="test-1",
            public_key=public_key,
            status=PublisherKeyStatus.TRUSTED,
        )
    )
    from energy_core.db.models.module_publisher_key import ModulePublisherKeyModel

    session.add(
        ModulePublisherKeyModel(
            publisher_id="emic-tests",
            key_id="test-1",
            public_key_hex=public_key.hex(),
            status="trusted",
        )
    )
    await session.commit()

    archive = FIXTURES / "integration.demo-1.0.0.emicpkg"
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

    await PackageInstaller(session, settings).install(signed_archive)

    default_module_registry.clear()
    with patch("energy_core.platform.modules.packages.loader.Settings", return_value=settings):
        await load_installed_module_packages(session_factory, settings=settings)
    assert default_module_registry.get("integration.demo") is not None

    default_module_registry.clear()
    with patch("energy_core.platform.modules.packages.loader.Settings", return_value=settings):
        await load_installed_module_packages(session_factory, settings=settings)
    repo = InstalledPackageRepository(session)
    record = await repo.get("integration.demo")
    assert record is not None
    assert record.package_state == PackageState.INSTALLED
    assert default_module_registry.get("integration.demo") is not None
