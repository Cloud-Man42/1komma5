"""Charging session reconciliation audit."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class SessionRevision:
    field_name: str
    previous_value: str | None
    new_value: str | None
    revision_reason: str
    revised_at: datetime


class ChargingSessionReconciliationService:
    def build_revision(
        self,
        *,
        field_name: str,
        previous_value: str | float | None,
        new_value: str | float | None,
        reason: str,
    ) -> SessionRevision | None:
        prev = None if previous_value is None else str(previous_value)
        new = None if new_value is None else str(new_value)
        if prev == new:
            return None
        return SessionRevision(
            field_name=field_name,
            previous_value=prev,
            new_value=new,
            revision_reason=reason,
            revised_at=datetime.now(UTC),
        )
