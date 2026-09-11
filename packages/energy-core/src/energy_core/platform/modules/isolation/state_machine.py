"""Legal isolated runtime state transitions."""

from __future__ import annotations

from energy_core.platform.modules.isolation.types import IsolatedRuntimeState

_TRANSITIONS: dict[IsolatedRuntimeState, frozenset[IsolatedRuntimeState]] = {
    IsolatedRuntimeState.PREPARING: frozenset(
        {IsolatedRuntimeState.STARTING, IsolatedRuntimeState.BLOCKED, IsolatedRuntimeState.QUARANTINED}
    ),
    IsolatedRuntimeState.STARTING: frozenset(
        {IsolatedRuntimeState.HANDSHAKING, IsolatedRuntimeState.CRASHED, IsolatedRuntimeState.STOPPED, IsolatedRuntimeState.QUARANTINED}
    ),
    IsolatedRuntimeState.HANDSHAKING: frozenset(
        {IsolatedRuntimeState.READY, IsolatedRuntimeState.CRASHED, IsolatedRuntimeState.QUARANTINED, IsolatedRuntimeState.STOPPED, IsolatedRuntimeState.STOPPING}
    ),
    IsolatedRuntimeState.READY: frozenset(
        {IsolatedRuntimeState.RUNNING, IsolatedRuntimeState.STOPPING, IsolatedRuntimeState.CRASHED, IsolatedRuntimeState.QUARANTINED, IsolatedRuntimeState.DEGRADED}
    ),
    IsolatedRuntimeState.RUNNING: frozenset(
        {IsolatedRuntimeState.DEGRADED, IsolatedRuntimeState.STOPPING, IsolatedRuntimeState.CRASHED, IsolatedRuntimeState.QUARANTINED}
    ),
    IsolatedRuntimeState.DEGRADED: frozenset(
        {IsolatedRuntimeState.RUNNING, IsolatedRuntimeState.STOPPING, IsolatedRuntimeState.CRASHED, IsolatedRuntimeState.QUARANTINED}
    ),
    IsolatedRuntimeState.STOPPING: frozenset({IsolatedRuntimeState.STOPPED, IsolatedRuntimeState.CRASHED}),
    IsolatedRuntimeState.STOPPED: frozenset({IsolatedRuntimeState.PREPARING, IsolatedRuntimeState.BLOCKED, IsolatedRuntimeState.QUARANTINED}),
    IsolatedRuntimeState.CRASHED: frozenset({IsolatedRuntimeState.PREPARING, IsolatedRuntimeState.QUARANTINED, IsolatedRuntimeState.BLOCKED}),
    IsolatedRuntimeState.QUARANTINED: frozenset({IsolatedRuntimeState.STOPPED, IsolatedRuntimeState.STOPPING}),
    IsolatedRuntimeState.BLOCKED: frozenset({IsolatedRuntimeState.PREPARING}),
}


def can_transition(from_state: IsolatedRuntimeState, to_state: IsolatedRuntimeState) -> bool:
    if from_state == to_state:
        return True
    return to_state in _TRANSITIONS.get(from_state, frozenset())


def assert_transition(from_state: IsolatedRuntimeState, to_state: IsolatedRuntimeState) -> None:
    if not can_transition(from_state, to_state):
        raise ValueError(f"Illegal runtime transition: {from_state} -> {to_state}")
