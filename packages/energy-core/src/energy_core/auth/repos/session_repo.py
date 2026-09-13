"""User session repository."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.auth.session_tokens import extract_session_prefix, hash_token
from energy_core.db.models import EmicRoleModel, EmicUserModel, EmicUserSessionModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: int,
        token_hash: str,
        token_prefix: str,
        csrf_token_hash: str,
        expires_at: datetime,
        source_ip: str | None,
        user_agent: str | None,
    ) -> EmicUserSessionModel:
        now = datetime.now(UTC)
        row = EmicUserSessionModel(
            user_id=user_id,
            token_hash=token_hash,
            token_prefix=token_prefix,
            csrf_token_hash=csrf_token_hash,
            expires_at=expires_at,
            last_seen_at=now,
            source_ip=source_ip,
            user_agent=user_agent,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_by_token(self, token: str) -> EmicUserSessionModel | None:
        prefix = extract_session_prefix(token)
        if prefix is None:
            return None
        token_hash = hash_token(token)
        stmt = (
            select(EmicUserSessionModel)
            .options(
                selectinload(EmicUserSessionModel.user)
                .selectinload(EmicUserModel.roles)
                .selectinload(EmicRoleModel.permissions),
                selectinload(EmicUserSessionModel.user).selectinload(EmicUserModel.site_access),
            )
            .where(
                EmicUserSessionModel.token_prefix == prefix,
                EmicUserSessionModel.token_hash == token_hash,
                EmicUserSessionModel.revoked_at.is_(None),
            )
        )
        return await self._session.scalar(stmt)

    async def revoke(self, session_row: EmicUserSessionModel) -> None:
        session_row.revoked_at = datetime.now(UTC)
        await self._session.flush()

    async def revoke_all_for_user(self, user_id: int) -> None:
        rows = (
            await self._session.scalars(
                select(EmicUserSessionModel).where(
                    EmicUserSessionModel.user_id == user_id,
                    EmicUserSessionModel.revoked_at.is_(None),
                )
            )
        ).all()
        now = datetime.now(UTC)
        for row in rows:
            row.revoked_at = now
        await self._session.flush()

    async def touch(self, session_row: EmicUserSessionModel, *, expires_at: datetime | None = None) -> None:
        session_row.last_seen_at = datetime.now(UTC)
        if expires_at is not None:
            session_row.expires_at = expires_at
        await self._session.flush()
