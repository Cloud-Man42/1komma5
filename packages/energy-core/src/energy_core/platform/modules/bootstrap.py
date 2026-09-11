"""Register default EMIC modules at application startup."""

from __future__ import annotations

from energy_core.platform.capabilities.types import Capability
from energy_core.platform.modules.aliases import CANONICAL_TO_LEGACY
from energy_core.platform.modules.onboarding_schemas import (
    ARCTIC_SPA_CONFIG_SCHEMA,
    CHARGEAMPS_CONFIG_SCHEMA,
    HEARTBEAT_CONFIG_SCHEMA,
    MERCEDES_CONFIG_SCHEMA,
)
from energy_core.platform.modules.registry import ModuleDescriptor, default_module_registry
from energy_core.platform.modules.types import ModuleType

_DEFAULT_MODULES: tuple[ModuleDescriptor, ...] = (
    ModuleDescriptor(
        module_id="integration.heartbeat",
        name="1Komma5 Heartbeat",
        version="1.0.0",
        module_type=ModuleType.INTEGRATION,
        description="Energy telemetry and EV bridge via Heartbeat API",
        capabilities_provided=(
            Capability.ENERGY_READ_GRID_POWER,
            Capability.ENERGY_READ_SOLAR_POWER,
            Capability.BATTERY_READ_SOC,
            Capability.BATTERY_READ_POWER,
            Capability.PRICE_READ_CURRENT,
            Capability.PRICE_READ_FORECAST,
        ),
        configuration_schema=HEARTBEAT_CONFIG_SCHEMA,
        onboardable=True,
        device_categories=("energy_provider",),
        connection_types=("api", "credentials"),
        onboard_handler="heartbeat",
        supports_discovery=True,
        can_disable=False,
    ),
    ModuleDescriptor(
        module_id="integration.chargeamps",
        name="Charge Amps",
        version="1.0.0",
        module_type=ModuleType.INTEGRATION,
        description="Charge Amps Halo EV charger control",
        capabilities_provided=(
            Capability.EV_CHARGER_START,
            Capability.EV_CHARGER_STOP,
            Capability.EV_CHARGER_SET_CURRENT,
            Capability.EV_CHARGER_READ_POWER,
            Capability.EV_CHARGER_READ_ENERGY,
        ),
        configuration_schema=CHARGEAMPS_CONFIG_SCHEMA,
        onboardable=True,
        device_categories=("ev_charger",),
        connection_types=("api_key", "credentials"),
        onboard_handler="chargeamps",
        supports_discovery=True,
    ),
    ModuleDescriptor(
        module_id="integration.mercedes",
        name="Mercedes-Benz",
        version="1.0.0",
        module_type=ModuleType.INTEGRATION,
        description="Mercedes vehicle telematics",
        capabilities_provided=(
            Capability.VEHICLE_READ_SOC,
            Capability.VEHICLE_READ_RANGE,
            Capability.VEHICLE_READ_CHARGING_STATE,
        ),
        configuration_schema=MERCEDES_CONFIG_SCHEMA,
        onboardable=True,
        device_categories=("vehicle",),
        connection_types=("oauth", "credentials"),
        onboard_handler="mercedes",
    ),
    ModuleDescriptor(
        module_id="integration.arctic_spa",
        name="Arctic Spa",
        version="1.0.0",
        module_type=ModuleType.INTEGRATION,
        description="Arctic Spa hot tub integration",
        capabilities_provided=(
            Capability.SPA_READ_TEMPERATURE,
            Capability.READ_POWER,
        ),
        configuration_schema=ARCTIC_SPA_CONFIG_SCHEMA,
        onboardable=True,
        device_categories=("spa",),
        connection_types=("api_key",),
        onboard_handler="arctic_spa",
    ),
    ModuleDescriptor(
        module_id="integration.chargefinder",
        name="ChargeFinder",
        version="1.0.0",
        module_type=ModuleType.INTEGRATION,
        description="Away charging station lookup via ChargeFinder",
        capabilities_provided=(Capability.READ_STATUS,),
    ),
    ModuleDescriptor(
        module_id="integration.smhi",
        name="SMHI Weather",
        version="1.0.0",
        module_type=ModuleType.INTEGRATION,
        description="SMHI STRÅNG and SNOW weather data for solar intelligence",
        capabilities_provided=(
            Capability.WEATHER_READ_FORECAST,
            Capability.WEATHER_READ_CURRENT,
        ),
    ),
    ModuleDescriptor(
        module_id="integration.dmi",
        name="DMI Harmonie",
        version="1.0.0",
        module_type=ModuleType.INTEGRATION,
        description="DMI Harmonie weather forecast for Denmark solar intelligence",
        capabilities_provided=(Capability.WEATHER_READ_FORECAST,),
    ),
    ModuleDescriptor(
        module_id="integration.open_meteo",
        name="Open-Meteo",
        version="1.0.0",
        module_type=ModuleType.INTEGRATION,
        description="Open-Meteo weather fallback for solar forecast",
        capabilities_provided=(Capability.WEATHER_READ_FORECAST,),
    ),
    ModuleDescriptor(
        module_id="feature.smart-charging",
        name="Smart Charging",
        version="1.0.0",
        module_type=ModuleType.FEATURE,
        description="Smart EV charging orchestration",
        capabilities_provided=(Capability.SMART_CHARGING,),
        capabilities_required=(
            Capability.EV_CHARGER_START,
            Capability.EV_CHARGER_STOP,
        ),
        optional_capabilities=(
            Capability.ENERGY_READ_GRID_POWER,
            Capability.BATTERY_READ_SOC,
            Capability.FORECAST_SOLAR,
            Capability.PRICE_READ_FORECAST,
            Capability.VEHICLE_READ_SOC,
        ),
    ),
    ModuleDescriptor(
        module_id="feature.vehicles",
        name="Vehicle Integration",
        version="1.0.0",
        module_type=ModuleType.FEATURE,
        dependencies=("integration.mercedes",),
        capabilities_provided=(Capability.READ_STATUS,),
    ),
    ModuleDescriptor(
        module_id="feature.spa-energy",
        name="Spa Energy",
        version="1.0.0",
        module_type=ModuleType.FEATURE,
        dependencies=("integration.arctic_spa",),
        capabilities_provided=(Capability.READ_POWER,),
    ),
    ModuleDescriptor(
        module_id="feature.energy-balance",
        name="Energy Balance",
        version="1.0.0",
        module_type=ModuleType.FEATURE,
        dependencies=("feature.smart-charging",),
    ),
    ModuleDescriptor(
        module_id="feature.solar-forecast",
        name="Solar Forecast",
        version="1.0.0",
        module_type=ModuleType.FEATURE,
        capabilities_provided=(Capability.FORECAST_SOLAR, Capability.READ_POWER),
    ),
    ModuleDescriptor(
        module_id="feature.price-engine",
        name="Price Engine",
        version="1.0.0",
        module_type=ModuleType.FEATURE,
        dependencies=("integration.heartbeat",),
        capabilities_provided=(Capability.PRICE_READ_CURRENT, Capability.PRICE_READ_FORECAST),
    ),
    ModuleDescriptor(
        module_id="feature.energy-control",
        name="Energy Control",
        version="1.0.0",
        module_type=ModuleType.FEATURE,
        dependencies=("integration.heartbeat",),
        capabilities_provided=(Capability.OPTIMIZATION_ENERGY,),
    ),
)


def register_default_modules() -> None:
    """Idempotent registration of static module descriptors."""
    for descriptor in _DEFAULT_MODULES:
        if default_module_registry.get(descriptor.module_id) is None:
            default_module_registry.register(descriptor)
    for canonical_id, legacy_id in CANONICAL_TO_LEGACY.items():
        if default_module_registry.get(legacy_id) is not None:
            continue
        canonical = default_module_registry.get(canonical_id)
        if canonical is None:
            continue
        default_module_registry.register(
            ModuleDescriptor(
                module_id=legacy_id,
                name=f"{canonical.name} (legacy alias)",
                version=canonical.version,
                module_type=canonical.module_type,
                description=f"Legacy alias for {canonical_id}",
                dependencies=canonical.dependencies,
                capabilities_provided=canonical.capabilities_provided,
                capabilities_required=canonical.capabilities_required,
                optional_capabilities=canonical.optional_capabilities,
                configuration_schema=canonical.configuration_schema,
                onboardable=canonical.onboardable,
                device_categories=canonical.device_categories,
                connection_types=canonical.connection_types,
                can_disable=canonical.can_disable,
                onboard_handler=canonical.onboard_handler,
                supports_discovery=canonical.supports_discovery,
            )
        )
