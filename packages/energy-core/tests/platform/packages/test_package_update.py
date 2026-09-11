"""Package update and rollback tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from energy_core.db.installed_package_repo import InstalledPackageRepository
from energy_core.platform.modules.packages.errors import HEALTH_GATE_FAILED, PackageError
from energy_core.platform.modules.packages.installer import PackageInstaller
from energy_core.platform.modules.packages.rollback import PackageRollbackService
from energy_core.platform.modules.packages.updater import PackageUpdater

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "modules"


@pytest.mark.asyncio
async def test_update_demo_1_0_to_1_1(package_session) -> None:
    session, settings, _ = package_session
    await PackageInstaller(session, settings).install(FIXTURES / "integration.demo-1.0.0.emicpkg")
    result = await PackageUpdater(session, settings).update(
        "integration.demo",
        FIXTURES / "integration.demo-1.1.0.emicpkg",
    )
    assert result.success is True
    assert result.installed_version == "1.1.0"
    row = await InstalledPackageRepository(session).get("integration.demo")
    assert row is not None
    assert row.rollback_version == "1.0.0"


@pytest.mark.asyncio
async def test_rollback_after_update(package_session) -> None:
    session, settings, _ = package_session
    await PackageInstaller(session, settings).install(FIXTURES / "integration.demo-1.0.0.emicpkg")
    await PackageUpdater(session, settings).update(
        "integration.demo",
        FIXTURES / "integration.demo-1.1.0.emicpkg",
    )
    result = await PackageRollbackService(session, settings).rollback("integration.demo")
    assert result.installed_version == "1.0.0"


@pytest.mark.asyncio
async def test_bad_health_update_rejected(package_session) -> None:
    session, settings, _ = package_session
    await PackageInstaller(session, settings).install(FIXTURES / "integration.demo-1.0.0.emicpkg")
    await PackageUpdater(session, settings).update(
        "integration.demo",
        FIXTURES / "integration.demo-1.1.0.emicpkg",
    )
    with pytest.raises(PackageError) as exc:
        await PackageUpdater(session, settings).update(
            "integration.demo",
            FIXTURES / "integration.demo-1.2.0-bad.emicpkg",
        )
    assert exc.value.code == HEALTH_GATE_FAILED
    row = await InstalledPackageRepository(session).get("integration.demo")
    assert row is not None
    assert row.installed_version == "1.1.0"
