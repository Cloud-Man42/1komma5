"""Site-aware capability provider registry."""

from __future__ import annotations

from dataclasses import dataclass, field

from energy_core.platform.capabilities.types import Capability


@dataclass(frozen=True, slots=True)
class CapabilityProvider:
    site_id: int
    module_id: str
    capability: Capability
    device_id: str | None = None


@dataclass
class CapabilityRegistry:
    """Index of which module provides which capability for a site."""

    _providers: dict[tuple[int, Capability], list[CapabilityProvider]] = field(default_factory=dict)

    def clear_site(self, site_id: int) -> None:
        keys = [key for key in self._providers if key[0] == site_id]
        for key in keys:
            del self._providers[key]

    def unregister_module(self, site_id: int, module_id: str) -> None:
        keys_to_delete: list[tuple[int, Capability]] = []
        for key, providers in self._providers.items():
            if key[0] != site_id:
                continue
            remaining = [item for item in providers if item.module_id != module_id]
            if len(remaining) != len(providers):
                if remaining:
                    self._providers[key] = remaining
                else:
                    keys_to_delete.append(key)
        for key in keys_to_delete:
            del self._providers[key]

    def register_provider(
        self,
        *,
        site_id: int,
        module_id: str,
        capability: Capability,
        device_id: str | None = None,
    ) -> None:
        provider = CapabilityProvider(
            site_id=site_id,
            module_id=module_id,
            capability=capability,
            device_id=device_id,
        )
        key = (site_id, capability)
        bucket = self._providers.setdefault(key, [])
        if not any(item.module_id == module_id and item.device_id == device_id for item in bucket):
            bucket.append(provider)

    def providers_for(self, site_id: int, capability: Capability) -> tuple[CapabilityProvider, ...]:
        return tuple(self._providers.get((site_id, capability), ()))

    def site_has_capability(self, site_id: int, capability: Capability) -> bool:
        return bool(self.providers_for(site_id, capability))

    def capabilities_for_site(self, site_id: int) -> set[Capability]:
        return {cap for (sid, cap) in self._providers if sid == site_id}


default_capability_registry = CapabilityRegistry()
