"""Tests for distributed module runtime state in Redis."""

from __future__ import annotations

import pytest

from energy_core.cache.module_runtime_state import (
    RuntimeStateSnapshot,
    resolve_distributed_runtime_status,
)
from energy_core.platform.modules.types import RuntimeStatus


def test_resolve_distributed_runtime_status_prefers_redis_running() -> None:
    snapshot = RuntimeStateSnapshot(
        site_id=1,
        module_id="feature.solar-forecast",
        runtime_state=RuntimeStatus.RUNNING,
    )
    assert (
        resolve_distributed_runtime_status(
            snapshot,
            local_state=RuntimeStatus.STOPPED,
            enabled=True,
        )
        == RuntimeStatus.RUNNING
    )


def test_resolve_distributed_runtime_status_disabled_forces_stopped() -> None:
    snapshot = RuntimeStateSnapshot(
        site_id=1,
        module_id="feature.solar-forecast",
        runtime_state=RuntimeStatus.RUNNING,
    )
    assert (
        resolve_distributed_runtime_status(
            snapshot,
            local_state=RuntimeStatus.RUNNING,
            enabled=False,
        )
        == RuntimeStatus.STOPPED
    )


def test_resolve_distributed_runtime_status_falls_back_to_local_without_redis() -> None:
    assert (
        resolve_distributed_runtime_status(
            None,
            local_state=RuntimeStatus.BLOCKED,
            enabled=True,
            distributed_runtime_expected=False,
        )
        == RuntimeStatus.BLOCKED
    )


def test_resolve_distributed_runtime_status_missing_remote_returns_unknown() -> None:
    assert (
        resolve_distributed_runtime_status(
            None,
            local_state=RuntimeStatus.STOPPED,
            enabled=True,
            distributed_runtime_expected=True,
        )
        == RuntimeStatus.UNKNOWN
    )


@pytest.mark.parametrize(
    ("runtime_state",),
    [
        (RuntimeStatus.RUNNING,),
        (RuntimeStatus.STOPPED,),
        (RuntimeStatus.FAILED,),
        (RuntimeStatus.BLOCKED,),
        (RuntimeStatus.STARTING,),
        (RuntimeStatus.STOPPING,),
    ],
)
def test_resolve_distributed_runtime_status_uses_fresh_snapshot(runtime_state: RuntimeStatus) -> None:
    snapshot = RuntimeStateSnapshot(
        site_id=1,
        module_id="integration.heartbeat",
        runtime_state=runtime_state,
    )
    assert (
        resolve_distributed_runtime_status(
            snapshot,
            local_state=RuntimeStatus.STOPPED,
            enabled=True,
            distributed_runtime_expected=True,
        )
        == runtime_state
    )


@pytest.mark.asyncio
async def test_runtime_state_publish_read_roundtrip() -> None:
    pytest.importorskip("redis")
    try:
        from redis.asyncio import Redis
    except ImportError:
        pytest.skip("redis not installed")

    client = Redis.from_url("redis://127.0.0.1:6379/15", decode_responses=True)
    try:
        await client.ping()
    except Exception:
        pytest.skip("local redis unavailable")

    from energy_core.cache.module_runtime_state import ModuleRuntimeStateStore

    store = ModuleRuntimeStateStore("redis://127.0.0.1:6379/15")
    snapshot = RuntimeStateSnapshot(
        site_id=99,
        module_id="integration.heartbeat",
        runtime_state=RuntimeStatus.RUNNING,
        last_error=None,
        instance_id="test-instance",
    )
    try:
        assert await store.publish(snapshot) is True
        read = await store.read_site(99)
        assert "integration.heartbeat" in read
        assert read["integration.heartbeat"].runtime_state == RuntimeStatus.RUNNING
    finally:
        await client.delete("emic:runtime:99:integration.heartbeat")
        await client.aclose()
