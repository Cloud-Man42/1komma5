"""Runtime authorization DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class RuntimeAuthorizationRecord:
    id: int
    module_id: str
    version: str
    artifact_sha256: str
    publisher_id: str
    site_id: int
    approved_by: str
    approved_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    reason: str | None

    @property
    def active(self) -> bool:
        return self.revoked_at is None
