"""Session lifecycle for EMIC user auth."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from energy_core.auth.datetime_utils import ensure_utc, utc_now
from energy_core.auth.principal import AuthMethod, Principal
from energy_core.auth.repos.session_repo import SessionRepository
from energy_core.auth.repos.user_repo import UserRepository
from energy_core.auth.session_tokens import generate_csrf_token, generate_session_token, hash_token
from energy_core.config import Settings
from energy_core.db.models import EmicUserSessionModel
from energy_core.tenancy.repo import TenantRepository
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class CreatedSession:
    session: EmicUserSessionModel
    session_token: str
    csrf_token: str


class SessionService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._sessions = SessionRepository(session)
        self._users = UserRepository(session)

    def _ttl(self) -> timedelta:
        return timedelta(hours=self._settings.emic_session_ttl_hours)

    def _slide_ttl(self) -> timedelta:
        return timedelta(minutes=self._settings.emic_session_slide_minutes)

    async def create_session(
        self,
        user_id: int,
        *,
        source_ip: str | None,
        user_agent: str | None,
    ) -> CreatedSession:
        generated = generate_session_token()
        csrf = generate_csrf_token()
        now = utc_now()
        row = await self._sessions.create(
            user_id=user_id,
            token_hash=generated.token_hash,
            token_prefix=generated.token_prefix,
            csrf_token_hash=hash_token(csrf),
            expires_at=now + self._ttl(),
            source_ip=source_ip,
            user_agent=user_agent,
        )
        return CreatedSession(session=row, session_token=generated.token, csrf_token=csrf)

    async def resolve_principal(self, session_token: str | None) -> Principal | None:
        if not session_token:
            return None
        row = await self._sessions.get_by_token(session_token)
        if row is None:
            return None
        now = utc_now()
        expires_at = ensure_utc(row.expires_at)
        if expires_at <= now:
            await self._sessions.revoke(row)
            return None
        user = row.user
        if not user.is_active:
            await self._sessions.revoke(row)
            return None

        last_seen_at = ensure_utc(row.last_seen_at)
        if last_seen_at + self._slide_ttl() <= now:
            await self._sessions.touch(row, expires_at=now + self._ttl())
        else:
            await self._sessions.touch(row)

        tenant_repo = TenantRepository(self._session)
        platform_roles = await tenant_repo.list_platform_roles(user.id)
        tenant_id = row.active_tenant_id
        tenant_user_id: int | None = None
        roles = frozenset(r.name for r in user.roles)
        permissions = self._users.resolve_permissions(user)
        site_ids = self._users.resolve_site_ids(user)

        if tenant_id is not None:
            membership = await tenant_repo.get_membership(tenant_id, user.id)
            if membership is not None and membership.is_active:
                tenant_user_id = membership.id
                roles = frozenset(r.name for r in membership.roles)
                permissions = self._resolve_membership_permissions(membership)
                site_ids = await tenant_repo.resolve_membership_site_ids(membership)
        else:
            memberships = await tenant_repo.list_for_user(user.id)
            if len(memberships) == 1:
                tenant_id = memberships[0].id
                membership = await tenant_repo.get_membership(tenant_id, user.id)
                if membership is not None:
                    tenant_user_id = membership.id
                    roles = frozenset(r.name for r in membership.roles)
                    permissions = self._resolve_membership_permissions(membership)
                    site_ids = await tenant_repo.resolve_membership_site_ids(membership)
                    row.active_tenant_id = tenant_id
                    await self._session.flush()

        return Principal(
            user_id=user.id,
            username=user.username,
            email=user.email,
            display_name=user.display_name or user.username,
            roles=roles,
            permissions=permissions,
            site_ids=site_ids,
            auth_method=AuthMethod.SESSION,
            session_id=row.id,
            must_change_password=user.must_change_password,
            tenant_id=tenant_id,
            tenant_user_id=tenant_user_id,
            platform_roles=platform_roles,
        )

    @staticmethod
    def _resolve_membership_permissions(membership) -> frozenset[str]:
        perms: set[str] = set()
        for role in membership.roles:
            for perm in role.permissions:
                perms.add(perm.key)
        return frozenset(perms)

    async def set_active_tenant(self, session_token: str, tenant_id: int) -> bool:
        row = await self._sessions.get_by_token(session_token)
        if row is None:
            return False
        membership = await TenantRepository(self._session).get_membership(tenant_id, row.user_id)
        if membership is None or not membership.is_active:
            return False
        row.active_tenant_id = tenant_id
        await self._session.flush()
        return True

    async def verify_csrf(self, session_token: str, csrf_token: str | None) -> bool:
        if not csrf_token:
            return False
        row = await self._sessions.get_by_token(session_token)
        if row is None:
            return False
        from energy_core.auth.session_tokens import verify_token

        return verify_token(csrf_token, row.csrf_token_hash)

    async def revoke_session(self, session_token: str) -> None:
        row = await self._sessions.get_by_token(session_token)
        if row is not None:
            await self._sessions.revoke(row)

    async def revoke_all_user_sessions(self, user_id: int) -> None:
        await self._sessions.revoke_all_for_user(user_id)
