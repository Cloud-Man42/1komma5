"""Package runtime and capability registration tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from energy_core.db.models.modules import SiteModuleConfigurationModel
from energy_core.platform.capabilities.registry import default_capability_registry
from energy_core.platform.capabilities.types import Capability
from energy_core.platform.modules.bootstrap import register_default_modules
from energy_core.platform.modules.packages.installer import PackageInstaller
from energy_core.platform.modules.packages.loader import load_installed_module_packages
from energy_core.platform.modules.site_modules import SiteModuleResolver

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "modules"


@pytest.mark.asyncio
async def test_package_capability_registered_when_enabled(package_session) -> None:
    session, settings, session_factory = package_session
    await PackageInstaller(session, settings).install(FIXTURES / "integration.demo-1.0.0.emicpkg")
    register_default_modules()
    await load_installed_module_packages(session_factory, settings=settings)

    session.add(
        SiteModuleConfigurationModel(
            site_id=1,
            module_id="integration.demo",
            enabled_override=True,
        )
    )
    await session.commit()

    default_capability_registry.clear_site(1)
    resolver = SiteModuleResolver(session, settings=settings)
    await resolver.register_capabilities_for_module(1, "integration.demo")
    providers = default_capability_registry.providers_for(1, Capability.READ_STATUS)
    assert any(p.module_id == "integration.demo" for p in providers)
