"""Per-site module activation and capability projection."""

from __future__ import annotations

import time
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings, get_settings
from energy_core.cache.module_runtime_state import read_runtime_states, resolve_distributed_runtime_status
from energy_core.db.consumer_repo import ConsumerRepository
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.models import EvChargerModel, SiteModel
from energy_core.db.solar_forecast_repo import SolarSiteConfigRepository
from energy_core.db.vehicle_repo import VehicleProviderRepository
from energy_core.energy.client_access import open_heartbeat_client
from energy_core.platform.capabilities.registry import CapabilityRegistry, default_capability_registry
from energy_core.platform.capabilities.types import Capability
from energy_core.platform.modules.aliases import LEGACY_MODULE_ALIASES, resolve_module_id
from energy_core.platform.modules.registry import ModuleDescriptor, default_module_registry
from energy_core.platform.modules.resolver import CanDisableResult, CanStartResult, ModuleDependencyResolver, default_module_dependency_resolver
from energy_core.platform.modules.runtime import INTEGRATION_PROVIDER_MODULE_MAP, ModuleRuntimeStore, default_module_runtime_store
from energy_core.platform.modules.runtime_registry import ModuleRuntimeRegistry, default_module_runtime_registry
from energy_core.db.models.modules import SiteModuleConfigurationModel
from energy_core.platform.modules.types import ActivationStatus, ModuleHealthStatus, ModuleType, RuntimeStatus
from energy_core.platform.health.aggregator import HealthAggregator


_CACHE_TTL_SECONDS = 30.0
_site_cache: dict[int, tuple[float, tuple["SiteModuleState", ...]]] = {}


@dataclass(frozen=True, slots=True)
class SiteModuleState:
    module_id: str
    name: str
    version: str
    module_type: ModuleType
    enabled: bool
    activation: ActivationStatus
    runtime_status: RuntimeStatus
    health_status: ModuleHealthStatus
    capabilities_provided: tuple[str, ...]
    capabilities_required: tuple[str, ...]
    optional_capabilities: tuple[str, ...]
    missing_required_capabilities: tuple[str, ...]
    missing_optional_capabilities: tuple[str, ...]
    can_start: bool
    last_error: str | None = None


class SiteModuleResolver:
    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
        capability_registry: CapabilityRegistry | None = None,
        runtime_store: ModuleRuntimeStore | None = None,
        runtime_registry: ModuleRuntimeRegistry | None = None,
        dependency_resolver: ModuleDependencyResolver | None = None,
        is_sqlite: bool | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._capabilities = capability_registry or default_capability_registry
        self._runtime = runtime_store or default_module_runtime_store
        self._runtime_registry = runtime_registry or default_module_runtime_registry
        self._resolver = dependency_resolver or default_module_dependency_resolver
        self._is_sqlite = self._settings.is_sqlite if is_sqlite is None else is_sqlite

    async def list_modules(self, site_id: int, *, use_cache: bool = True) -> tuple[SiteModuleState, ...]:
        if use_cache:
            cached = _site_cache.get(site_id)
            if cached is not None and time.monotonic() - cached[0] <= _CACHE_TTL_SECONDS:
                return cached[1]

        projection = await self._project_enabled(site_id)
        overrides = await self._load_overrides(site_id)
        enabled_modules = self._apply_overrides(projection, overrides)

        await self._rebuild_runtime_capabilities(site_id, enabled_modules)

        distributed_runtime = await read_runtime_states(self._settings, site_id)
        distributed_expected = bool((self._settings.redis_url or "").strip())

        states: list[SiteModuleState] = []
        legacy_ids = set(LEGACY_MODULE_ALIASES.keys())
        for descriptor in default_module_registry.list_modules():
            if descriptor.module_id in legacy_ids:
                continue
            if not descriptor.supports_per_site_activation and descriptor.module_type == ModuleType.CORE:
                continue
            enabled = enabled_modules.get(descriptor.module_id, False)
            can_start = self._resolver.can_start(
                descriptor.module_id,
                site_id=site_id,
                enabled_modules=set(enabled_modules.keys()),
                capability_registry=self._capabilities,
            )
            runtime_handle = self._runtime_registry.get_handle(site_id, descriptor.module_id)
            distributed = distributed_runtime.get(descriptor.module_id)
            runtime_status = resolve_distributed_runtime_status(
                distributed,
                local_state=runtime_handle.state,
                enabled=enabled,
                distributed_runtime_expected=distributed_expected and enabled,
            )
            last_error = runtime_handle.last_error
            if distributed is not None and distributed.last_error:
                last_error = distributed.last_error
            if not enabled:
                runtime_status = RuntimeStatus.STOPPED
                activation = ActivationStatus.DISABLED
            elif runtime_status == RuntimeStatus.STOPPED and can_start.can_start:
                runtime_status = RuntimeStatus.STOPPED
                activation = ActivationStatus.ENABLED
            elif runtime_status in {
                RuntimeStatus.RUNNING,
                RuntimeStatus.STARTING,
                RuntimeStatus.STOPPING,
                RuntimeStatus.UNKNOWN,
            } and can_start.can_start:
                activation = ActivationStatus.ENABLED
            elif can_start.can_start:
                activation = ActivationStatus.ENABLED
            else:
                if distributed is None:
                    runtime_status = RuntimeStatus.BLOCKED
                activation = ActivationStatus.ENABLED

            health = await self._module_health(site_id, descriptor, enabled)
            if runtime_status == RuntimeStatus.RUNNING and health == ModuleHealthStatus.UNKNOWN:
                if descriptor.module_type != ModuleType.INTEGRATION:
                    health = ModuleHealthStatus.HEALTHY

            states.append(
                SiteModuleState(
                    module_id=descriptor.module_id,
                    name=descriptor.name,
                    version=descriptor.version,
                    module_type=descriptor.module_type,
                    enabled=enabled,
                    activation=activation,
                    runtime_status=runtime_status,
                    health_status=health,
                    capabilities_provided=tuple(cap.value for cap in descriptor.capabilities_provided),
                    capabilities_required=tuple(cap.value for cap in descriptor.capabilities_required),
                    optional_capabilities=tuple(cap.value for cap in descriptor.optional_capabilities),
                    missing_required_capabilities=tuple(cap.value for cap in can_start.missing_required),
                    missing_optional_capabilities=tuple(cap.value for cap in can_start.missing_optional),
                    can_start=can_start.can_start,
                    last_error=last_error,
                )
            )

        result = tuple(states)
        _site_cache[site_id] = (time.monotonic(), result)
        return result

    async def is_module_enabled(self, site_id: int, module_id: str) -> bool:
        canonical = resolve_module_id(module_id)
        modules = await self.list_modules(site_id)
        for state in modules:
            if state.module_id == canonical:
                return state.enabled and state.can_start
        return False

    async def is_module_active(self, site_id: int, module_id: str) -> bool:
        """Enabled at site level (ignores capability blocking)."""
        canonical = resolve_module_id(module_id)
        projection = await self._project_enabled(site_id)
        overrides = await self._load_overrides(site_id)
        enabled_modules = self._apply_overrides(projection, overrides)
        return enabled_modules.get(canonical, False)

    async def can_disable(self, site_id: int, module_id: str) -> CanDisableResult:
        canonical = resolve_module_id(module_id)
        projection = await self._project_enabled(site_id)
        overrides = await self._load_overrides(site_id)
        enabled_modules = set(self._apply_overrides(projection, overrides).keys())
        self._capabilities.clear_site(site_id)
        await self._register_site_capabilities(site_id, self._apply_overrides(projection, overrides))
        return self._resolver.can_disable(
            canonical,
            site_id=site_id,
            enabled_modules=enabled_modules,
            capability_registry=self._capabilities,
        )

    async def resolve_enabled_modules(self, site_id: int) -> dict[str, bool]:
        projection = await self._project_enabled(site_id)
        overrides = await self._load_overrides(site_id)
        return self._apply_overrides(projection, overrides)

    async def persist_enabled_override(self, site_id: int, module_id: str, enabled: bool) -> SiteModuleState:
        canonical = resolve_module_id(module_id)
        if not enabled:
            check = await self.can_disable(site_id, canonical)
            if not check.allowed:
                raise ValueError(check.reason or "Cannot disable module")

        row = await self._session.scalar(
            select(SiteModuleConfigurationModel).where(
                SiteModuleConfigurationModel.site_id == site_id,
                SiteModuleConfigurationModel.module_id == canonical,
            )
        )
        if row is None:
            row = SiteModuleConfigurationModel(site_id=site_id, module_id=canonical, enabled_override=enabled)
            self._session.add(row)
        else:
            row.enabled_override = enabled
        await self._session.flush()
        _site_cache.pop(site_id, None)
        modules = await self.list_modules(site_id, use_cache=False)
        for state in modules:
            if state.module_id == canonical:
                return state
        raise ValueError(f"Unknown module: {canonical}")

    async def set_enabled(self, site_id: int, module_id: str, enabled: bool) -> SiteModuleState:
        return await self.persist_enabled_override(site_id, module_id, enabled)

    async def register_capabilities_for_module(self, site_id: int, module_id: str) -> None:
        enabled = {module_id: True}
        await self._register_site_capabilities(site_id, enabled, module_ids={module_id})

    async def _rebuild_runtime_capabilities(self, site_id: int, enabled_modules: dict[str, bool]) -> None:
        self._capabilities.clear_site(site_id)
        running_modules = {
            module_id
            for module_id in enabled_modules
            if self._runtime_registry.is_running(site_id, module_id)
        }
        if not running_modules:
            return
        await self._register_site_capabilities(
            site_id,
            enabled_modules,
            module_ids=running_modules,
        )

    async def can_start_module(self, site_id: int, module_id: str) -> CanStartResult:
        canonical = resolve_module_id(module_id)
        projection = await self._project_enabled(site_id)
        overrides = await self._load_overrides(site_id)
        enabled = self._apply_overrides(projection, overrides)
        self._capabilities.clear_site(site_id)
        await self._register_site_capabilities(site_id, enabled)
        return self._resolver.can_start(
            canonical,
            site_id=site_id,
            enabled_modules=set(enabled.keys()),
            capability_registry=self._capabilities,
        )

    async def _load_overrides(self, site_id: int) -> dict[str, bool]:
        rows = await self._session.scalars(
            select(SiteModuleConfigurationModel).where(SiteModuleConfigurationModel.site_id == site_id)
        )
        return {row.module_id: bool(row.enabled_override) for row in rows.all() if row.enabled_override is not None}

    def _apply_overrides(self, projection: dict[str, bool], overrides: dict[str, bool]) -> dict[str, bool]:
        merged = dict(projection)
        for module_id, enabled in overrides.items():
            merged[module_id] = enabled
        return {mid: val for mid, val in merged.items() if val}

    async def _project_enabled(self, site_id: int) -> dict[str, bool]:
        site = await self._session.get(SiteModel, site_id)
        if site is None:
            return {}

        result: dict[str, bool] = {}

        heartbeat_ready = site.external_system_id is not None
        if heartbeat_ready:
            client = await open_heartbeat_client(self._session)
            heartbeat_ready = client is not None
        if heartbeat_ready:
            result["integration.heartbeat"] = True
            result["feature.price-engine"] = True

        chargers = await EvChargerRepository(self._session).list_for_site(site_id)
        bridge_chargers = [c for c in chargers if c.bridge_enabled]
        if bridge_chargers:
            result["integration.chargeamps"] = True
            result["feature.smart-charging"] = True
            result["feature.energy-balance"] = True

        vehicle_conn = await VehicleProviderRepository(self._session).get_for_site(site_id)
        if vehicle_conn is not None and vehicle_conn.enabled:
            result["integration.mercedes"] = True
            result["feature.vehicles"] = True

        spa_row = await ConsumerRepository(self._session).get_spa_by_site_slug(site.slug)
        if spa_row is not None:
            consumer, config, _ = spa_row
            if consumer.enabled and config.integration_enabled and self._settings.arctic_spa_enabled:
                result["integration.arctic_spa"] = True
                result["feature.spa-energy"] = True

        solar_config = await SolarSiteConfigRepository(self._session).get(site_id, timezone=site.timezone)
        if solar_config is not None and solar_config.enabled:
            result["feature.solar-forecast"] = True

        if site.optimization_mode and str(site.optimization_mode) != "MONITOR_ONLY":
            if self._settings.energy_control_collector_enabled:
                result["feature.energy-control"] = True

        if self._settings.chargefinder_enabled:
            result["integration.chargefinder"] = True

        return result

    async def _register_site_capabilities(
        self,
        site_id: int,
        enabled_modules: dict[str, bool],
        *,
        module_ids: set[str] | None = None,
    ) -> None:
        active = module_ids if module_ids is not None else set(enabled_modules.keys())

        if "integration.chargeamps" in active and enabled_modules.get("integration.chargeamps"):
            chargers = await EvChargerRepository(self._session).list_for_site(site_id)
            for charger in chargers:
                if not charger.bridge_enabled:
                    continue
                device_id = f"ev_charger:{charger.id}"
                for cap in (
                    Capability.EV_CHARGER_START,
                    Capability.EV_CHARGER_STOP,
                    Capability.EV_CHARGER_SET_CURRENT,
                    Capability.EV_CHARGER_READ_POWER,
                    Capability.EV_CHARGER_READ_ENERGY,
                ):
                    self._capabilities.register_provider(
                        site_id=site_id,
                        module_id="integration.chargeamps",
                        capability=cap,
                        device_id=device_id,
                    )

        if "integration.mercedes" in active and enabled_modules.get("integration.mercedes"):
            for cap in (
                Capability.VEHICLE_READ_SOC,
                Capability.VEHICLE_READ_RANGE,
                Capability.VEHICLE_READ_CHARGING_STATE,
            ):
                self._capabilities.register_provider(
                    site_id=site_id,
                    module_id="integration.mercedes",
                    capability=cap,
                )

        if "integration.heartbeat" in active and enabled_modules.get("integration.heartbeat"):
            for cap in (
                Capability.ENERGY_READ_GRID_POWER,
                Capability.ENERGY_READ_SOLAR_POWER,
                Capability.BATTERY_READ_SOC,
                Capability.BATTERY_READ_POWER,
                Capability.PRICE_READ_CURRENT,
                Capability.PRICE_READ_FORECAST,
            ):
                self._capabilities.register_provider(
                    site_id=site_id,
                    module_id="integration.heartbeat",
                    capability=cap,
                )

        if "integration.arctic_spa" in active and enabled_modules.get("integration.arctic_spa"):
            self._capabilities.register_provider(
                site_id=site_id,
                module_id="integration.arctic_spa",
                capability=Capability.SPA_READ_TEMPERATURE,
            )
            self._capabilities.register_provider(
                site_id=site_id,
                module_id="integration.arctic_spa",
                capability=Capability.READ_POWER,
            )

        if "feature.solar-forecast" in active and enabled_modules.get("feature.solar-forecast"):
            self._capabilities.register_provider(
                site_id=site_id,
                module_id="feature.solar-forecast",
                capability=Capability.FORECAST_SOLAR,
            )
            self._capabilities.register_provider(
                site_id=site_id,
                module_id="feature.solar-forecast",
                capability=Capability.WEATHER_READ_FORECAST,
            )
            site = await self._session.get(SiteModel, site_id)
            country = ((site.energy_economics_country if site else None) or "SE").upper()[:2]
            if country == "DK":
                self._capabilities.register_provider(
                    site_id=site_id,
                    module_id="integration.dmi",
                    capability=Capability.WEATHER_READ_FORECAST,
                )
            elif country == "SE":
                self._capabilities.register_provider(
                    site_id=site_id,
                    module_id="integration.smhi",
                    capability=Capability.WEATHER_READ_FORECAST,
                )
                self._capabilities.register_provider(
                    site_id=site_id,
                    module_id="integration.smhi",
                    capability=Capability.WEATHER_READ_CURRENT,
                )
            self._capabilities.register_provider(
                site_id=site_id,
                module_id="integration.open_meteo",
                capability=Capability.WEATHER_READ_FORECAST,
            )

        if "integration.chargefinder" in active and enabled_modules.get("integration.chargefinder"):
            self._capabilities.register_provider(
                site_id=site_id,
                module_id="integration.chargefinder",
                capability=Capability.READ_STATUS,
            )

        for module_id in active:
            if not enabled_modules.get(module_id):
                continue
            descriptor = default_module_registry.get(module_id)
            if descriptor is None or descriptor.package_source.value != "installed":
                continue
            for cap in descriptor.capabilities_provided:
                self._capabilities.register_provider(
                    site_id=site_id,
                    module_id=module_id,
                    capability=cap,
                )

    async def _module_health(
        self,
        site_id: int,
        descriptor: ModuleDescriptor,
        enabled: bool,
    ) -> ModuleHealthStatus:
        if not enabled:
            return ModuleHealthStatus.UNKNOWN
        if descriptor.module_type != ModuleType.INTEGRATION:
            return ModuleHealthStatus.HEALTHY

        aggregator = HealthAggregator(self._session, is_sqlite=self._is_sqlite)
        records = await aggregator.list_for_site(site_id)
        for record in records:
            module_id = INTEGRATION_PROVIDER_MODULE_MAP.get(record.provider)
            if module_id == descriptor.module_id:
                return ModuleHealthStatus(record.status.value)
        return ModuleHealthStatus.UNKNOWN


def invalidate_site_module_cache(site_id: int | None = None) -> None:
    if site_id is None:
        _site_cache.clear()
    else:
        _site_cache.pop(site_id, None)
