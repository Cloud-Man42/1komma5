"""Serialize module descriptors for API responses."""

from __future__ import annotations

from typing import Any


def serialize_module_descriptor(module) -> dict[str, Any]:
    from energy_core.platform.modules.aliases import CANONICAL_TO_LEGACY

    return {
        "module_id": module.module_id,
        "legacy_module_id": CANONICAL_TO_LEGACY.get(module.module_id),
        "name": module.name,
        "version": module.version,
        "module_type": module.module_type.value,
        "description": module.description,
        "dependencies": list(module.dependencies),
        "capabilities_provided": [cap.value for cap in module.capabilities_provided],
        "capabilities_required": [cap.value for cap in module.capabilities_required],
        "optional_capabilities": [cap.value for cap in module.optional_capabilities],
        "supports_per_site_activation": module.supports_per_site_activation,
        "configuration_schema": dict(module.configuration_schema),
        "onboardable": module.onboardable,
        "device_categories": list(module.device_categories),
        "connection_types": list(module.connection_types),
        "can_disable": module.can_disable,
        "onboard_handler": module.onboard_handler,
        "supports_discovery": module.supports_discovery,
    }
