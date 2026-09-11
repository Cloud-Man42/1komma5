"""Sensibo runtime authorization gate tests (Sprint E)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from energy_core.db.models.module_publisher import ModulePublisherModel
from energy_core.db.models.module_publisher_key import ModulePublisherKeyModel
from energy_core.config import AppEnvironment
from energy_core.platform.modules.bootstrap import register_default_modules
from energy_core.platform.modules.governance.types import PublisherTier
from energy_core.platform.modules.packages.installer import PackageInstaller
from energy_core.platform.modules.packages.signing import generate_ed25519_keypair, sign_package_dir
from energy_core.platform.modules.packages.trust_store import PublisherKeyRecord, PublisherKeyStatus, PublisherTrustStore
from energy_core.platform.modules.runtime_authorization.service import RuntimeAuthorizationService
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "modules"
SENSIBO_ARCHIVE = FIXTURES / "integration.sensibo-1.0.0.emicpkg"
SIGNING_INFO = FIXTURES / "integration.sensibo-signing.json"


@pytest.fixture
async def sensibo_installed(isolation_session):
    session, settings, session_factory = isolation_session
    settings.app_env = AppEnvironment.PRODUCTION
    settings.third_party_runtime_enabled = False
    settings.isolated_runtime_enabled = True
    build_script = FIXTURES.parents[5] / "modules" / "sensibo" / "build_emicpkg.py"
    import subprocess
    import sys

    if not SENSIBO_ARCHIVE.exists():
        subprocess.run([sys.executable, str(build_script)], check=True)

    if SIGNING_INFO.exists():
        info = json.loads(SIGNING_INFO.read_text(encoding="utf-8"))
        public_key = bytes.fromhex(str(info["public_key_hex"]))
        session.add(
            ModulePublisherKeyModel(
                publisher_id=str(info["publisher_id"]),
                key_id=str(info["key_id"]),
                public_key_hex=public_key.hex(),
                status="trusted",
            )
        )
    else:
        private_key, public_key = generate_ed25519_keypair()
        session.add(
            ModulePublisherKeyModel(
                publisher_id="emic-official",
                key_id="sensibo-test",
                public_key_hex=public_key.hex(),
                status="trusted",
            )
        )
        import shutil
        import tempfile
        import zipfile

        with tempfile.TemporaryDirectory(prefix="emic-sensibo-test-sign-") as tmp:
            extract = Path(tmp) / "pkg"
            extract.mkdir()
            with zipfile.ZipFile(SENSIBO_ARCHIVE, "r") as zf:
                zf.extractall(extract)
            sign_package_dir(
                package_dir=extract,
                publisher="emic-official",
                key_id="sensibo-test",
                private_key_pem=private_key,
            )
            backup = SENSIBO_ARCHIVE.with_suffix(".emicpkg.bak")
            shutil.copy2(SENSIBO_ARCHIVE, backup)
            with zipfile.ZipFile(SENSIBO_ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for path in extract.rglob("*"):
                    if path.is_file():
                        zf.write(path, path.relative_to(extract).as_posix())

    session.add(
        ModulePublisherModel(
            publisher_id="emic-official",
            display_name="EMIC Official",
            tier=PublisherTier.OFFICIAL.value,
            status="ACTIVE",
        )
    )
    await session.commit()
    result = await PackageInstaller(session, settings).install(SENSIBO_ARCHIVE)
    assert result.success, result.message
    register_default_modules()
    from energy_core.db.installed_package_repo import InstalledPackageRepository
    from energy_core.platform.modules.packages.loader import _register_from_manifest, load_installed_module_packages

    installed = await InstalledPackageRepository(session).get("integration.sensibo")
    assert installed is not None
    package_dir = Path(installed.package_path)
    _register_from_manifest(package_dir / "manifest.json", package_dir, skip_import=True)
    await load_installed_module_packages(session_factory, settings=settings)
    return session, settings, session_factory


@pytest.mark.asyncio
async def test_sensibo_runtime_blocked_without_authorization(sensibo_installed):
    session, settings, _ = sensibo_installed
    allowed = await RuntimeAuthorizationService(session, settings).runtime_spawn_allowed(
        settings,
        module_id="integration.sensibo",
        version="1.0.0",
        artifact_sha256="0" * 64,
        publisher_id="emic-official",
        site_id=1,
    )
    assert allowed is False


@pytest.mark.asyncio
async def test_sensibo_runtime_allowed_with_exact_authorization(sensibo_installed):
    session, settings, _ = sensibo_installed
    from energy_core.db.installed_package_repo import InstalledPackageRepository

    package = await InstalledPackageRepository(session).get("integration.sensibo")
    assert package is not None
    auth = RuntimeAuthorizationService(session, settings)
    await auth.grant(
        module_id="integration.sensibo",
        version=package.installed_version,
        artifact_sha256=package.checksum_sha256,
        publisher_id=package.publisher,
        site_id=1,
        approved_by="test",
    )
    await session.commit()
    allowed = await auth.runtime_spawn_allowed(
        settings,
        module_id="integration.sensibo",
        version=package.installed_version,
        artifact_sha256=package.checksum_sha256,
        publisher_id=package.publisher,
        site_id=1,
    )
    assert allowed is True
    assert settings.runtime_spawn_allowed() is False
