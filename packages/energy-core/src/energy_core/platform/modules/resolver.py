"""Module dependency resolution."""

from __future__ import annotations

from dataclasses import dataclass, field

from energy_core.platform.capabilities.registry import CapabilityRegistry
from energy_core.platform.capabilities.types import Capability
from energy_core.platform.modules.aliases import resolve_module_id
from energy_core.platform.modules.registry import ModuleDescriptor, ModuleRegistry, default_module_registry


@dataclass(frozen=True, slots=True)
class CanStartResult:
    can_start: bool
    missing_required: tuple[Capability, ...] = ()
    missing_optional: tuple[Capability, ...] = ()
    blocked_by_modules: tuple[str, ...] = ()
    missing_module_dependencies: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CanDisableResult:
    allowed: bool
    reason: str | None = None
    dependent_modules: tuple[str, ...] = ()


class ModuleDependencyResolver:
    def __init__(
        self,
        registry: ModuleRegistry | None = None,
        capability_registry: CapabilityRegistry | None = None,
    ) -> None:
        self._registry = registry or default_module_registry
        self._capabilities = capability_registry

    def startup_order(self, module_ids: tuple[str, ...]) -> tuple[str, ...]:
        graph = {resolve_module_id(mid): set() for mid in module_ids}
        for module_id in module_ids:
            canonical = resolve_module_id(module_id)
            descriptor = self._registry.get(canonical)
            if descriptor is None:
                continue
            graph[canonical] = {resolve_module_id(dep) for dep in descriptor.dependencies}

        ordered: list[str] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> None:
            if node in visiting:
                raise ValueError(f"Circular module dependency detected involving {node}")
            if node in visited:
                return
            visiting.add(node)
            for dep in graph.get(node, set()):
                if dep in graph:
                    visit(dep)
            visiting.remove(node)
            visited.add(node)
            ordered.append(node)

        for node in graph:
            visit(node)
        return tuple(ordered)

    def can_start(
        self,
        module_id: str,
        *,
        site_id: int,
        enabled_modules: set[str],
        capability_registry: CapabilityRegistry,
    ) -> CanStartResult:
        canonical = resolve_module_id(module_id)
        descriptor = self._registry.get(canonical)
        if descriptor is None:
            return CanStartResult(can_start=False, blocked_by_modules=(canonical,))

        missing_deps: list[str] = []
        for dep in descriptor.dependencies:
            dep_id = resolve_module_id(dep)
            if dep_id not in enabled_modules:
                missing_deps.append(dep_id)

        missing_required: list[Capability] = []
        for cap in descriptor.capabilities_required:
            if not capability_registry.site_has_capability(site_id, cap):
                missing_required.append(cap)

        missing_optional: list[Capability] = []
        for cap in descriptor.optional_capabilities:
            if not capability_registry.site_has_capability(site_id, cap):
                missing_optional.append(cap)

        can_start = not missing_deps and not missing_required
        return CanStartResult(
            can_start=can_start,
            missing_required=tuple(missing_required),
            missing_optional=tuple(missing_optional),
            missing_module_dependencies=tuple(missing_deps),
        )

    def can_disable(
        self,
        module_id: str,
        *,
        site_id: int,
        enabled_modules: set[str],
        capability_registry: CapabilityRegistry,
    ) -> CanDisableResult:
        canonical = resolve_module_id(module_id)
        descriptor = self._registry.get(canonical)
        if descriptor is not None and not descriptor.can_disable:
            return CanDisableResult(allowed=False, reason="Core module cannot be disabled")
        if canonical not in enabled_modules:
            return CanDisableResult(allowed=True)

        dependents: list[str] = []
        for other_id in enabled_modules:
            if other_id == canonical:
                continue
            descriptor = self._registry.get(other_id)
            if descriptor is None:
                continue
            if canonical in {resolve_module_id(dep) for dep in descriptor.dependencies}:
                dependents.append(other_id)
                continue
            module_caps = self._module_provided_capabilities(canonical)
            if not module_caps or not descriptor.capabilities_required:
                continue
            for req in descriptor.capabilities_required:
                if req in module_caps and not self._other_providers_exist(
                    site_id, req, canonical, capability_registry
                ):
                    dependents.append(other_id)
                    break

        if dependents:
            return CanDisableResult(
                allowed=False,
                reason="Other enabled modules depend on capabilities from this module",
                dependent_modules=tuple(sorted(set(dependents))),
            )
        return CanDisableResult(allowed=True)

    def _module_provided_capabilities(self, module_id: str) -> set[Capability]:
        descriptor = self._registry.get(module_id)
        if descriptor is None:
            return set()
        return set(descriptor.capabilities_provided)

    def _other_providers_exist(
        self,
        site_id: int,
        capability: Capability,
        excluding_module: str,
        capability_registry: CapabilityRegistry,
    ) -> bool:
        providers = capability_registry.providers_for(site_id, capability)
        return any(item.module_id != excluding_module for item in providers)


default_module_dependency_resolver = ModuleDependencyResolver()
