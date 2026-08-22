"""Virtual EVSE device identity."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VirtualEvseDeviceProfile:
    device_id: str
    device_name: str
    physical_charger_label: str
    ev_vehicle_label: str
    max_power_w: float

    @classmethod
    def for_charger(
        cls,
        charger_id: int,
        *,
        physical_charger_label: str = "Charge Amps Halo",
        ev_vehicle_label: str = "Mercedes EQE 500",
        max_power_w: float = 11000.0,
        name: str | None = None,
    ) -> VirtualEvseDeviceProfile:
        device_id = f"emic-evse-{charger_id}"
        device_name = name or f"Virtual EVSE ({physical_charger_label})"
        return cls(
            device_id=device_id,
            device_name=device_name,
            physical_charger_label=physical_charger_label,
            ev_vehicle_label=ev_vehicle_label,
            max_power_w=max_power_w,
        )
