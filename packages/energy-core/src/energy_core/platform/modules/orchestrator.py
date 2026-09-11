"""Module lifecycle orchestration."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings, get_settings
from energy_core.platform.capabilities.registry import CapabilityRegistry, default_capability_registry
from energy_core.platform.modules.handlers import (
    LaneModuleHandler,
    ModuleRuntimeContext,
    get_module_handler,
)
from energy_core.platform.modules.isolation.adapters import IsolatedModuleAdapter
from energy_core.platform.modules.isolation.policy import requires_isolated_runtime
from energy_core.platform.modules.registry import default_module_registry
from energy_core.platform.modules.resolver import ModuleDependencyResolver, default_module_dependency_resolver
from energy_core.platform.modules.runtime_registry import ModuleRuntimeRegistry, default_module_runtime_registry
from energy_core.platform.modules.site_modules import SiteModuleResolver, invalidate_site_module_cache
from energy_core.cache.module_runtime_state import publish_runtime_state
from energy_core.platform.modules.types import RuntimeStatus

logger = logging.getLogger(__name__)


class ModuleOrchestrator:
    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
        session_factory: object | None = None,
        capability_registry: CapabilityRegistry | None = None,
        runtime_registry: ModuleRuntimeRegistry | None = None,
        dependency_resolver: ModuleDependencyResolver | None = None,
        extras: dict | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._session_factory = session_factory
        self._capabilities = capability_registry or default_capability_registry
        self._runtime = runtime_registry or default_module_runtime_registry
        self._resolver = dependency_resolver or default_module_dependency_resolver
        self._extras = extras or {}

    async def _emit_runtime_state(
        self,
        site_id: int,
        module_id: str,
        *,
        runtime_state: RuntimeStatus,
        last_error: str | None = None,
    ) -> None:
        module_version: str | None = None
        package_checksum: str | None = None
        descriptor = default_module_registry.get(module_id)
        if descriptor is not None and descriptor.installed_version:
            module_version = descriptor.installed_version
        from energy_core.db.installed_package_repo import InstalledPackageRepository

        package_row = await InstalledPackageRepository(self._session).get(module_id)
        if package_row is not None:
            module_version = package_row.installed_version
            package_checksum = package_row.checksum_sha256
        await publish_runtime_state(
            self._settings,
            site_id=site_id,
            module_id=module_id,
            runtime_state=runtime_state,
            last_error=last_error,
            module_version=module_version,
            package_checksum=package_checksum,
        )

    async def start_module(self, site_id: int, module_id: str) -> None:
        if not self._settings.module_gate_enabled:
            return

        descriptor = default_module_registry.get(module_id)
        if descriptor is None:
            return

        handle = self._runtime.get_handle(site_id, module_id)
        if handle.state == RuntimeStatus.RUNNING:
            logger.debug("ModuleStartRequested site_id=%s module_id=%s skipped=already_running", site_id, module_id)
            return
        if handle.state == RuntimeStatus.STARTING:
            return

        resolver = SiteModuleResolver(self._session, settings=self._settings, capability_registry=self._capabilities)
        enabled_map = await resolver.resolve_enabled_modules(site_id)
        if not enabled_map.get(module_id, False):
            self._runtime.mark_stopped(site_id, module_id)
            await self._emit_runtime_state(site_id, module_id, runtime_state=RuntimeStatus.STOPPED)
            return

        enabled_ids = set(enabled_map.keys())
        can_start = self._resolver.can_start(
            module_id,
            site_id=site_id,
            enabled_modules=enabled_ids,
            capability_registry=self._capabilities,
        )
        if not can_start.can_start:
            reason = ",".join(cap.value for cap in can_start.missing_required) or "dependencies"
            logger.info(
                "ModuleBlocked site_id=%s module_id=%s missing=%s",
                site_id,
                module_id,
                reason,
            )
            self._runtime.mark_blocked(site_id, module_id, reason=reason)
            await self._emit_runtime_state(site_id, module_id, runtime_state=RuntimeStatus.BLOCKED, last_error=reason)
            self._capabilities.unregister_module(site_id, module_id)
            await self._reevaluate_dependents(site_id, module_id)
            return

        logger.info("ModuleStartRequested site_id=%s module_id=%s", site_id, module_id)
        self._runtime.mark_starting(site_id, module_id)
        await self._emit_runtime_state(site_id, module_id, runtime_state=RuntimeStatus.STARTING)

        from energy_core.platform.modules.governance.publisher_repository import PublisherRepository

        publisher_row = None
        if descriptor.publisher:
            publisher_row = await PublisherRepository(self._session).get(descriptor.publisher)
        publisher_tier = publisher_row.tier if publisher_row else None
        if requires_isolated_runtime(descriptor, publisher_tier=publisher_tier):
            adapter = IsolatedModuleAdapter(self._session, self._settings)
            ctx = ModuleRuntimeContext(
                session_factory=self._session_factory,
                settings=self._settings,
                site_id=site_id,
                module_id=module_id,
                cancel_event=handle.cancel_event,
                extras=self._extras,
            )
            await adapter.start(ctx, publisher_tier=publisher_tier)
            current = await adapter._manager.list_runtimes(site_id=site_id)
            running = any(r.module_id == module_id and r.state.value == "RUNNING" for r in current)
            if running:
                await resolver.register_capabilities_for_module(site_id, module_id)
                self._runtime.mark_running(site_id, module_id)
                await self._emit_runtime_state(site_id, module_id, runtime_state=RuntimeStatus.RUNNING)
            else:
                self._runtime.mark_blocked(site_id, module_id, reason="isolated runtime blocked")
                await self._emit_runtime_state(
                    site_id,
                    module_id,
                    runtime_state=RuntimeStatus.BLOCKED,
                    last_error="isolated runtime blocked",
                )
            return

        handler = get_module_handler(module_id) or LaneModuleHandler(module_id)
        ctx = ModuleRuntimeContext(
            session_factory=self._session_factory,
            settings=self._settings,
            site_id=site_id,
            module_id=module_id,
            cancel_event=handle.cancel_event,
            extras=self._extras,
        )
        try:
            await handler.start(ctx)
            await resolver.register_capabilities_for_module(site_id, module_id)
            self._runtime.mark_running(site_id, module_id)
            await self._emit_runtime_state(site_id, module_id, runtime_state=RuntimeStatus.RUNNING)
            logger.info("ModuleStarted site_id=%s module_id=%s", site_id, module_id)
            logger.info("CapabilityRegistered site_id=%s module_id=%s", site_id, module_id)
            await self._reevaluate_dependents(site_id, module_id, try_start=True)
        except Exception as exc:
            self._runtime.mark_failed(site_id, module_id, error=str(exc))
            await self._emit_runtime_state(
                site_id,
                module_id,
                runtime_state=RuntimeStatus.FAILED,
                last_error=str(exc),
            )
            self._capabilities.unregister_module(site_id, module_id)
            logger.exception("ModuleFailed site_id=%s module_id=%s", site_id, module_id)

    async def stop_module(self, site_id: int, module_id: str) -> None:
        handle = self._runtime.get_handle(site_id, module_id)
        if handle.state in {RuntimeStatus.STOPPED, RuntimeStatus.STOPPING}:
            return

        logger.info("ModuleStopRequested site_id=%s module_id=%s", site_id, module_id)
        self._runtime.mark_stopping(site_id, module_id)
        await self._emit_runtime_state(site_id, module_id, runtime_state=RuntimeStatus.STOPPING)
        from energy_core.platform.modules.governance.publisher_repository import PublisherRepository

        descriptor = default_module_registry.get(module_id)
        publisher_tier = None
        if descriptor and descriptor.publisher:
            publisher_row = await PublisherRepository(self._session).get(descriptor.publisher)
            publisher_tier = publisher_row.tier if publisher_row else None
        if descriptor and requires_isolated_runtime(descriptor, publisher_tier=publisher_tier):
            adapter = IsolatedModuleAdapter(self._session, self._settings)
            ctx = ModuleRuntimeContext(
                session_factory=self._session_factory,
                settings=self._settings,
                site_id=site_id,
                module_id=module_id,
                cancel_event=handle.cancel_event,
                extras=self._extras,
            )
            await adapter.stop(ctx)
            self._capabilities.unregister_module(site_id, module_id)
            self._runtime.mark_stopped(site_id, module_id)
            await self._emit_runtime_state(site_id, module_id, runtime_state=RuntimeStatus.STOPPED)
            invalidate_site_module_cache(site_id)
            return

        handler = get_module_handler(module_id) or LaneModuleHandler(module_id)
        ctx = ModuleRuntimeContext(
            session_factory=self._session_factory,
            settings=self._settings,
            site_id=site_id,
            module_id=module_id,
            cancel_event=handle.cancel_event,
            extras=self._extras,
        )
        try:
            await handler.stop(ctx)
        except Exception as exc:
            logger.exception("Module stop error site_id=%s module_id=%s", site_id, module_id)
            self._runtime.mark_failed(site_id, module_id, error=str(exc))
            await self._emit_runtime_state(
                site_id,
                module_id,
                runtime_state=RuntimeStatus.FAILED,
                last_error=str(exc),
            )
            return
        finally:
            self._capabilities.unregister_module(site_id, module_id)
            self._runtime.mark_stopped(site_id, module_id)
            await self._emit_runtime_state(site_id, module_id, runtime_state=RuntimeStatus.STOPPED)
            invalidate_site_module_cache(site_id)
            logger.info("ModuleStopped site_id=%s module_id=%s", site_id, module_id)
            logger.info("CapabilityUnregistered site_id=%s module_id=%s", site_id, module_id)
            await self._reevaluate_dependents(site_id, module_id)

    async def sync_site(self, site_id: int) -> None:
        resolver = SiteModuleResolver(self._session, settings=self._settings, capability_registry=self._capabilities)
        enabled_map = await resolver.resolve_enabled_modules(site_id)
        desired = set(enabled_map.keys())
        running = set(self._runtime.active_modules_for_site(site_id))

        to_stop = running - desired
        stop_order = list(self._resolver.startup_order(tuple(to_stop)))
        stop_order.reverse()
        for module_id in stop_order:
            if module_id in to_stop:
                await self.stop_module(site_id, module_id)

        to_start = desired - running
        try:
            start_order = self._resolver.startup_order(tuple(desired))
        except ValueError as exc:
            logger.error("ModuleStartupOrderFailed site_id=%s error=%s", site_id, exc)
            return
        for module_id in start_order:
            if module_id in to_start or module_id in desired:
                current = self._runtime.get_state(site_id, module_id)
                if current != RuntimeStatus.RUNNING:
                    await self.start_module(site_id, module_id)

    async def start_all_sites(self) -> None:
        from energy_core.db.repositories import SiteRepository

        sites = await SiteRepository(self._session).list_all()
        for site in sites:
            await self.sync_site(site.id)

    async def _reevaluate_dependents(
        self,
        site_id: int,
        changed_module_id: str,
        *,
        try_start: bool = False,
    ) -> None:
        resolver = SiteModuleResolver(self._session, settings=self._settings, capability_registry=self._capabilities)
        enabled_map = await resolver.resolve_enabled_modules(site_id)
        enabled_ids = set(enabled_map.keys())
        for descriptor in default_module_registry.list_modules():
            if descriptor.module_id == changed_module_id:
                continue
            if descriptor.module_id not in enabled_ids:
                continue
            if changed_module_id not in descriptor.dependencies and not descriptor.capabilities_required:
                continue
            can_start = self._resolver.can_start(
                descriptor.module_id,
                site_id=site_id,
                enabled_modules=enabled_ids,
                capability_registry=self._capabilities,
            )
            if can_start.can_start:
                if try_start:
                    await self.start_module(site_id, descriptor.module_id)
                elif self._runtime.get_state(site_id, descriptor.module_id) == RuntimeStatus.BLOCKED:
                    await self.start_module(site_id, descriptor.module_id)
            else:
                current = self._runtime.get_state(site_id, descriptor.module_id)
                if current == RuntimeStatus.RUNNING:
                    await self.stop_module(site_id, descriptor.module_id)
                elif current != RuntimeStatus.STOPPED:
                    reason = ",".join(cap.value for cap in can_start.missing_required)
                    self._runtime.mark_blocked(site_id, descriptor.module_id, reason=reason)
                    await self._emit_runtime_state(
                        site_id,
                        descriptor.module_id,
                        runtime_state=RuntimeStatus.BLOCKED,
                        last_error=reason,
                    )

    async def reconcile_all_sites(self) -> None:
        from energy_core.db.repositories import SiteRepository

        sites = await SiteRepository(self._session).list_all()
        for site in sites:
            await self.sync_site(site.id)
