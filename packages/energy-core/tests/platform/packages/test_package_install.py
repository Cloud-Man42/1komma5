"""Package install lifecycle tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from energy_core.db.installed_package_repo import InstalledPackageRepository
from energy_core.platform.modules.bootstrap import register_default_modules
from energy_core.platform.modules.packages.installer import PackageInstaller
from energy_core.platform.modules.packages.loader import load_installed_module_packages
from energy_core.platform.modules.packages.remover import PackageRemover
from energy_core.platform.modules.registry import default_module_registry

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "modules"


@pytest.mark.asyncio
async def test_install_demo_package(package_session) -> None:
    session, settings, _ = package_session
    archive = FIXTURES / "integration.demo-1.0.0.emicpkg"
    result = await PackageInstaller(session, settings).install(archive)
    assert result.success is True
    assert result.restart_required is True
    row = await InstalledPackageRepository(session).get("integration.demo")
    assert row is not None
    assert row.installed_version == "1.0.0"


@pytest.mark.asyncio
async def test_installed_package_registers_on_loader(package_session) -> None:
    session, settings, session_factory = package_session
    archive = FIXTURES / "integration.demo-1.0.0.emicpkg"
    await PackageInstaller(session, settings).install(archive)
    register_default_modules()
    await load_installed_module_packages(session_factory, settings=settings)
    descriptor = default_module_registry.get("integration.demo")
    assert descriptor is not None
    assert descriptor.package_source.value == "installed"


@pytest.mark.asyncio
async def test_remove_installed_package(package_session) -> None:
    session, settings, _ = package_session
    archive = FIXTURES / "integration.demo-1.0.0.emicpkg"
    await PackageInstaller(session, settings).install(archive)
    result = await PackageRemover(session, settings).remove("integration.demo")
    assert result.success is True
    assert await InstalledPackageRepository(session).get("integration.demo") is None
