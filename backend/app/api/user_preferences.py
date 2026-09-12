"""User site selection preferences."""

from __future__ import annotations

from typing import Annotated

from app.deps import get_app_settings, get_db_session
from app.site_access import filter_sites_for_principal
from app.user_auth import require_authenticated, verify_csrf
from energy_core.auth.principal import Principal
from energy_core.auth.repos.user_preference_repo import UserSitePreferenceRepository
from energy_core.config import Settings
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/user", tags=["user-preferences"])


class SiteSelectionPatch(BaseModel):
    selected_site_slugs: list[str] = Field(default_factory=list, max_length=32)


def _sanitize_slugs(requested: list[str], accessible_slugs: set[str]) -> list[str]:
    return [s for s in dict.fromkeys(requested) if s in accessible_slugs]


def _selection_mode(count: int) -> str:
    if count <= 0:
        return "none"
    if count == 1:
        return "single"
    return "multi"


@router.get("/site-selection")
async def get_site_selection(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    principal: Annotated[Principal, Depends(require_authenticated)],
) -> dict:
    accessible = await filter_sites_for_principal(session, principal, auth_enabled=settings.emic_user_auth_enabled)
    accessible_slugs = {s.slug for s in accessible}
    ordered_accessible = [s.slug for s in accessible]

    if principal.user_id is None:
        selected = ordered_accessible
    else:
        repo = UserSitePreferenceRepository(session)
        stored = _sanitize_slugs(await repo.get_selected_slugs(principal.user_id), accessible_slugs)
        if not stored and ordered_accessible:
            selected = ordered_accessible
        else:
            selected = stored

    return {
        "selectedSiteSlugs": selected,
        "accessibleSiteSlugs": ordered_accessible,
        "mode": _selection_mode(len(selected)),
    }


@router.patch("/site-selection")
async def patch_site_selection(
    body: SiteSelectionPatch,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    principal: Annotated[Principal, Depends(require_authenticated)],
) -> dict:
    await verify_csrf(request, session, settings)
    if principal.user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required to persist selection")

    accessible = await filter_sites_for_principal(session, principal, auth_enabled=settings.emic_user_auth_enabled)
    accessible_slugs = {s.slug for s in accessible}
    sanitized = _sanitize_slugs(body.selected_site_slugs, accessible_slugs)

    for slug in body.selected_site_slugs:
        if slug not in accessible_slugs:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Site access denied: {slug}")

    repo = UserSitePreferenceRepository(session)
    saved = await repo.set_selected_slugs(principal.user_id, sanitized)
    await session.commit()

    return {
        "selectedSiteSlugs": saved,
        "accessibleSiteSlugs": [s.slug for s in accessible],
        "mode": _selection_mode(len(saved)),
    }
