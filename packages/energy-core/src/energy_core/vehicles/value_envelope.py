"""Helpers for timed value quality envelopes."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.vehicles.abstractions.models import TimedValue, ValueQuality
from energy_core.vehicles.mercedes.constants import STALE_TELEMETRY_SECONDS


def build_timed_value(
    value: float | bool | str | None,
    *,
    source_timestamp: datetime | None,
    received_timestamp: datetime | None,
    estimated: bool = False,
) -> TimedValue:
    now = datetime.now(UTC)
    received = received_timestamp or now
    age = None
    if received is not None:
        ts = received if received.tzinfo else received.replace(tzinfo=UTC)
        age = max(0.0, (now - ts).total_seconds())
    quality = _quality_for(value=value, age_seconds=age, estimated=estimated)
    return TimedValue(
        value=value,
        source_timestamp=source_timestamp,
        received_timestamp=received,
        age_seconds=age,
        quality=quality,
    )


def _quality_for(*, value: float | bool | str | None, age_seconds: float | None, estimated: bool) -> ValueQuality:
    if value is None:
        return ValueQuality.UNAVAILABLE
    if estimated:
        return ValueQuality.ESTIMATED
    if age_seconds is None:
        return ValueQuality.UNAVAILABLE
    if age_seconds <= 120:
        return ValueQuality.LIVE
    if age_seconds <= STALE_TELEMETRY_SECONDS:
        return ValueQuality.RECENT
    return ValueQuality.STALE
