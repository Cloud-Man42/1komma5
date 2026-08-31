"""Create vendor-neutral charger adapters from persisted configuration."""

from __future__ import annotations

import os

from energy_core.chargers.charge_amps import build_chargeamps_controller
from energy_core.chargers.framework.adapters.charge_amps import ChargeAmpsFrameworkAdapter
from energy_core.chargers.framework.adapters.unsupported import UnsupportedChargerAdapter
from energy_core.chargers.framework.catalog import CHARGE_AMPS_CLOUD, get_integration_method
from energy_core.chargers.framework.models import ChargerAdapter, ChargerConfiguration
from energy_core.chargers.halo_adapter import ChargeAmpsHaloAdapter, build_halo_adapter
from energy_core.chargers.mock import MockChargeAmpsController
from energy_core.db.models import EvChargerModel
from energy_core.secrets import CredentialCipher


class ChargerAdapterFactory:
    """Select adapter implementation from manufacturer/model/integration method."""

    @staticmethod
    def from_charger_model(charger: EvChargerModel) -> ChargerAdapter:
        config = configuration_from_model(charger)
        return ChargerAdapterFactory.create(config)

    @staticmethod
    def create(config: ChargerConfiguration) -> ChargerAdapter:
        method = get_integration_method(config.integration_method)
        if method is None:
            return UnsupportedChargerAdapter(
                manufacturer_id=config.manufacturer_id,
                model_id=config.model_id,
                integration_method=config.integration_method,
            )

        if config.integration_method == CHARGE_AMPS_CLOUD:
            return _build_charge_amps(config)

        if config.integration_method.startswith("OCPP"):
            return UnsupportedChargerAdapter(
                manufacturer_id=config.manufacturer_id,
                model_id=config.model_id,
                integration_method=config.integration_method,
            )

        return UnsupportedChargerAdapter(
            manufacturer_id=config.manufacturer_id,
            model_id=config.model_id,
            integration_method=config.integration_method,
        )


def configuration_from_model(charger: EvChargerModel) -> ChargerConfiguration:
    manufacturer_id = charger.manufacturer_id or _legacy_manufacturer_id(charger.manufacturer)
    model_id = charger.model_id or _legacy_model_id(charger.model)
    integration_method = charger.integration_method or _legacy_integration_method(charger.control_source)
    connection_settings = _parse_connection_settings(charger.connection_settings)
    external_id = (
        connection_settings.get("charger_id")
        or charger.chargeamp_charger_id
        or charger.external_charger_id
    )
    return ChargerConfiguration(
        charger_id=charger.id,
        site_id=charger.site_id,
        manufacturer_id=manufacturer_id,
        model_id=model_id,
        integration_method=integration_method,
        display_name=charger.name,
        enabled=charger.bridge_enabled,
        external_charger_id=str(external_id) if external_id else None,
        api_key=CredentialCipher().decrypt(charger.chargeamps_api_key) or None,
        connection_settings=connection_settings,
        min_current_a=charger.min_current_a,
        max_current_a=charger.max_current_a,
        phases=charger.phases,
        nominal_voltage_v=charger.nominal_voltage_v,
        legacy_control_source=charger.control_source,
    )


def _build_charge_amps(config: ChargerConfiguration) -> ChargerAdapter:
    charger_id = config.external_charger_id or f"mock-{config.charger_id}"
    api_key = config.api_key or os.getenv("CHARGEAMPS_API_KEY", "")
    email = os.getenv("CHARGEAMPS_EMAIL", "")
    password = os.getenv("CHARGEAMPS_PASSWORD", "")
    use_mock = os.getenv("CHARGEAMPS_MOCK", "true").lower() in {"1", "true", "yes"}

    if not use_mock and api_key:
        inner = build_halo_adapter(
            charger_id,
            api_key=api_key,
            email=email,
            password=password,
            min_current_a=config.min_current_a,
            max_current_a=config.max_current_a,
            phases=config.phases,
        )
        return ChargeAmpsFrameworkAdapter(
            inner,
            charger_id=charger_id,
            manufacturer_id=config.manufacturer_id,
            model_id=config.model_id,
        )

    controller = build_chargeamps_controller(
        charger_id,
        api_key=api_key,
        email=email,
        password=password,
        use_mock=use_mock,
        min_current_a=config.min_current_a,
        max_current_a=config.max_current_a,
        phases=config.phases,
    )
    from energy_core.chargers.charge_amps import ChargeAmpsExternalController, MockChargeAmpsController

    if isinstance(controller, ChargeAmpsExternalController) and controller._adapter is not None:
        inner = controller._adapter
    elif isinstance(controller, MockChargeAmpsController):
        inner = _MockInnerAdapter(controller, config)
    else:
        inner = _ControllerInnerAdapter(controller, config)
    return ChargeAmpsFrameworkAdapter(
        inner,
        charger_id=charger_id,
        manufacturer_id=config.manufacturer_id,
        model_id=config.model_id,
    )


class _MockInnerAdapter(ChargeAmpsHaloAdapter):
    def __init__(self, mock: MockChargeAmpsController, config: ChargerConfiguration) -> None:
        self._mock = mock
        self._min_current_a = config.min_current_a
        self._max_current_a = config.max_current_a
        self._phases = config.phases

    async def get_status(self):
        return await self._mock.get_status()

    async def set_current(self, amps: float) -> None:
        await self._mock.set_current_limit(amps)

    async def get_current(self) -> float:
        status = await self._mock.get_status()
        return status.current_limit_a or 0.0

    async def get_power(self) -> float:
        return 0.0

    async def start_charging(self) -> None:
        await self._mock.start_charging()

    async def stop_charging(self) -> None:
        await self._mock.stop_charging()

    async def is_connected(self) -> bool:
        return await self._mock.is_connected()

    async def is_vehicle_connected(self) -> bool:
        return await self._mock.is_vehicle_connected()

    async def get_capabilities(self):
        from energy_core.chargers.capabilities import ChargerCapabilities as LegacyCaps

        return LegacyCaps(
            min_current_a=self._min_current_a,
            max_current_a=self._max_current_a,
            phases=self._phases,
            supports_current_control=True,
            supports_remote_start_stop=True,
            supports_power_reading=True,
            supports_dynamic_phases=False,
        )


class _ControllerInnerAdapter(ChargeAmpsHaloAdapter):
    def __init__(self, controller, config: ChargerConfiguration) -> None:
        self._controller = controller
        self._min_current_a = config.min_current_a
        self._max_current_a = config.max_current_a
        self._phases = config.phases

    async def get_status(self):
        return await self._controller.get_status()

    async def set_current(self, amps: float) -> None:
        await self._controller.set_current_limit(amps)

    async def get_current(self) -> float:
        status = await self._controller.get_status()
        return status.current_limit_a or 0.0

    async def get_power(self) -> float:
        return 0.0

    async def start_charging(self) -> None:
        await self._controller.start_charging()

    async def stop_charging(self) -> None:
        await self._controller.stop_charging()

    async def is_connected(self) -> bool:
        return await self._controller.is_connected()

    async def is_vehicle_connected(self) -> bool:
        return await self._controller.is_vehicle_connected()

    async def get_capabilities(self):
        from energy_core.chargers.capabilities import ChargerCapabilities as LegacyCaps

        return LegacyCaps(
            min_current_a=self._min_current_a,
            max_current_a=self._max_current_a,
            phases=self._phases,
            supports_current_control=True,
            supports_remote_start_stop=True,
            supports_power_reading=False,
            supports_dynamic_phases=False,
        )


def _legacy_manufacturer_id(name: str) -> str:
    normalized = name.strip().lower().replace(" ", "-")
    mapping = {"chargeamps": "charge-amps", "charge-amps": "charge-amps"}
    return mapping.get(normalized, normalized or "unknown")


def _legacy_model_id(name: str) -> str:
    return name.strip().lower().replace(" ", "-") or "unknown"


def _legacy_integration_method(control_source: str) -> str:
    if control_source == "chargeamp":
        return CHARGE_AMPS_CLOUD
    return control_source


def _parse_connection_settings(raw: str | None) -> dict:
    if not raw:
        return {}
    import json

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
