"""Package remove guard tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from energy_core.platform.modules.packages.errors import MODULE_HAS_DEVICES, PackageError
from energy_core.platform.modules.packages.installer import PackageInstaller
from energy_core.platform.modules.packages.remover import PackageRemover

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "modules"


@pytest.mark.asyncio
async def test_remove_blocks_when_devices_reference_module(package_session, monkeypatch) -> None:
    session, settings, _ = package_session
    await PackageInstaller(session, settings).install(FIXTURES / "integration.demo-1.0.0.emicpkg")

    from energy_core.platform.devices.registry import DeviceId, DeviceRecord, DeviceRegistry, DeviceType
    from energy_core.contracts.health import HealthStatus

    async def fake_list(self, module_id: str):
        return (
            DeviceRecord(
                device_id=DeviceId(DeviceType.ENERGY_CONSUMER, 1),
                site_id=1,
                name="Demo device",
                manufacturer="",
                model="demo",
                integration="integration.demo",
                connection_status=None,
                health_status=HealthStatus.HEALTHY,
                last_seen=None,
                enabled=True,
            ),
        )

    monkeypatch.setattr(DeviceRegistry, "list_referencing_module", fake_list)

    with pytest.raises(PackageError) as exc:
        await PackageRemover(session, settings).remove("integration.demo")
    assert exc.value.code == MODULE_HAS_DEVICES
