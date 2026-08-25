"""Persistence for Heartbeat Virtual EV Bridge discovery and settings."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import (
    HeartbeatApiObservationModel,
    HeartbeatBridgeSettingsModel,
    HeartbeatDiscoveryRunModel,
    HeartbeatEvMappingModel,
    HeartbeatWriteTestModel,
    VirtualChargerCommandModel,
    VirtualChargerDecisionModel,
    VirtualChargerReplayRunModel,
)
from energy_core.heartbeat.discovery.models import (
    HeartbeatApiObservation,
    HeartbeatBridgeSettingsRecord,
    HeartbeatEvDiscoveryResult,
    VirtualEvMappingRecord,
)


def _serialize_discovery_result(result: HeartbeatEvDiscoveryResult) -> dict[str, Any]:
    def _obs(o: HeartbeatApiObservation) -> dict[str, Any]:
        return {
            "method": o.method,
            "path": o.path,
            "status_code": o.status_code,
            "started_at": o.started_at.isoformat(),
            "duration_ms": o.duration_ms,
            "request_headers_redacted": o.request_headers_redacted,
            "response_headers_redacted": o.response_headers_redacted,
            "raw_json": o.raw_json,
            "parsed_summary": o.parsed_summary,
            "unknown_fields": list(o.unknown_fields),
            "schema_fingerprint": o.schema_fingerprint,
            "error": o.error,
        }

    return {
        "site_slug": result.site_slug,
        "site_name": result.site_name,
        "system_id": result.system_id,
        "authenticated": result.authenticated,
        "ev_profiles": [asdict(p) for p in result.ev_profiles],
        "wallboxes": [asdict(w) for w in result.wallboxes],
        "ems_devices": [asdict(d) for d in result.ems_devices],
        "assignments": [asdict(a) for a in result.assignments],
        "charging_modes": list(result.charging_modes),
        "ai_decision_types": list(result.ai_decision_types),
        "ai_decisions_found": result.ai_decisions_found,
        "resolved_ev_id": asdict(result.resolved_ev_id),
        "setup_classification": result.setup_classification.value,
        "bridge_lifecycle": result.bridge_lifecycle.value,
        "halo_found": result.halo_found,
        "halo_online": result.halo_online,
        "virtual_bridge_suitable": result.virtual_bridge_suitable,
        "warnings": list(result.warnings),
        "emic_vehicle_lines": list(result.emic_vehicle_lines),
        "field_hints": list(result.field_hints),
        "observations": [_obs(o) for o in result.observations],
        "started_at": result.started_at.isoformat(),
        "completed_at": result.completed_at.isoformat(),
    }


@dataclass(frozen=True, slots=True)
class StoredDiscoveryRun:
    id: int
    site_id: int
    status: str
    system_id: str | None
    conclusion_class: str | None
    bridge_lifecycle: str | None
    resolved_ev_id: str | None
    confidence_pct: float | None
    report_text: str
    started_at: datetime
    completed_at: datetime | None


class HeartbeatDiscoveryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_bridge_settings(self, site_id: int) -> HeartbeatBridgeSettingsRecord:
        result = await self._session.execute(
            select(HeartbeatBridgeSettingsModel).where(HeartbeatBridgeSettingsModel.site_id == site_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = HeartbeatBridgeSettingsModel(site_id=site_id)
            self._session.add(row)
            await self._session.flush()
        return self._to_settings(row)

    async def update_bridge_settings(
        self,
        site_id: int,
        **kwargs: Any,
    ) -> HeartbeatBridgeSettingsRecord:
        result = await self._session.execute(
            select(HeartbeatBridgeSettingsModel).where(HeartbeatBridgeSettingsModel.site_id == site_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = HeartbeatBridgeSettingsModel(site_id=site_id)
            self._session.add(row)
        for key, value in kwargs.items():
            if value is not None and hasattr(row, key):
                setattr(row, key, value)
        await self._session.flush()
        return self._to_settings(row)

    async def save_discovery_run(
        self,
        site_id: int,
        result: HeartbeatEvDiscoveryResult,
        *,
        status: str = "COMPLETED",
        error_message: str | None = None,
    ) -> int:
        run = HeartbeatDiscoveryRunModel(
            site_id=site_id,
            status=status,
            system_id=result.system_id,
            conclusion_class=result.setup_classification.value,
            bridge_lifecycle=result.bridge_lifecycle.value,
            resolved_ev_id=result.resolved_ev_id.heartbeat_ev_id,
            confidence_pct=result.resolved_ev_id.confidence_pct,
            report_json=json.dumps(_serialize_discovery_result(result)),
            report_text=result.report_text,
            error_message=error_message,
            started_at=result.started_at,
            completed_at=result.completed_at,
        )
        self._session.add(run)
        await self._session.flush()

        for obs in result.observations:
            self._session.add(
                HeartbeatApiObservationModel(
                    run_id=run.id,
                    method=obs.method,
                    path=obs.path,
                    status_code=obs.status_code,
                    duration_ms=obs.duration_ms,
                    observation_json=json.dumps(
                        {
                            "method": obs.method,
                            "path": obs.path,
                            "status_code": obs.status_code,
                            "duration_ms": obs.duration_ms,
                            "request_headers_redacted": obs.request_headers_redacted,
                            "response_headers_redacted": obs.response_headers_redacted,
                            "raw_json": obs.raw_json,
                            "parsed_summary": obs.parsed_summary,
                            "unknown_fields": list(obs.unknown_fields),
                            "schema_fingerprint": obs.schema_fingerprint,
                            "error": obs.error,
                        }
                    ),
                    schema_fingerprint=obs.schema_fingerprint,
                    recorded_at=obs.started_at,
                )
            )
        await self._session.flush()
        return run.id

    async def list_runs(self, site_id: int, *, limit: int = 20) -> list[StoredDiscoveryRun]:
        result = await self._session.execute(
            select(HeartbeatDiscoveryRunModel)
            .where(HeartbeatDiscoveryRunModel.site_id == site_id)
            .order_by(desc(HeartbeatDiscoveryRunModel.started_at))
            .limit(limit)
        )
        return [self._to_run(row) for row in result.scalars().all()]

    async def get_run(self, site_id: int, run_id: int) -> StoredDiscoveryRun | None:
        result = await self._session.execute(
            select(HeartbeatDiscoveryRunModel).where(
                HeartbeatDiscoveryRunModel.site_id == site_id,
                HeartbeatDiscoveryRunModel.id == run_id,
            )
        )
        row = result.scalar_one_or_none()
        return self._to_run(row) if row else None

    async def get_run_report_json(self, run_id: int) -> dict[str, Any]:
        result = await self._session.execute(
            select(HeartbeatDiscoveryRunModel.report_json).where(HeartbeatDiscoveryRunModel.id == run_id)
        )
        raw = result.scalar_one_or_none()
        if not raw:
            return {}
        return json.loads(raw)

    async def list_observations(self, run_id: int) -> list[dict[str, Any]]:
        result = await self._session.execute(
            select(HeartbeatApiObservationModel)
            .where(HeartbeatApiObservationModel.run_id == run_id)
            .order_by(HeartbeatApiObservationModel.recorded_at)
        )
        return [json.loads(row.observation_json) for row in result.scalars().all()]

    async def upsert_mapping_from_discovery(
        self,
        site_id: int,
        result: HeartbeatEvDiscoveryResult,
        *,
        physical_charger_id: int | None = None,
    ) -> VirtualEvMappingRecord | None:
        ev_id = result.resolved_ev_id.heartbeat_ev_id
        if not ev_id:
            return None
        name = result.resolved_ev_id.ev_name or ev_id
        existing = await self._session.execute(
            select(HeartbeatEvMappingModel).where(
                HeartbeatEvMappingModel.site_id == site_id,
                HeartbeatEvMappingModel.heartbeat_ev_id == ev_id,
            )
        )
        row = existing.scalar_one_or_none()
        if row is None:
            row = HeartbeatEvMappingModel(
                site_id=site_id,
                heartbeat_ev_id=ev_id,
                heartbeat_ev_name=name,
                physical_charger_id=physical_charger_id,
                confidence_pct=result.resolved_ev_id.confidence_pct,
                last_discovery_at=result.completed_at,
            )
            self._session.add(row)
        else:
            row.heartbeat_ev_name = name
            row.confidence_pct = result.resolved_ev_id.confidence_pct
            row.last_discovery_at = result.completed_at
            if physical_charger_id is not None:
                row.physical_charger_id = physical_charger_id
        await self._session.flush()
        return self._to_mapping(row)

    async def list_mappings(self, site_id: int) -> list[VirtualEvMappingRecord]:
        result = await self._session.execute(
            select(HeartbeatEvMappingModel).where(HeartbeatEvMappingModel.site_id == site_id)
        )
        return [self._to_mapping(row) for row in result.scalars().all()]

    async def update_mapping(
        self,
        mapping_id: int,
        site_id: int,
        *,
        enabled: bool | None = None,
        physical_charger_id: int | None = None,
        vehicle_id: int | None = None,
    ) -> VirtualEvMappingRecord | None:
        result = await self._session.execute(
            select(HeartbeatEvMappingModel).where(
                HeartbeatEvMappingModel.id == mapping_id,
                HeartbeatEvMappingModel.site_id == site_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        if enabled is not None:
            row.enabled = enabled
        if physical_charger_id is not None:
            row.physical_charger_id = physical_charger_id
        if vehicle_id is not None:
            row.vehicle_id = vehicle_id
        await self._session.flush()
        return self._to_mapping(row)

    async def save_write_test(
        self,
        site_id: int,
        heartbeat_ev_id: str,
        classification: str,
        *,
        dry_run: bool,
        steps: list[dict[str, Any]],
        result: dict[str, Any],
        started_at: datetime,
        completed_at: datetime | None,
    ) -> int:
        row = HeartbeatWriteTestModel(
            site_id=site_id,
            heartbeat_ev_id=heartbeat_ev_id,
            classification=classification,
            dry_run=dry_run,
            steps_json=json.dumps(steps),
            result_json=json.dumps(result),
            started_at=started_at,
            completed_at=completed_at,
        )
        self._session.add(row)
        await self._session.flush()
        return row.id

    async def save_decision(
        self,
        site_id: int,
        *,
        charger_id: int | None,
        heartbeat_ev_id: str | None,
        bridge_state: str,
        heartbeat_mode: str | None,
        ai_decision: str | None,
        decision: dict[str, Any],
        reason: str,
    ) -> None:
        self._session.add(
            VirtualChargerDecisionModel(
                site_id=site_id,
                charger_id=charger_id,
                heartbeat_ev_id=heartbeat_ev_id,
                bridge_state=bridge_state,
                heartbeat_mode=heartbeat_mode,
                ai_decision=ai_decision,
                decision_json=json.dumps(decision, default=str),
                reason=reason,
                recorded_at=datetime.now(UTC),
            )
        )
        await self._session.flush()

    async def save_command(
        self,
        site_id: int,
        *,
        charger_id: int | None,
        action: str,
        current_a: float | None,
        reason: str,
        simulated: bool,
        applied: bool,
    ) -> None:
        self._session.add(
            VirtualChargerCommandModel(
                site_id=site_id,
                charger_id=charger_id,
                action=action,
                current_a=current_a,
                reason=reason,
                simulated=simulated,
                applied=applied,
                recorded_at=datetime.now(UTC),
            )
        )
        await self._session.flush()

    async def list_recent_commands(self, site_id: int, *, limit: int = 50) -> list[dict[str, Any]]:
        result = await self._session.execute(
            select(VirtualChargerCommandModel)
            .where(VirtualChargerCommandModel.site_id == site_id)
            .order_by(desc(VirtualChargerCommandModel.recorded_at))
            .limit(limit)
        )
        return [
            {
                "action": row.action,
                "current_a": row.current_a,
                "reason": row.reason,
                "simulated": row.simulated,
                "applied": row.applied,
                "recorded_at": row.recorded_at.isoformat(),
            }
            for row in result.scalars().all()
        ]

    async def list_recent_decisions(self, site_id: int, *, limit: int = 50) -> list[dict[str, Any]]:
        result = await self._session.execute(
            select(VirtualChargerDecisionModel)
            .where(VirtualChargerDecisionModel.site_id == site_id)
            .order_by(desc(VirtualChargerDecisionModel.recorded_at))
            .limit(limit)
        )
        rows: list[dict[str, Any]] = []
        for row in result.scalars().all():
            rows.append(
                {
                    "bridge_state": row.bridge_state,
                    "heartbeat_ev_id": row.heartbeat_ev_id,
                    "heartbeat_mode": row.heartbeat_mode,
                    "ai_decision": row.ai_decision,
                    "reason": row.reason,
                    "recorded_at": row.recorded_at.isoformat(),
                }
            )
        return rows

    async def save_replay_run(
        self,
        site_id: int,
        hours: int,
        report_json: dict[str, Any],
        report_text: str,
        started_at: datetime,
        completed_at: datetime | None,
    ) -> int:
        row = VirtualChargerReplayRunModel(
            site_id=site_id,
            hours=hours,
            report_json=json.dumps(report_json),
            report_text=report_text,
            started_at=started_at,
            completed_at=completed_at,
        )
        self._session.add(row)
        await self._session.flush()
        return row.id

    def _to_settings(self, row: HeartbeatBridgeSettingsModel) -> HeartbeatBridgeSettingsRecord:
        return HeartbeatBridgeSettingsRecord(
            site_id=row.site_id,
            discovery_enabled=row.discovery_enabled,
            write_enabled=row.write_enabled,
            virtual_bridge_enabled=row.virtual_bridge_enabled,
            physical_control_enabled=row.physical_control_enabled,
            soc_sync_enabled=row.soc_sync_enabled,
            replay_enabled=row.replay_enabled,
            simulation_mode=row.simulation_mode,
            confidence_threshold_pct=row.confidence_threshold_pct,
            battery_priority_mode=row.battery_priority_mode,
        )

    def _to_run(self, row: HeartbeatDiscoveryRunModel) -> StoredDiscoveryRun:
        return StoredDiscoveryRun(
            id=row.id,
            site_id=row.site_id,
            status=row.status,
            system_id=row.system_id,
            conclusion_class=row.conclusion_class,
            bridge_lifecycle=row.bridge_lifecycle,
            resolved_ev_id=row.resolved_ev_id,
            confidence_pct=row.confidence_pct,
            report_text=row.report_text,
            started_at=row.started_at,
            completed_at=row.completed_at,
        )

    def _to_mapping(self, row: HeartbeatEvMappingModel) -> VirtualEvMappingRecord:
        return VirtualEvMappingRecord(
            id=row.id,
            site_id=row.site_id,
            heartbeat_ev_id=row.heartbeat_ev_id,
            heartbeat_ev_name=row.heartbeat_ev_name,
            physical_charger_id=row.physical_charger_id,
            vehicle_id=row.vehicle_id,
            provider=row.provider,
            enabled=row.enabled,
            confidence_pct=row.confidence_pct,
            last_discovery_at=row.last_discovery_at,
        )
