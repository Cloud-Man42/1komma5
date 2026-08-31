"""Vehicle charging state machine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class ChargingState(StrEnum):
    UNKNOWN = "UNKNOWN"
    DISCONNECTED = "DISCONNECTED"
    PLUGGED_IN = "PLUGGED_IN"
    WAITING = "WAITING"
    CHARGING = "CHARGING"
    PAUSED = "PAUSED"
    CHARGING_COMPLETE = "CHARGING_COMPLETE"
    DISCONNECTED_AFTER_CHARGE = "DISCONNECTED_AFTER_CHARGE"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class ChargingStateTransition:
    from_state: ChargingState | None
    to_state: ChargingState
    occurred_at: datetime
    trigger: str


class VehicleChargingStateMachine:
    def __init__(self, *, initial: ChargingState = ChargingState.UNKNOWN) -> None:
        self._state = initial
        self._transitions: list[ChargingStateTransition] = []

    @property
    def state(self) -> ChargingState:
        return self._state

    @property
    def transitions(self) -> tuple[ChargingStateTransition, ...]:
        return tuple(self._transitions)

    def restore(self, state: str) -> None:
        try:
            self._state = ChargingState(state)
        except ValueError:
            self._state = ChargingState.UNKNOWN

    def apply(
        self,
        *,
        is_plugged_in: bool | None,
        is_charging: bool | None,
        trigger: str,
    ) -> ChargingStateTransition | None:
        target = self._derive_target(is_plugged_in=is_plugged_in, is_charging=is_charging)
        if target == self._state:
            return None
        transition = ChargingStateTransition(
            from_state=self._state,
            to_state=target,
            occurred_at=datetime.now(UTC),
            trigger=trigger,
        )
        self._transitions.append(transition)
        self._state = target
        return transition

    def _derive_target(self, *, is_plugged_in: bool | None, is_charging: bool | None) -> ChargingState:
        if is_plugged_in is False:
            if self._state in {ChargingState.CHARGING, ChargingState.PAUSED, ChargingState.CHARGING_COMPLETE}:
                return ChargingState.DISCONNECTED_AFTER_CHARGE
            return ChargingState.DISCONNECTED
        if is_plugged_in is True and is_charging is False:
            if self._state == ChargingState.CHARGING:
                return ChargingState.CHARGING_COMPLETE
            return ChargingState.PLUGGED_IN
        if is_charging is True:
            if self._state in {ChargingState.PAUSED, ChargingState.PLUGGED_IN, ChargingState.WAITING}:
                return ChargingState.CHARGING
            if self._state == ChargingState.CHARGING:
                return ChargingState.CHARGING
            return ChargingState.CHARGING
        if self._state == ChargingState.CHARGING and is_charging is False:
            return ChargingState.PAUSED
        return self._state if self._state != ChargingState.UNKNOWN else ChargingState.UNKNOWN
