from __future__ import annotations

from datetime import date, datetime
from typing import Any

from energy_core.integrations.heartbeat.connection import CLOUD_PORT, HeartbeatConnectionType
from pydantic import BaseModel, Field, field_validator

class ChargeFinderStatusResponse(BaseModel):
    health_status: str
    unified_health_status: str
    enabled: bool
    mode: str
    search_radius_m: int
    cache_ttl_seconds: int
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    last_lookup_at: datetime | None = None
    last_latency_ms: int | None = None
    consecutive_failures: int = 0
    last_error: str | None = None
    cache_hits: int = 0
    cache_misses: int = 0
    parser_failures: int = 0
    blocked_until: datetime | None = None
    browser_status: str | None = None
    parsing_version: str = "1"
    metrics: dict[str, float | int] = Field(default_factory=dict)


class ChargeFinderDiagnosticsResponse(BaseModel):
    health_status: str
    unified_health_status: str
    enabled: bool
    mode: str
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    last_lookup_at: datetime | None = None
    last_latency_ms: int | None = None
    consecutive_failures: int = 0
    last_error: str | None = None
    cache_hits: int = 0
    cache_misses: int = 0
    parser_failures: int = 0
    blocked_until: datetime | None = None
    browser_status: str | None = None
    parsing_version: str = "1"
    metrics: dict[str, float | int] = Field(default_factory=dict)


class ChargeFinderTestLookupRequest(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    radius_m: int | None = None
    use_mercedes_position: bool = False
    site_slug: str | None = None


class ChargeFinderTestLookupResponse(BaseModel):
    latitude: float
    longitude: float
    radius_m: int
    candidate_count: int
    candidates: list[dict[str, str | float | None]] = Field(default_factory=list)


class ChargeFinderRawLookupResponse(BaseModel):
    latitude: float
    longitude: float
    radius_m: int
    stations: list[dict] = Field(default_factory=list)
