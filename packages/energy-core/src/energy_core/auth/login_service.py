"""Login, lockout, and password change logic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from energy_core.auth.datetime_utils import ensure_utc, utc_now
from energy_core.auth.passwords import hash_password, validate_password_policy, verify_password
from energy_core.auth.repos.auth_audit_repo import AuthAuditRepository
from energy_core.auth.repos.user_repo import UserRepository
from energy_core.config import Settings
from energy_core.db.models import EmicUserModel
from sqlalchemy.ext.asyncio import AsyncSession


GENERIC_LOGIN_ERROR = "Felaktigt användarnamn eller lösenord."


@dataclass(frozen=True, slots=True)
class LoginResult:
    user: EmicUserModel


class LoginService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._users = UserRepository(session)
        self._audit = AuthAuditRepository(session)

    async def authenticate(
        self,
        username_or_email: str,
        password: str,
        *,
        source_ip: str | None = None,
    ) -> LoginResult:
        user = await self._users.get_by_username_or_email(username_or_email)
        if user is None:
            await self._audit.append(
                event_type="LOGIN_FAILED",
                action="login",
                success=False,
                username=username_or_email[:64],
                source_ip=source_ip,
                metadata={"reason": "unknown_user"},
            )
            raise ValueError(GENERIC_LOGIN_ERROR)

        if not user.is_active:
            await self._audit.append(
                event_type="LOGIN_FAILED",
                action="login",
                success=False,
                user_id=user.id,
                username=user.username,
                source_ip=source_ip,
                metadata={"reason": "disabled"},
            )
            raise ValueError(GENERIC_LOGIN_ERROR)

        now = utc_now()
        lockout_until = ensure_utc(user.lockout_until) if user.lockout_until else None
        if user.is_locked and lockout_until and lockout_until > now:
            await self._audit.append(
                event_type="LOCKOUT",
                action="login",
                success=False,
                user_id=user.id,
                username=user.username,
                source_ip=source_ip,
            )
            raise ValueError(GENERIC_LOGIN_ERROR)

        if user.is_locked and lockout_until and lockout_until <= now:
            user.is_locked = False
            user.lockout_until = None
            user.failed_login_attempts = 0

        if not verify_password(password, user.password_hash):
            lockout_until = None
            if user.failed_login_attempts + 1 >= self._settings.emic_login_max_attempts:
                lockout_until = now + timedelta(minutes=self._settings.emic_login_lockout_minutes)
            await self._users.record_failed_login(user, lockout_until=lockout_until)
            await self._audit.append(
                event_type="LOGIN_FAILED",
                action="login",
                success=False,
                user_id=user.id,
                username=user.username,
                source_ip=source_ip,
                metadata={"reason": "bad_password"},
            )
            raise ValueError(GENERIC_LOGIN_ERROR)

        await self._users.record_successful_login(user)
        await self._audit.append(
            event_type="LOGIN_SUCCESS",
            action="login",
            success=True,
            user_id=user.id,
            username=user.username,
            source_ip=source_ip,
        )
        return LoginResult(user=user)

    async def change_password(
        self,
        user: EmicUserModel,
        *,
        current_password: str,
        new_password: str,
        source_ip: str | None = None,
    ) -> None:
        if not verify_password(current_password, user.password_hash):
            await self._audit.append(
                event_type="PASSWORD_CHANGED",
                action="change_password",
                success=False,
                user_id=user.id,
                username=user.username,
                source_ip=source_ip,
            )
            raise ValueError("Nuvarande lösenord är felaktigt.")

        policy_error = validate_password_policy(new_password)
        if policy_error:
            raise ValueError(policy_error)

        user.password_hash = hash_password(new_password)
        user.password_changed_at = utc_now()
        user.must_change_password = False
        user.updated_at = utc_now()
        await self._session.flush()
        await self._audit.append(
            event_type="PASSWORD_CHANGED",
            action="change_password",
            success=True,
            user_id=user.id,
            username=user.username,
            source_ip=source_ip,
        )
