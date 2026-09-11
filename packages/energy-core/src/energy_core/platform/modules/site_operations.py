"""Aggregated site operations view for Module/Device hub."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings, get_settings
from energy_core.platform.devices.registry import DeviceRegistry
from energy_core.platform.modules.site_modules import SiteModuleResolver


@dataclass(frozen=True, slots=True)
class OperationsModuleCard:
    module_id: str
    name: str
    module_type: str
    enabled: bool
    runtime_status: str
    health_status: str
    last_error: str | None
    device_count: int
    can_disable: bool
    onboardable: bool
    package_source: str | None = None
    installed_version: str | None = None
    publisher: str | None = None
    package_state: str | None = None
    rollback_available: bool = False
    update_available: bool = False


@dataclass(frozen=True, slots=True)
class OperationsDeviceCard:
    device_type: str
    device_id: int
    name: str
    manufacturer: str
    model: str
    integration: str | None
    connection_status: str | None
    health_status: str
    last_seen: str | None
    enabled: bool


@dataclass(frozen=True, slots=True)
class SiteOperationsSnapshot:
    site_slug: str
    overall_health_status: str
    modules: tuple[OperationsModuleCard, ...]
    devices: tuple[OperationsDeviceCard, ...]
    integration_health: tuple[dict[str, Any], ...]


class SiteOperationsService:
    def __init__(self, session: AsyncSession, *, settings: Settings | None = None, is_sqlite: bool = False) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._is_sqlite = is_sqlite

    async def build_snapshot(self, site_id: int, site_slug: str) -> SiteOperationsSnapshot:
        from energy_core.contracts.health import HealthStatus, aggregate_health_status
        from energy_core.platform.health.aggregator import HealthAggregator
        from energy_core.platform.modules.registry import default_module_registry
        from energy_core.db.installed_package_repo import InstalledPackageRepository

        resolver = SiteModuleResolver(self._session, settings=self._settings)
        modules = await resolver.list_modules(site_id)
        installed_packages = {
            row.module_id: row for row in await InstalledPackageRepository(self._session).list_all()
        }
        devices = await DeviceRegistry(self._session).list_for_site(site_id)
        devices_by_integration: dict[str, int] = {}
        for device in devices:
            key = device.integration or "unknown"
            devices_by_integration[key] = devices_by_integration.get(key, 0) + 1

        module_cards: list[OperationsModuleCard] = []
        for state in modules:
            descriptor = default_module_registry.get(state.module_id)
            integration_key = state.module_id.split(".")[-1] if state.module_id.startswith("integration.") else None
            device_count = devices_by_integration.get(integration_key or "", 0) if integration_key else 0
            if state.module_id == "integration.chargeamps":
                device_count = sum(1 for d in devices if d.device_id.device_type.value == "ev_charger")
            elif state.module_id == "integration.mercedes":
                device_count = sum(1 for d in devices if d.device_id.device_type.value == "vehicle")
            elif state.module_id == "integration.arctic_spa":
                device_count = sum(1 for d in devices if d.device_id.device_type.value == "energy_consumer")
            package_row = installed_packages.get(state.module_id)
            module_cards.append(
                OperationsModuleCard(
                    module_id=state.module_id,
                    name=state.name,
                    module_type=state.module_type.value,
                    enabled=state.enabled,
                    runtime_status=state.runtime_status.value,
                    health_status=state.health_status.value,
                    last_error=state.last_error,
                    device_count=device_count,
                    can_disable=descriptor.can_disable if descriptor else True,
                    onboardable=descriptor.onboardable if descriptor else False,
                    package_source=descriptor.package_source.value if descriptor else None,
                    installed_version=(
                        package_row.installed_version if package_row else (descriptor.installed_version if descriptor else None)
                    ),
                    publisher=(
                        package_row.publisher if package_row else (descriptor.publisher if descriptor else None)
                    ),
                    package_state=(
                        package_row.package_state.value if package_row else (descriptor.package_state if descriptor else None)
                    ),
                    rollback_available=bool(package_row and package_row.rollback_version),
                    update_available=package_row.package_state.value == "update_available" if package_row else False,
                )
            )

        aggregator = HealthAggregator(self._session, is_sqlite=self._is_sqlite)
        records = await aggregator.list_for_site(site_id)
        provider_statuses = [record.status for record in records]
        overall = aggregate_health_status(tuple(provider_statuses)) if provider_statuses else HealthStatus.UNAVAILABLE
        legacy_rows = await aggregator.recorder.list_for_site(site_id)
        legacy_by_provider = {row["provider"]: row for row in legacy_rows}
        health_items = [
            {
                "provider": record.provider,
                "health_status": record.status.value,
                "last_error_class": legacy_by_provider.get(record.provider, {}).get("last_error_class"),
                "latency_ms": legacy_by_provider.get(record.provider, {}).get("latency_ms"),
            }
            for record in records
        ]

        device_cards = tuple(
            OperationsDeviceCard(
                device_type=record.device_id.device_type.value,
                device_id=record.device_id.id,
                name=record.name,
                manufacturer=record.manufacturer,
                model=record.model,
                integration=record.integration,
                connection_status=record.connection_status,
                health_status=record.health_status.value,
                last_seen=record.last_seen.isoformat() if record.last_seen else None,
                enabled=record.enabled,
            )
            for record in devices
        )

        return SiteOperationsSnapshot(
            site_slug=site_slug,
            overall_health_status=overall.value,
            modules=tuple(module_cards),
            devices=device_cards,
            integration_health=tuple(health_items),
        )
