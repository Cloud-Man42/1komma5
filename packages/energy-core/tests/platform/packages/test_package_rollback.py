"""Package rollback focused tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from energy_core.platform.modules.packages.installer import PackageInstaller
from energy_core.platform.modules.packages.rollback import PackageRollbackService
from energy_core.platform.modules.packages.updater import PackageUpdater

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "modules"


@pytest.mark.asyncio
async def test_explicit_downgrade_via_rollback(package_session) -> None:
    session, settings, _ = package_session
    await PackageInstaller(session, settings).install(FIXTURES / "integration.demo-1.0.0.emicpkg")
    await PackageUpdater(session, settings).update(
        "integration.demo",
        FIXTURES / "integration.demo-1.1.0.emicpkg",
    )
    result = await PackageRollbackService(session, settings).rollback("integration.demo")
    assert result.installed_version == "1.0.0"
    assert result.restart_required is True
