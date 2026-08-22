"""In-memory Virtual EVSE state store for SEMP and diagnostics."""

from __future__ import annotations

from energy_core.virtual_evse.state import VirtualEvseState


class VirtualEvseStateStore:
    def __init__(self) -> None:
        self._states: dict[int, VirtualEvseState] = {}

    def set(self, charger_id: int, state: VirtualEvseState) -> None:
        self._states[charger_id] = state

    def get(self, charger_id: int) -> VirtualEvseState | None:
        return self._states.get(charger_id)

    def list_enabled_ids(self, enabled_charger_ids: list[int]) -> list[str]:
        return [f"emic-evse-{cid}" for cid in enabled_charger_ids]

    def resolve_charger_id(self, device_id: str) -> int | None:
        prefix = "emic-evse-"
        if not device_id.startswith(prefix):
            return None
        try:
            return int(device_id[len(prefix) :])
        except ValueError:
            return None


# Process-wide store updated by collector, read by API/SEMP routes.
GLOBAL_VIRTUAL_EVSE_STORE = VirtualEvseStateStore()
