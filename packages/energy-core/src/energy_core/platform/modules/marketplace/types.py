"""Marketplace trust metadata types (Step 5C.1 / 5C.1.5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class MetadataHealth(StrEnum):
    UNINITIALIZED = "uninitialized"
    HEALTHY = "healthy"
    STALE = "stale"
    EXPIRED = "expired"
    OFFLINE = "offline"
    INVALID = "invalid"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"


class RevocationFreshness(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    EXPIRED = "expired"
    UNAVAILABLE = "unavailable"


class SyncOutcome(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    REJECTED = "rejected"
    SKIPPED = "skipped"
    IN_PROGRESS = "in_progress"


class MetadataErrorCode(StrEnum):
    NETWORK_ERROR = "NETWORK_ERROR"
    TLS_ERROR = "TLS_ERROR"
    HTTP_ERROR = "HTTP_ERROR"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    UNKNOWN_ROOT = "UNKNOWN_ROOT"
    EXPIRED_METADATA = "EXPIRED_METADATA"
    METADATA_ROLLBACK_DETECTED = "METADATA_ROLLBACK_DETECTED"
    INVALID_METADATA = "INVALID_METADATA"
    INVALID_CACHE = "INVALID_CACHE"
    SIZE_LIMIT_EXCEEDED = "SIZE_LIMIT_EXCEEDED"
    REDIRECT_REJECTED = "REDIRECT_REJECTED"
    SYNC_IN_PROGRESS = "SYNC_IN_PROGRESS"
    TIMEOUT = "TIMEOUT"


# Allowed metadata target paths — not package artifacts
CATALOG_TARGET_PATH = "emic/catalog.json"
REVOCATIONS_TARGET_PATH = "emic/revocations.json"
ADVISORIES_TARGET_PATH = "emic/advisories.json"
ALLOWED_METADATA_TARGETS = frozenset({CATALOG_TARGET_PATH, REVOCATIONS_TARGET_PATH, ADVISORIES_TARGET_PATH})


@dataclass(frozen=True, slots=True)
class MarketplaceMetadataVersions:
    root_version: int
    timestamp_version: int
    snapshot_version: int
    targets_version: int


@dataclass(frozen=True, slots=True)
class MarketplaceSyncResult:
    outcome: SyncOutcome
    message: str
    versions: MarketplaceMetadataVersions | None = None
    catalog: dict[str, Any] | None = None
    revocations: dict[str, Any] | None = None
    advisories: dict[str, Any] | None = None
    metadata_expires_at: datetime | None = None
    error_code: MetadataErrorCode | None = None
    error_category: str | None = None


@dataclass(frozen=True, slots=True)
class RollbackRejection:
    role: str
    trusted_version: int
    incoming_version: int


@dataclass(frozen=True, slots=True)
class ApplySyncResult:
    row_changed: bool
    promoted: bool
    rollback: RollbackRejection | None = None
    revocations_changed: bool = False
    advisories_changed: bool = False
    root_rotated: bool = False
    trust_event: TrustMetadataUpdatedEvent | None = None


@dataclass(frozen=True, slots=True)
class MarketplaceStatusView:
    enabled: bool
    metadata_health: MetadataHealth
    revocation_freshness: RevocationFreshness
    last_sync: datetime | None
    last_success: datetime | None
    last_error: str | None
    sync_failed: bool
    offline: bool
    root_version: int | None
    timestamp_version: int | None
    snapshot_version: int | None
    targets_version: int | None
    catalog_age_seconds: float | None
    revocation_age_seconds: float | None
    cache_generation: int
    catalog_status: str
    revocation_status: str
    revocation_generation: int | None = None


@dataclass(slots=True)
class TrustMetadataUpdatedEvent:
    """Future hook for policy engine — no runtime side effects in 5C.1."""

    cache_generation: int
    versions: MarketplaceMetadataVersions
    catalog: dict[str, Any] | None = None
    revocations: dict[str, Any] | None = None


@dataclass
class TrustMetadataUpdatedListenerRegistry:
    """In-process listeners for post-commit trust metadata updates."""

    _listeners: list[Any] = field(default_factory=list)

    def register(self, callback: Any) -> None:
        self._listeners.append(callback)

    def emit(self, event: TrustMetadataUpdatedEvent) -> None:
        for listener in list(self._listeners):
            listener(event)


trust_metadata_listeners = TrustMetadataUpdatedListenerRegistry()
