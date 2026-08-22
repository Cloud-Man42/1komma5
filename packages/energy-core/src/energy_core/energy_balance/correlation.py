"""Align Sungrow, Halo, Virtual EVSE, and Heartbeat EV telemetry by timestamp."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from energy_core.chargers.meter_adapter import MeterSnapshot
from energy_core.energy.state import EnergyState
from energy_core.sungrow.types import SungrowTelemetrySnapshot
from energy_core.virtual_evse.state import VirtualEvseState


@dataclass(frozen=True, slots=True)
class CorrelatedTelemetry:
    recorded_at: datetime
    aligned: bool
    alignment_delta_seconds: float | None
    sungrow: SungrowTelemetrySnapshot | None
    halo: MeterSnapshot | None
    virtual_evse: VirtualEvseState | None
    heartbeat: EnergyState | None
    failure_reason: str | None = None


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _age_between(a: datetime, b: datetime) -> float:
    return abs((_ensure_utc(a) - _ensure_utc(b)).total_seconds())


def correlate_telemetry(
    *,
    sungrow: SungrowTelemetrySnapshot | None,
    halo: MeterSnapshot | None,
    virtual_evse: VirtualEvseState | None,
    heartbeat: EnergyState | None,
    max_alignment_age_seconds: float,
) -> CorrelatedTelemetry:
    timestamps: list[datetime] = []
    if sungrow is not None:
        timestamps.append(sungrow.recorded_at)
    if halo is not None:
        timestamps.append(halo.recorded_at)
    if virtual_evse is not None:
        timestamps.append(virtual_evse.recorded_at)
    if heartbeat is not None:
        timestamps.append(heartbeat.timestamp)

    if not timestamps:
        return CorrelatedTelemetry(
            recorded_at=datetime.now(UTC),
            aligned=False,
            alignment_delta_seconds=None,
            sungrow=sungrow,
            halo=halo,
            virtual_evse=virtual_evse,
            heartbeat=heartbeat,
            failure_reason="no_telemetry",
        )

    recorded_at = max(_ensure_utc(ts) for ts in timestamps)
    deltas = [_age_between(recorded_at, ts) for ts in timestamps]
    max_delta = max(deltas)
    aligned = max_delta <= max_alignment_age_seconds

    if not aligned:
        return CorrelatedTelemetry(
            recorded_at=recorded_at,
            aligned=False,
            alignment_delta_seconds=max_delta,
            sungrow=sungrow,
            halo=halo,
            virtual_evse=virtual_evse,
            heartbeat=heartbeat,
            failure_reason="timestamp_mismatch",
        )

    return CorrelatedTelemetry(
        recorded_at=recorded_at,
        aligned=True,
        alignment_delta_seconds=max_delta,
        sungrow=sungrow,
        halo=halo,
        virtual_evse=virtual_evse,
        heartbeat=heartbeat,
    )
