"""Mock Tesla Fleet API client."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.integrations.tesla.parsing import parse_vehicle_state
from energy_core.vehicles.abstractions.models import VehicleState


class TeslaMockClient:
    def __init__(self) -> None:
        self._vehicle_payload = {
            "id": "mock-tesla-1",
            "id_s": "mock-tesla-1",
            "vin": "5YJ3E1EA1KF000001",
            "model": "Model 3",
            "state": "online",
            "charge_state": {
                "battery_level": 62,
                "charging_state": "Stopped",
                "charger_power": 0,
            },
            "drive_state": {"range": 320.0},
            "vehicle_state": {"car_type": "model3", "api_version": 70},
        }

    async def list_vehicles(self) -> list[dict[str, object]]:
        return [{"id_s": self._vehicle_payload["id_s"], "vin": self._vehicle_payload["vin"]}]

    async def get_vehicle_data(self, vehicle_id: str) -> dict[str, object]:
        _ = vehicle_id
        return dict(self._vehicle_payload)

    async def get_vehicle_states(self) -> tuple[VehicleState, ...]:
        now = datetime.now(UTC)
        return (parse_vehicle_state(self._vehicle_payload, now=now),)
