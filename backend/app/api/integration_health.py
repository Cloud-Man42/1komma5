"""Integration health API."""

from __future__ import annotations

from app.deps import get_app_settings, get_db_session
from energy_core.db.repositories import SiteRepository
from energy_core.integrations.health import IntegrationHealthRecorder
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["integration-health"])


class IntegrationHealthItem(BaseModel):
    provider: str
    status: str
    last_success_at: str | None = None
    last_attempt_at: str | None = None
    latency_ms: float | None = None
    consecutive_failures: int = 0
    stale_seconds: float | None = None
    circuit_breaker_state: str | None = None
    last_error_class: str | None = None


class IntegrationHealthResponse(BaseModel):
    slug: str
    providers: list[IntegrationHealthItem] = Field(default_factory=list)


@router.get("/sites/{slug}/integration-health", response_model=IntegrationHealthResponse)
async def get_integration_health(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    settings=Depends(get_app_settings),
) -> IntegrationHealthResponse:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    recorder = IntegrationHealthRecorder(session, is_sqlite=settings.is_sqlite)
    providers = await recorder.list_for_site(site.id)
    return IntegrationHealthResponse(
        slug=slug,
        providers=[IntegrationHealthItem(**item) for item in providers],
    )
