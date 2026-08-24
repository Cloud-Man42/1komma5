"""Mercedes connection manager tests."""

from __future__ import annotations

from energy_core.vehicles.mercedes.transport.backoff import MercedesBackoffPolicy
from energy_core.vehicles.mercedes.transport.connection_manager import MercedesConnectionManager


def test_backoff_rate_limit_uses_longest_step():
    policy = MercedesBackoffPolicy()
    first = policy.on_rate_limited()
    second = policy.on_rate_limited()
    assert first.blocked is True
    assert second.blocked is True
    assert first.delay_seconds >= 900
    assert second.delay_seconds >= 900


def test_backoff_failure_is_monotonic():
    policy = MercedesBackoffPolicy()
    delays = [policy.on_failure().delay_seconds for _ in range(4)]
    assert delays == sorted(delays)


def test_connection_manager_reset_clears_circuit():
    manager = MercedesConnectionManager()
    manager.status.circuit_open = True
    manager.status.auth_failure_count = 5
    manager.reset_circuit()
    assert manager.status.circuit_open is False
    assert manager.status.auth_failure_count == 0
