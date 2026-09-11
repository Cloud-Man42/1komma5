"""Integration-specific onboarding handlers (read-only test + discovery)."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings, get_settings
from energy_core.db.consumer_repo import ConsumerRepository
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.heartbeat_settings_repo import HeartbeatSettingsRepository
from energy_core.db.models import SiteModel
from energy_core.db.vehicle_repo import VehicleProviderRepository
from energy_core.integrations.arctic_spa.factory import ArcticSpaConfiguration, build_arctic_spa_service
from energy_core.integrations.chargeamps.config import build_chargeamps_connection_info
from energy_core.integrations.heartbeat.config import build_heartbeat_connection_info
from energy_core.platform.modules.onboarding.types import (
    CapabilityProbe,
    ConnectionTestResult,
    DiscoveryDevice,
    DiscoveryResult,
)
from energy_core.providers.vehicle_integrations import MercedesAuthError, build_mercedes_provider
from energy_core.secrets import SecretBox


class OnboardHandler(ABC):
    handler_id: str

    def __init__(self, session: AsyncSession, *, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings or get_settings()

    @abstractmethod
    async def configured_secrets(self, site_id: int) -> set[str]:
        raise NotImplementedError

    @abstractmethod
    async def test_connection(self, site_id: int) -> ConnectionTestResult:
        raise NotImplementedError

    async def discover(self, site_id: int) -> DiscoveryResult:
        return DiscoveryResult(supported=False, message="Discovery not supported for this module")


class HeartbeatOnboardHandler(OnboardHandler):
    handler_id = "heartbeat"

    async def configured_secrets(self, site_id: int) -> set[str]:
        repo = HeartbeatSettingsRepository(self._session)
        record = await repo.get_record()
        info = build_heartbeat_connection_info(record, await repo.list_site_mappings())
        configured: set[str] = set()
        if info.password_configured:
            configured.add("password")
        if info.api_token_configured:
            configured.add("api_token")
        return configured

    async def test_connection(self, site_id: int) -> ConnectionTestResult:
        start = time.perf_counter()
        repo = HeartbeatSettingsRepository(self._session)
        record = await repo.get_record()
        sites = await repo.list_site_mappings()
        info = build_heartbeat_connection_info(record, sites)
        site = await self._session.get(SiteModel, site_id)
        external_id = site.external_system_id if site else None
        ready = bool(info.api_token_configured or info.password_configured) and bool(external_id)
        latency = int((time.perf_counter() - start) * 1000)
        caps = (
            CapabilityProbe(name="energy.read.grid_power", kind="read", available=ready),
            CapabilityProbe(name="energy.read.solar_power", kind="read", available=ready),
            CapabilityProbe(name="price.read.current", kind="read", available=ready),
        )
        if not external_id:
            return ConnectionTestResult(
                success=False,
                message="Heartbeat system ID is not configured for this site",
                capabilities=caps,
                latency_ms=latency,
            )
        if not (info.api_token_configured or info.password_configured):
            return ConnectionTestResult(
                success=False,
                message="Heartbeat credentials are not configured",
                capabilities=caps,
                latency_ms=latency,
            )
        return ConnectionTestResult(
            success=True,
            message="Heartbeat configuration looks valid",
            capabilities=caps,
            latency_ms=latency,
        )

    async def discover(self, site_id: int) -> DiscoveryResult:
        return DiscoveryResult(
            supported=True,
            message="Use Heartbeat bridge EV discovery from the EV dashboard",
        )


class ChargeAmpsOnboardHandler(OnboardHandler):
    handler_id = "chargeamps"

    async def configured_secrets(self, site_id: int) -> set[str]:
        repo = EvChargerRepository(self._session)
        configured: set[str] = set()
        info = build_chargeamps_connection_info(
            charger_api_keys_configured=await repo.count_with_chargeamps_api_key(),
        )
        if info.api_key_configured or info.env_api_key_configured:
            configured.add("api_key")
        if info.password_configured:
            configured.add("password")
        chargers = await repo.list_for_site(site_id)
        if any(repo.decrypt_chargeamps_api_key(charger) for charger in chargers if charger.chargeamps_api_key):
            configured.add("api_key")
        return configured

    async def test_connection(self, site_id: int) -> ConnectionTestResult:
        start = time.perf_counter()
        repo = EvChargerRepository(self._session)
        chargers = await repo.list_bridge_enabled_with_sites()
        site_chargers = [c for c in chargers if c.site_id == site_id]
        info = build_chargeamps_connection_info(
            charger_api_keys_configured=await repo.count_with_chargeamps_api_key(),
        )
        latency = int((time.perf_counter() - start) * 1000)
        devices = tuple(
            DiscoveryDevice(
                external_id=charger.external_charger_id or charger.chargeamp_charger_id or str(charger.id),
                name=charger.name,
                device_type="ev_charger",
                manufacturer=charger.manufacturer,
                model=charger.model,
            )
            for charger in site_chargers
        )
        caps = (
            CapabilityProbe(name="ev_charger.start", kind="control", available=info.ready),
            CapabilityProbe(name="ev_charger.read_power", kind="read", available=info.ready),
        )
        if not info.ready:
            return ConnectionTestResult(
                success=False,
                message="Charge Amps credentials or charger API keys are not configured",
                devices_found=devices,
                capabilities=caps,
                latency_ms=latency,
            )
        return ConnectionTestResult(
            success=True,
            message=f"Charge Amps ready ({len(devices)} bridge-enabled charger(s) on site)",
            devices_found=devices,
            capabilities=caps,
            latency_ms=latency,
        )

    async def discover(self, site_id: int) -> DiscoveryResult:
        repo = EvChargerRepository(self._session)
        chargers = await repo.list_for_site(site_id)
        devices = tuple(
            DiscoveryDevice(
                external_id=charger.external_charger_id or charger.chargeamp_charger_id or str(charger.id),
                name=charger.name,
                device_type="ev_charger",
                manufacturer=charger.manufacturer,
                model=charger.model,
            )
            for charger in chargers
        )
        return DiscoveryResult(supported=True, devices=devices, message=f"Found {len(devices)} charger(s)")


class MercedesOnboardHandler(OnboardHandler):
    handler_id = "mercedes"

    async def configured_secrets(self, site_id: int) -> set[str]:
        repo = VehicleProviderRepository(self._session, secret_box=SecretBox.from_settings())
        row = await repo.get_for_site(site_id)
        configured: set[str] = set()
        if row and row.encrypted_password:
            configured.add("password")
        if row and repo.load_token_bundle(row) is not None:
            configured.add("oauth_token")
        return configured

    async def test_connection(self, site_id: int) -> ConnectionTestResult:
        start = time.perf_counter()
        repo = VehicleProviderRepository(self._session, secret_box=SecretBox.from_settings())
        row = await repo.get_for_site(site_id)
        if row is None or not row.enabled:
            return ConnectionTestResult(
                success=False,
                message="Mercedes integration is not enabled for this site",
                latency_ms=int((time.perf_counter() - start) * 1000),
            )
        token_bundle = repo.load_token_bundle(row)
        if token_bundle is None:
            return ConnectionTestResult(
                success=False,
                message="Mercedes is not authenticated",
                latency_ms=int((time.perf_counter() - start) * 1000),
            )
        provider = build_mercedes_provider(row, token_bundle=token_bundle)
        try:
            states = await provider.sync_from_rest()
            latency = int((time.perf_counter() - start) * 1000)
            devices = tuple(
                DiscoveryDevice(
                    external_id=state.vehicle_id,
                    name=state.model or state.vehicle_id,
                    device_type="vehicle",
                    manufacturer="Mercedes-Benz",
                    model=state.model or "",
                    metadata={"vin": state.vin} if state.vin else {},
                )
                for state in states
            )
            caps = (
                CapabilityProbe(name="vehicle.read_soc", kind="read", available=bool(states)),
                CapabilityProbe(name="vehicle.read_range", kind="read", available=bool(states)),
            )
            return ConnectionTestResult(
                success=True,
                message=f"Connected to Mercedes ({len(devices)} vehicle(s) found)",
                devices_found=devices,
                capabilities=caps,
                latency_ms=latency,
            )
        except MercedesAuthError as exc:
            return ConnectionTestResult(
                success=False,
                message=str(exc),
                latency_ms=int((time.perf_counter() - start) * 1000),
            )
        except Exception as exc:
            return ConnectionTestResult(
                success=False,
                message=str(exc),
                latency_ms=int((time.perf_counter() - start) * 1000),
            )
        finally:
            await provider.close()


class ArcticSpaOnboardHandler(OnboardHandler):
    handler_id = "arctic_spa"

    async def configured_secrets(self, site_id: int) -> set[str]:
        repo = ConsumerRepository(self._session)
        existing = await repo.get_spa_for_site(site_id)
        configured: set[str] = set()
        if existing is not None:
            _consumer, config = existing
            if repo.decrypt_spa_api_key(config):
                configured.add("api_key")
        return configured

    async def test_connection(self, site_id: int) -> ConnectionTestResult:
        start = time.perf_counter()
        repo = ConsumerRepository(self._session)
        existing = await repo.get_spa_for_site(site_id)
        if existing is None:
            return ConnectionTestResult(
                success=False,
                message="No Arctic Spa consumer configured for this site",
                latency_ms=int((time.perf_counter() - start) * 1000),
            )
        consumer, config = existing
        cfg = ArcticSpaConfiguration.merge(
            db_enabled=True,
            db_base_url=config.api_base_url,
            db_api_key=repo.decrypt_spa_api_key(config),
            db_spa_id=config.external_spa_id,
        )
        result = await build_arctic_spa_service(cfg).test_connection()
        latency = int((time.perf_counter() - start) * 1000)
        devices = ()
        if result.spa_found:
            devices = (
                DiscoveryDevice(
                    external_id=config.external_spa_id or str(consumer.id),
                    name=consumer.name,
                    device_type="spa",
                    manufacturer="Arctic Spa",
                    model="Hot tub",
                ),
            )
        caps = (
            CapabilityProbe(name="spa.read_temperature", kind="read", available=result.success),
            CapabilityProbe(name="read.power", kind="read", available=result.success),
        )
        return ConnectionTestResult(
            success=result.success,
            message=result.message,
            devices_found=devices,
            capabilities=caps,
            latency_ms=latency,
        )


class SensiboOnboardHandler(OnboardHandler):
    handler_id = "sensibo"

    async def configured_secrets(self, site_id: int) -> set[str]:
        from energy_core.climate.external_config import ExternalModuleConfigService

        if await ExternalModuleConfigService(self._session).credential_configured(
            site_id=site_id, module_id="integration.sensibo"
        ):
            return {"api_key"}
        return set()

    async def test_connection(self, site_id: int) -> ConnectionTestResult:
        import json
        import time

        from energy_core.climate.external_config import ExternalModuleConfigService
        from energy_core.platform.modules.brokers.network_broker import NetworkBroker
        from energy_core.secrets import CredentialCipher

        start = time.perf_counter()
        row = await ExternalModuleConfigService(self._session).get(site_id=site_id, module_id="integration.sensibo")
        if row is None or not row.credential_encrypted:
            return ConnectionTestResult(
                success=False,
                message="Sensibo API key not configured",
                latency_ms=int((time.perf_counter() - start) * 1000),
            )
        api_key = CredentialCipher().decrypt(row.credential_encrypted)
        broker = NetworkBroker(self._settings)
        broker.allow_host(module_id="integration.sensibo", site_id=site_id, host="home.sensibo.com")
        try:
            response = await broker.request(
                runtime_instance_id="onboard-probe",
                module_id="integration.sensibo",
                site_id=site_id,
                url="https://home.sensibo.com/api/v2/users/me/pods",
                method="GET",
                permissions=("network.external",),
                headers={"X-API-KEY": api_key, "Accept": "application/json"},
            )
            status = int(response.get("status_code") or 0)
            success = status == 200
            message = "Sensibo API reachable" if success else f"Sensibo API returned {status}"
            if success:
                body = json.loads(response.get("body") or "{}")
                pods = body.get("result") if isinstance(body, dict) else []
                count = len(pods) if isinstance(pods, list) else 0
                message = f"Sensibo API reachable ({count} device(s))"
        except Exception as exc:
            success = False
            message = str(exc)
        latency = int((time.perf_counter() - start) * 1000)
        caps = (
            CapabilityProbe(name="hvac.read_temperature", kind="read", available=success),
            CapabilityProbe(name="hvac.read_humidity", kind="read", available=success),
            CapabilityProbe(name="hvac.read_status", kind="read", available=success),
        )
        return ConnectionTestResult(success=success, message=message, capabilities=caps, latency_ms=latency)

    async def discover(self, site_id: int) -> DiscoveryResult:
        import json

        from energy_core.climate.external_config import ExternalModuleConfigService
        from energy_core.platform.modules.brokers.network_broker import NetworkBroker
        from energy_core.secrets import CredentialCipher

        row = await ExternalModuleConfigService(self._session).get(site_id=site_id, module_id="integration.sensibo")
        if row is None or not row.credential_encrypted:
            return DiscoveryResult(supported=False, message="Configure Sensibo API key first")
        api_key = CredentialCipher().decrypt(row.credential_encrypted)
        broker = NetworkBroker(self._settings)
        broker.allow_host(module_id="integration.sensibo", site_id=site_id, host="home.sensibo.com")
        try:
            response = await broker.request(
                runtime_instance_id="onboard-probe",
                module_id="integration.sensibo",
                site_id=site_id,
                url="https://home.sensibo.com/api/v2/users/me/pods",
                method="GET",
                permissions=("network.external",),
                headers={"X-API-KEY": api_key, "Accept": "application/json"},
            )
            if int(response.get("status_code") or 0) != 200:
                return DiscoveryResult(supported=True, message="Discovery failed", devices=())
            body = json.loads(response.get("body") or "{}")
            pods = body.get("result") if isinstance(body, dict) else []
            devices = []
            if isinstance(pods, list):
                for pod in pods:
                    if not isinstance(pod, dict):
                        continue
                    pod_id = str(pod.get("id") or pod.get("deviceUid") or "")
                    devices.append(
                        DiscoveryDevice(
                            external_id=pod_id,
                            name=str(pod.get("room") or pod.get("productModel") or pod_id),
                            device_type="climate",
                            manufacturer="Sensibo",
                            model=str(pod.get("productModel") or "AC"),
                            online=pod.get("connectionStatus") == "Connected",
                        )
                    )
            return DiscoveryResult(supported=True, message=f"Found {len(devices)} device(s)", devices=tuple(devices))
        except Exception as exc:
            return DiscoveryResult(supported=True, message=str(exc), devices=())


_HANDLERS: dict[str, type[OnboardHandler]] = {
    HeartbeatOnboardHandler.handler_id: HeartbeatOnboardHandler,
    ChargeAmpsOnboardHandler.handler_id: ChargeAmpsOnboardHandler,
    MercedesOnboardHandler.handler_id: MercedesOnboardHandler,
    ArcticSpaOnboardHandler.handler_id: ArcticSpaOnboardHandler,
    SensiboOnboardHandler.handler_id: SensiboOnboardHandler,
}


def get_onboard_handler(handler_id: str, session: AsyncSession, *, settings: Settings | None = None) -> OnboardHandler:
    cls = _HANDLERS.get(handler_id)
    if cls is None:
        raise KeyError(f"Unknown onboard handler: {handler_id}")
    return cls(session, settings=settings)
