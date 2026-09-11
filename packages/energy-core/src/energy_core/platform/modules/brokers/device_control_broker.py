"""Device control broker."""



from __future__ import annotations



import logging

from datetime import UTC, datetime, timedelta



from energy_core.config import Settings

from energy_core.platform.modules.brokers.synthetic_device import SyntheticDeviceAdapter



logger = logging.getLogger(__name__)



CONTROL_PERMISSIONS = frozenset(

    {

        "device.control",

        "energy.control",

        "charger.control",

        "vehicle.control",

        "hvac.control",

        "spa.control",

    }

)





class DeviceControlBroker:

    def __init__(self, settings: Settings, *, synthetic: SyntheticDeviceAdapter | None = None) -> None:

        self._settings = settings

        self._synthetic = synthetic or SyntheticDeviceAdapter()

        self._leases: dict[tuple[str, int, str, str], datetime] = {}



    @property

    def synthetic(self) -> SyntheticDeviceAdapter:

        return self._synthetic



    def _lease_key(

        self,

        *,

        runtime_instance_id: str,

        site_id: int,

        device_id: str,

        capability: str,

    ) -> tuple[str, int, str, str]:

        return (runtime_instance_id, site_id, device_id, capability)



    def grant_lease(

        self,

        *,

        runtime_instance_id: str,

        site_id: int,

        device_id: str,

        capability: str = "device.control",

        ttl_seconds: float | None = None,

    ) -> datetime:

        ttl = ttl_seconds if ttl_seconds is not None else self._settings.isolated_runtime_control_lease_ttl_seconds

        expires = datetime.now(UTC) + timedelta(seconds=ttl)

        self._leases[self._lease_key(runtime_instance_id=runtime_instance_id, site_id=site_id, device_id=device_id, capability=capability)] = expires

        return expires



    def revoke_runtime(self, runtime_instance_id: str) -> None:

        keys = [k for k in self._leases if k[0] == runtime_instance_id]

        for key in keys:

            self._leases.pop(key, None)

        self._synthetic.release_control(runtime_instance_id)



    def lease_valid(

        self,

        *,

        runtime_instance_id: str,

        site_id: int,

        device_id: str,

        capability: str = "device.control",

    ) -> bool:

        expires = self._leases.get(

            self._lease_key(runtime_instance_id=runtime_instance_id, site_id=site_id, device_id=device_id, capability=capability)

        )

        if expires is None:

            return False

        return datetime.now(UTC) < expires



    async def acquire_lease(

        self,

        *,

        runtime_instance_id: str,

        module_id: str,

        site_id: int,

        capability: str,

        params: dict,

        permissions: tuple[str, ...],

    ) -> dict:

        if not CONTROL_PERMISSIONS.intersection(set(permissions)):

            raise PermissionError("device control permission required")

        device_id = str(params.get("device_id", ""))

        if not device_id:

            raise ValueError("device_id required")

        device_site_id = int(params.get("site_id", site_id))

        if device_site_id != site_id:

            raise PermissionError("cross-site device control denied")

        expires = self.grant_lease(

            runtime_instance_id=runtime_instance_id,

            site_id=site_id,

            device_id=device_id,

            capability=capability,

        )

        logger.info(

            "device.lease.acquire runtime=%s site=%s device=%s capability=%s",

            runtime_instance_id,

            site_id,

            device_id,

            capability,

        )

        return {

            "acquired": True,

            "device_id": device_id,

            "capability": capability,

            "expires_at": expires.isoformat(),

            "runtime_instance_id": runtime_instance_id,

            "module_id": module_id,

            "site_id": site_id,

        }



    async def renew_lease(

        self,

        *,

        runtime_instance_id: str,

        site_id: int,

        capability: str,

        params: dict,

        permissions: tuple[str, ...],

    ) -> dict:

        if not CONTROL_PERMISSIONS.intersection(set(permissions)):

            raise PermissionError("device control permission required")

        device_id = str(params.get("device_id", ""))

        if not device_id:

            raise ValueError("device_id required")

        if not self.lease_valid(

            runtime_instance_id=runtime_instance_id,

            site_id=site_id,

            device_id=device_id,

            capability=capability,

        ):

            raise PermissionError("no active lease to renew")

        expires = self.grant_lease(

            runtime_instance_id=runtime_instance_id,

            site_id=site_id,

            device_id=device_id,

            capability=capability,

        )

        return {

            "renewed": True,

            "device_id": device_id,

            "capability": capability,

            "expires_at": expires.isoformat(),

        }



    async def command(

        self,

        *,

        runtime_instance_id: str,

        module_id: str,

        site_id: int,

        capability: str,

        command: str,

        params: dict,

        permissions: tuple[str, ...],

    ) -> dict:

        if not CONTROL_PERMISSIONS.intersection(set(permissions)):

            raise PermissionError("device control permission required")

        device_id = str(params.get("device_id", ""))

        if not device_id:

            raise ValueError("device_id required")

        device_site_id = int(params.get("site_id", site_id))

        if device_site_id != site_id:

            raise PermissionError("cross-site device control denied")

        if not self.lease_valid(

            runtime_instance_id=runtime_instance_id,

            site_id=site_id,

            device_id=device_id,

            capability=capability,

        ):

            raise PermissionError("control lease required; call AcquireControlLease first")

        result = self._synthetic.apply_command(

            site_id=site_id,

            device_id=device_id,

            command=command,

            params=params,

            runtime_instance_id=runtime_instance_id,

        )

        logger.info(

            "device.command runtime=%s site=%s device=%s command=%s",

            runtime_instance_id,

            site_id,

            device_id,

            command,

        )

        return result


