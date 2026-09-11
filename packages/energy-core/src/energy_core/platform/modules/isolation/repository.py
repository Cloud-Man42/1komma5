"""Isolated runtime persistence."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models.isolated_runtime import (
    IsolatedRuntimeInstanceModel,
    RuntimeControlLeaseModel,
    RuntimeEventModel,
)
from energy_core.platform.modules.isolation.state_machine import assert_transition
from energy_core.platform.modules.isolation.types import (
    ControlLeaseRecord,
    IsolatedRuntimeRecord,
    IsolatedRuntimeState,
    RuntimeEventType,
)


def _new_runtime_id() -> str:
    return uuid.uuid4().hex


def _record_from_row(row: IsolatedRuntimeInstanceModel) -> IsolatedRuntimeRecord:
    reasons: tuple[str, ...] = ()
    if row.reason_codes_json:
        try:
            parsed = json.loads(row.reason_codes_json)
            if isinstance(parsed, list):
                reasons = tuple(str(x) for x in parsed)
        except json.JSONDecodeError:
            pass
    return IsolatedRuntimeRecord(
        id=row.id,
        runtime_instance_id=row.runtime_instance_id,
        module_id=row.module_id,
        version=row.version,
        publisher_id=row.publisher_id,
        artifact_sha256=row.artifact_sha256,
        site_id=row.site_id,
        state=IsolatedRuntimeState(row.state),
        process_identity=row.process_identity,
        process_pid=row.process_pid,
        sandbox_mode=row.sandbox_mode,
        socket_path=row.socket_path,
        package_path=row.package_path,
        data_path=row.data_path,
        protocol_version=row.protocol_version,
        restart_count=row.restart_count,
        last_error=row.last_error,
        reason_codes=reasons,
        permissions_json=row.permissions_json,
        started_at=row.started_at,
        last_heartbeat_at=row.last_heartbeat_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class IsolatedRuntimeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_instance(
        self,
        *,
        module_id: str,
        version: str,
        publisher_id: str,
        artifact_sha256: str,
        site_id: int,
        state: IsolatedRuntimeState = IsolatedRuntimeState.PREPARING,
        permissions_json: str | None = None,
    ) -> IsolatedRuntimeRecord:
        row = IsolatedRuntimeInstanceModel(
            runtime_instance_id=_new_runtime_id(),
            module_id=module_id,
            version=version,
            publisher_id=publisher_id,
            artifact_sha256=artifact_sha256,
            site_id=site_id,
            state=state.value,
            permissions_json=permissions_json,
        )
        self._session.add(row)
        await self._session.flush()
        return _record_from_row(row)

    async def get_by_instance_id(self, runtime_instance_id: str) -> IsolatedRuntimeRecord | None:
        result = await self._session.execute(
            select(IsolatedRuntimeInstanceModel).where(
                IsolatedRuntimeInstanceModel.runtime_instance_id == runtime_instance_id
            )
        )
        row = result.scalar_one_or_none()
        return _record_from_row(row) if row else None

    async def list_instances(self, *, site_id: int | None = None) -> list[IsolatedRuntimeRecord]:
        stmt = select(IsolatedRuntimeInstanceModel).order_by(IsolatedRuntimeInstanceModel.id.desc())
        if site_id is not None:
            stmt = stmt.where(IsolatedRuntimeInstanceModel.site_id == site_id)
        result = await self._session.execute(stmt)
        return [_record_from_row(row) for row in result.scalars().all()]

    async def transition(
        self,
        runtime_instance_id: str,
        *,
        to_state: IsolatedRuntimeState,
        last_error: str | None = None,
        reason_codes: tuple[str, ...] | None = None,
        **fields: object,
    ) -> IsolatedRuntimeRecord | None:
        record = await self.get_by_instance_id(runtime_instance_id)
        if record is None:
            return None
        assert_transition(record.state, to_state)
        values: dict[str, object] = {"state": to_state.value, "updated_at": datetime.now(UTC)}
        if last_error is not None:
            values["last_error"] = last_error
        if reason_codes is not None:
            values["reason_codes_json"] = json.dumps(list(reason_codes))
        values.update(fields)
        await self._session.execute(
            update(IsolatedRuntimeInstanceModel)
            .where(IsolatedRuntimeInstanceModel.runtime_instance_id == runtime_instance_id)
            .values(**values)
        )
        await self._session.flush()
        return await self.get_by_instance_id(runtime_instance_id)

    async def record_event(
        self,
        *,
        runtime_instance_id: str,
        event_type: RuntimeEventType,
        module_id: str,
        site_id: int,
        detail: dict | None = None,
    ) -> None:
        self._session.add(
            RuntimeEventModel(
                runtime_instance_id=runtime_instance_id,
                event_type=event_type.value,
                module_id=module_id,
                site_id=site_id,
                detail_json=json.dumps(detail or {}, sort_keys=True),
            )
        )
        await self._session.flush()

    async def list_events(
        self,
        *,
        runtime_instance_id: str | None = None,
        event_type: RuntimeEventType | None = None,
    ) -> list[RuntimeEventModel]:
        stmt = select(RuntimeEventModel).order_by(RuntimeEventModel.id.asc())
        if runtime_instance_id is not None:
            stmt = stmt.where(RuntimeEventModel.runtime_instance_id == runtime_instance_id)
        if event_type is not None:
            stmt = stmt.where(RuntimeEventModel.event_type == event_type.value)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create_lease(
        self,
        *,
        runtime_instance_id: str,
        module_id: str,
        site_id: int,
        device_id: str,
        capability: str,
        expires_at: datetime,
    ) -> ControlLeaseRecord:
        row = RuntimeControlLeaseModel(
            runtime_instance_id=runtime_instance_id,
            module_id=module_id,
            site_id=site_id,
            device_id=device_id,
            capability=capability,
            expires_at=expires_at,
            active=True,
        )
        self._session.add(row)
        await self._session.flush()
        return ControlLeaseRecord(
            id=row.id,
            runtime_instance_id=row.runtime_instance_id,
            module_id=row.module_id,
            site_id=row.site_id,
            device_id=row.device_id,
            capability=row.capability,
            expires_at=row.expires_at,
            active=row.active,
        )

    async def revoke_leases(self, runtime_instance_id: str) -> int:
        result = await self._session.execute(
            update(RuntimeControlLeaseModel)
            .where(RuntimeControlLeaseModel.runtime_instance_id == runtime_instance_id)
            .values(active=False)
        )
        return result.rowcount or 0

    async def record_heartbeat(self, runtime_instance_id: str) -> None:
        await self._session.execute(
            update(IsolatedRuntimeInstanceModel)
            .where(IsolatedRuntimeInstanceModel.runtime_instance_id == runtime_instance_id)
            .values(last_heartbeat_at=datetime.now(UTC), updated_at=datetime.now(UTC))
        )
        await self._session.flush()

    async def active_lease(
        self,
        *,
        runtime_instance_id: str,
        device_id: str,
        capability: str,
        now: datetime | None = None,
    ) -> ControlLeaseRecord | None:
        now = now or datetime.now(UTC)
        result = await self._session.execute(
            select(RuntimeControlLeaseModel).where(
                RuntimeControlLeaseModel.runtime_instance_id == runtime_instance_id,
                RuntimeControlLeaseModel.device_id == device_id,
                RuntimeControlLeaseModel.capability == capability,
                RuntimeControlLeaseModel.active.is_(True),
                RuntimeControlLeaseModel.expires_at > now,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return ControlLeaseRecord(
            id=row.id,
            runtime_instance_id=row.runtime_instance_id,
            module_id=row.module_id,
            site_id=row.site_id,
            device_id=row.device_id,
            capability=row.capability,
            expires_at=row.expires_at,
            active=row.active,
        )
