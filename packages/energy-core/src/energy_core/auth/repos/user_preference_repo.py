"""Persisted user site selection preferences."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.db.models import EmicUserSitePreferencesModel
from sqlalchemy.ext.asyncio import AsyncSession


class UserSitePreferenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_selected_slugs(self, user_id: int) -> list[str]:
        row = await self._session.get(EmicUserSitePreferencesModel, user_id)
        if row is None or not row.selected_site_slugs:
            return []
        if isinstance(row.selected_site_slugs, list):
            return [str(s) for s in row.selected_site_slugs]
        return []

    async def set_selected_slugs(self, user_id: int, slugs: list[str]) -> list[str]:
        unique = list(dict.fromkeys(slugs))
        row = await self._session.get(EmicUserSitePreferencesModel, user_id)
        if row is None:
            row = EmicUserSitePreferencesModel(user_id=user_id, selected_site_slugs=unique)
            self._session.add(row)
        else:
            row.selected_site_slugs = unique
            row.updated_at = datetime.now(UTC)
        await self._session.flush()
        return unique
