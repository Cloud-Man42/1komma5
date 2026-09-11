"""Mock vehicle command provider for tests."""

from __future__ import annotations

from dataclasses import dataclass

from energy_core.vehicles.commands.errors import VehicleCommandError
from energy_core.vehicles.commands.provider_resolver import VehicleCommandDispatchResult


@dataclass
class MockCommandFeatures:
    can_set_target_soc: bool = True
    can_start_charging: bool = True
    can_stop_charging: bool = True


class MockVehicleCommandProvider:
    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail
        self.calls: list[str] = []

    async def load_command_features(self, vin: str) -> MockCommandFeatures:
        self.calls.append(f"features:{vin}")
        return MockCommandFeatures()

    async def set_target_soc(
        self,
        vin: str,
        *,
        target_soc_percent: int,
        features: object,
    ) -> VehicleCommandDispatchResult:
        self.calls.append(f"set_target_soc:{vin}:{target_soc_percent}")
        if self._fail:
            raise VehicleCommandError("mock failure", code="transport_failed")
        return VehicleCommandDispatchResult(state="FINISHED")

    async def start_charging(self, vin: str, *, features: object) -> VehicleCommandDispatchResult:
        self.calls.append(f"start:{vin}")
        return VehicleCommandDispatchResult(state="FINISHED")

    async def stop_charging(self, vin: str, *, features: object) -> VehicleCommandDispatchResult:
        self.calls.append(f"stop:{vin}")
        if self._fail:
            raise VehicleCommandError("mock failure", code="transport_failed")
        return VehicleCommandDispatchResult(state="FINISHED")
