"""Integration health API."""

from __future__ import annotations

from app.deps import get_app_settings, get_db_session
from app.site_access import require_site_with_permission
from app.user_auth import require_authenticated
from energy_core.auth.principal import Principal
from energy_core.config import Settings
from energy_core.contracts.health import HealthStatus, aggregate_health_status
from energy_core.db.repositories import SiteRepository
from energy_core.platform.health.aggregator import HealthAggregator
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["integration-health"])


class IntegrationHealthItem(BaseModel):
    provider: str
    status: str
    health_status: str
    last_success_at: str | None = None
    last_attempt_at: str | None = None
    latency_ms: float | None = None
    consecutive_failures: int = 0
    stale_seconds: float | None = None
    circuit_breaker_state: str | None = None
    last_error_class: str | None = None


class IntegrationHealthResponse(BaseModel):
    slug: str
    overall_health_status: str
    providers: list[IntegrationHealthItem] = Field(default_factory=list)


@router.get("/sites/{slug}/integration-health", response_model=IntegrationHealthResponse)
async def get_integration_health(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    principal: Principal = Depends(require_authenticated),
) -> IntegrationHealthResponse:
    site = await require_site_with_permission(session, principal, settings, slug, "system.health.read")
    aggregator = HealthAggregator(session, is_sqlite=settings.is_sqlite)
    records = await aggregator.list_for_site(site.id)
    legacy_rows = await aggregator.recorder.list_for_site(site.id)
    legacy_by_provider = {row["provider"]: row for row in legacy_rows}
    provider_statuses: list[HealthStatus] = []
    items: list[IntegrationHealthItem] = []
    for record in records:
        provider_statuses.append(record.status)
        legacy = legacy_by_provider.get(record.provider, {})
        items.append(
            IntegrationHealthItem(
                provider=record.provider,
                status=str(legacy.get("status", "unknown")),
                health_status=record.status.value,
                last_success_at=legacy.get("last_success_at"),
                last_attempt_at=legacy.get("last_attempt_at"),
                latency_ms=legacy.get("latency_ms"),
                consecutive_failures=int(legacy.get("consecutive_failures", 0) or 0),
                stale_seconds=legacy.get("stale_seconds"),
                circuit_breaker_state=legacy.get("circuit_breaker_state"),
                last_error_class=legacy.get("last_error_class"),
            )
        )
    overall = aggregate_health_status(tuple(provider_statuses))
    return IntegrationHealthResponse(
        slug=slug,
        overall_health_status=overall.value,
        providers=items,
    )
