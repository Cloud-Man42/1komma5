"""Spa actuator runtime state persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import SpaActuatorStateModel
from energy_core.spa_energy.runtime import SpaActuatorRuntime, SpaActuatorState


@dataclass(frozen=True, slots=True)
class SpaActuatorStateRecord:
    consumer_id: int
    state: str
    runtime_json: str
    integration_degraded: bool
    integration_degraded_message_sv: str
    updated_at: datetime


class SpaActuatorStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, consumer_id: int) -> SpaActuatorRuntime:
        model = await self._session.get(SpaActuatorStateModel, consumer_id)
        if model is None:
            model = SpaActuatorStateModel(consumer_id=consumer_id)
            self._session.add(model)
            await self._session.flush()
        return self._deserialize(model.runtime_json)

    async def save(self, consumer_id: int, runtime: SpaActuatorRuntime) -> None:
        model = await self._session.get(SpaActuatorStateModel, consumer_id)
        if model is None:
            model = SpaActuatorStateModel(consumer_id=consumer_id)
            self._session.add(model)
        model.state = runtime.state.value
        model.runtime_json = self._serialize(runtime)
        model.integration_degraded = runtime.integration_degraded
        model.integration_degraded_message_sv = runtime.integration_degraded_message_sv
        await self._session.flush()

    def _serialize(self, runtime: SpaActuatorRuntime) -> str:
        return json.dumps(
            {
                "state": runtime.state.value,
                "cleaning_started_at": runtime.cleaning_started_at.isoformat() if runtime.cleaning_started_at else None,
                "cleaning_stop_at": runtime.cleaning_stop_at.isoformat() if runtime.cleaning_stop_at else None,
                "last_command_at": runtime.last_command_at.isoformat() if runtime.last_command_at else None,
                "last_stop_at": runtime.last_stop_at.isoformat() if runtime.last_stop_at else None,
                "starts_today": runtime.starts_today,
                "starts_day": runtime.starts_day,
                "manual_override_until": runtime.manual_override_until.isoformat() if runtime.manual_override_until else None,
                "filter_held_off_until": runtime.filter_held_off_until.isoformat() if runtime.filter_held_off_until else None,
                "last_planner_run_at": runtime.last_planner_run_at.isoformat() if runtime.last_planner_run_at else None,
                "integration_degraded": runtime.integration_degraded,
                "integration_degraded_message_sv": runtime.integration_degraded_message_sv,
                "last_reason": runtime.last_reason,
                "last_reason_sv": runtime.last_reason_sv,
            }
        )

    def _deserialize(self, raw: str) -> SpaActuatorRuntime:
        if not raw:
            return SpaActuatorRuntime()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return SpaActuatorRuntime()

        def parse_dt(value: str | None) -> datetime | None:
            if not value:
                return None
            return datetime.fromisoformat(value)

        state_raw = data.get("state", SpaActuatorState.IDLE.value)
        try:
            state = SpaActuatorState(state_raw)
        except ValueError:
            state = SpaActuatorState.IDLE

        return SpaActuatorRuntime(
            state=state,
            cleaning_started_at=parse_dt(data.get("cleaning_started_at")),
            cleaning_stop_at=parse_dt(data.get("cleaning_stop_at")),
            last_command_at=parse_dt(data.get("last_command_at")),
            last_stop_at=parse_dt(data.get("last_stop_at")),
            starts_today=int(data.get("starts_today", 0)),
            starts_day=str(data.get("starts_day", "")),
            manual_override_until=parse_dt(data.get("manual_override_until")),
            filter_held_off_until=parse_dt(data.get("filter_held_off_until")),
            last_planner_run_at=parse_dt(data.get("last_planner_run_at")),
            integration_degraded=bool(data.get("integration_degraded", False)),
            integration_degraded_message_sv=str(data.get("integration_degraded_message_sv", "")),
            last_reason=str(data.get("last_reason", "")),
            last_reason_sv=str(data.get("last_reason_sv", "")),
        )
