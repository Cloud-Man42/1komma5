"""Synthetic device adapter for Sprint C tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(slots=True)
class SyntheticDeviceState:
    device_id: str
    site_id: int
    owner_runtime_id: str | None = None
    last_command: str | None = None
    power_w: float = 0.0
    safe_default_power_w: float = 0.0
    command_log: list[dict] = field(default_factory=list)


class SyntheticDeviceAdapter:
    def __init__(self) -> None:
        self._devices: dict[tuple[int, str], SyntheticDeviceState] = {}

    def register_device(self, *, site_id: int, device_id: str, safe_default_power_w: float = 0.0) -> None:
        self._devices[(site_id, device_id)] = SyntheticDeviceState(
            device_id=device_id,
            site_id=site_id,
            safe_default_power_w=safe_default_power_w,
        )

    def get(self, site_id: int, device_id: str) -> SyntheticDeviceState | None:
        return self._devices.get((site_id, device_id))

    def apply_command(
        self,
        *,
        site_id: int,
        device_id: str,
        command: str,
        params: dict,
        runtime_instance_id: str,
    ) -> dict:
        device = self._devices.get((site_id, device_id))
        if device is None:
            raise ValueError("device not found")
        if command == "set_power":
            power = float(params.get("power_w", 0))
            if power < 0 or power > 11000:
                raise ValueError("power out of safe range")
            device.power_w = power
            device.owner_runtime_id = runtime_instance_id
        elif command == "read_power":
            return {"power_w": device.power_w}
        else:
            raise ValueError(f"unsupported command: {command}")
        device.last_command = command
        device.command_log.append(
            {"command": command, "params": params, "runtime": runtime_instance_id, "at": datetime.now(UTC).isoformat()}
        )
        return {"ok": True, "power_w": device.power_w}

    def release_control(self, runtime_instance_id: str) -> None:
        for device in self._devices.values():
            if device.owner_runtime_id == runtime_instance_id:
                device.owner_runtime_id = None
                device.power_w = device.safe_default_power_w
