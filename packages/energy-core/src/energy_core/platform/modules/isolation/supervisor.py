"""Runtime heartbeat supervisor and crash-loop protection."""



from __future__ import annotations



import asyncio

import logging

import random

from datetime import UTC, datetime

from pathlib import Path

from typing import TYPE_CHECKING



from energy_core.platform.modules.isolation.types import IsolatedRuntimeState, RuntimeEventType



if TYPE_CHECKING:

    from energy_core.config import Settings

    from energy_core.platform.modules.isolation.manager import IsolatedModuleRuntimeManager



logger = logging.getLogger(__name__)





class RuntimeSupervisor:

    """Monitors isolated runtimes for heartbeat loss, crashes, and restart policy."""



    def __init__(self, settings: Settings) -> None:

        self._settings = settings

        self._miss_counts: dict[str, int] = {}



    def record_heartbeat(self, runtime_instance_id: str) -> None:

        self._miss_counts[runtime_instance_id] = 0



    def clear_runtime(self, runtime_instance_id: str) -> None:

        self._miss_counts.pop(runtime_instance_id, None)



    async def supervise(self, manager: IsolatedModuleRuntimeManager) -> None:

        records = await manager.list_runtimes()

        now = datetime.now(UTC)

        interval = self._settings.isolated_runtime_heartbeat_interval_seconds

        threshold = self._settings.isolated_runtime_heartbeat_miss_threshold

        for record in records:

            if record.state not in {

                IsolatedRuntimeState.RUNNING,

                IsolatedRuntimeState.DEGRADED,

                IsolatedRuntimeState.READY,

            }:

                continue

            runtime_id = record.runtime_instance_id

            if await self._check_disk_quota(manager, record):

                continue

            proc = manager.active_process(runtime_id)

            if proc is not None and proc.process.poll() is not None:

                await self._handle_crash(manager, runtime_id, reason="process exited")

                continue

            last = record.last_heartbeat_at or record.started_at

            if last is None:

                continue

            if last.tzinfo is None:

                last = last.replace(tzinfo=UTC)

            age = (now - last).total_seconds()

            if age <= interval * threshold:

                self._miss_counts[runtime_id] = 0

                continue

            misses = self._miss_counts.get(runtime_id, 0) + 1

            self._miss_counts[runtime_id] = misses

            if misses < threshold:

                if record.state == IsolatedRuntimeState.RUNNING:

                    await manager._repo.transition(runtime_id, to_state=IsolatedRuntimeState.DEGRADED)

                continue

            await manager._audit(

                runtime_instance_id=runtime_id,

                event_type=RuntimeEventType.RESOURCE_LIMIT,

                module_id=record.module_id,

                site_id=record.site_id,

                detail={"reason": "heartbeat timeout", "misses": misses},

            )

            await manager.stop_runtime(runtime_id, reason="heartbeat timeout")

            fresh = await manager.get_runtime(runtime_id)

            if fresh is not None:

                await self._maybe_restart(manager, fresh, reason="heartbeat timeout")



    async def _check_disk_quota(self, manager: IsolatedModuleRuntimeManager, record) -> bool:

        if not record.data_path:

            return False

        data_path = Path(record.data_path)

        if not data_path.exists():

            return False

        quota_bytes = self._settings.isolated_runtime_data_quota_mb * 1024 * 1024

        total = sum(f.stat().st_size for f in data_path.rglob("*") if f.is_file())

        if total <= quota_bytes:

            return False

        await manager._audit(

            runtime_instance_id=record.runtime_instance_id,

            event_type=RuntimeEventType.RESOURCE_LIMIT,

            module_id=record.module_id,

            site_id=record.site_id,

            detail={"reason": "disk quota exceeded", "bytes": total, "quota": quota_bytes},

        )

        await manager.stop_runtime(record.runtime_instance_id, reason="disk quota exceeded")

        await manager._repo.transition(

            record.runtime_instance_id,

            to_state=IsolatedRuntimeState.QUARANTINED,

            last_error="disk quota exceeded",

            reason_codes=("DISK_QUOTA",),

        )

        return True



    async def _handle_crash(

        self,

        manager: IsolatedModuleRuntimeManager,

        runtime_instance_id: str,

        *,

        reason: str,

    ) -> None:

        record = await manager.get_runtime(runtime_instance_id)

        if record is None:

            return

        self.clear_runtime(runtime_instance_id)

        manager.drop_process(runtime_instance_id)

        manager.gateway.unregister_runtime(runtime_instance_id)

        manager.gateway.device_broker.revoke_runtime(runtime_instance_id)

        await manager._repo.revoke_leases(runtime_instance_id)

        await manager._repo.transition(

            runtime_instance_id,

            to_state=IsolatedRuntimeState.CRASHED,

            last_error=reason,

        )

        await manager._audit(

            runtime_instance_id=runtime_instance_id,

            event_type=RuntimeEventType.CRASH,

            module_id=record.module_id,

            site_id=record.site_id,

            detail={"reason": reason},

        )

        await self._maybe_restart(manager, record, reason=reason)



    async def _maybe_restart(

        self,

        manager: IsolatedModuleRuntimeManager,

        record,

        *,

        reason: str,

    ) -> None:

        max_restarts = self._settings.isolated_runtime_max_restarts

        if record.restart_count >= max_restarts:

            await manager._repo.transition(

                record.runtime_instance_id,

                to_state=IsolatedRuntimeState.QUARANTINED,

                last_error=f"crash-loop: {reason}",

                reason_codes=("CRASH_LOOP",),

            )

            await manager._audit(

                runtime_instance_id=record.runtime_instance_id,

                event_type=RuntimeEventType.QUARANTINE,

                module_id=record.module_id,

                site_id=record.site_id,

                detail={"reason": "crash-loop", "restarts": record.restart_count},

            )

            return

        backoff = self.restart_backoff_seconds(record.restart_count)

        jitter = random.uniform(0, min(backoff, 2.0))

        await asyncio.sleep(backoff + jitter)

        await manager._repo.transition(

            record.runtime_instance_id,

            to_state=IsolatedRuntimeState.PREPARING,

            restart_count=record.restart_count + 1,

        )



    def restart_backoff_seconds(self, restart_count: int) -> float:

        base = self._settings.isolated_runtime_restart_backoff_seconds

        return min(base * (2**restart_count), 300.0)


