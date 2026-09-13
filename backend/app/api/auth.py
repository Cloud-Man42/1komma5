"""EMIC user authentication API."""

from __future__ import annotations

from typing import Annotated

from app.deps import get_app_settings, get_db_session
from app.login_rate_limit import LOGIN_RATE_LIMITER
from app.user_auth import (
    CSRF_COOKIE,
    CSRF_HEADER,
    SESSION_COOKIE,
    build_user_response,
    require_authenticated,
    verify_csrf,
)
from energy_core.auth.login_service import LoginService
from energy_core.auth.passwords import validate_password_policy
from energy_core.auth.repos.auth_audit_repo import AuthAuditRepository
from energy_core.auth.repos.user_repo import UserRepository
from energy_core.auth.session_service import SessionService
from energy_core.config import Settings
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username_or_email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=1, max_length=128)


def _cookie_params(settings: Settings) -> dict:
    return {
        "httponly": True,
        "secure": settings.emic_cookie_secure or settings.is_production,
        "samesite": "lax",
        "path": "/",
    }


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> dict:
    client_ip = request.client.host if request.client else "unknown"
    if not LOGIN_RATE_LIMITER.check(client_ip, limit_per_minute=settings.emic_login_rate_limit_per_minute):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts")

    login_service = LoginService(session, settings)
    try:
        result = await login_service.authenticate(
            body.username_or_email,
            body.password,
            source_ip=client_ip,
        )
    except ValueError as exc:
        await session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    created = await SessionService(session, settings).create_session(
        result.user.id,
        source_ip=client_ip,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()

    cookie_kwargs = _cookie_params(settings)
    max_age = settings.emic_session_ttl_hours * 3600
    response.set_cookie(SESSION_COOKIE, created.session_token, max_age=max_age, **cookie_kwargs)
    response.set_cookie(
        CSRF_COOKIE,
        created.csrf_token,
        max_age=max_age,
        httponly=False,
        secure=cookie_kwargs["secure"],
        samesite="lax",
        path="/",
    )

    user_repo = UserRepository(session)
    principal_permissions = user_repo.resolve_permissions(result.user)
    from energy_core.auth.principal import AuthMethod, Principal

    principal = Principal(
        user_id=result.user.id,
        username=result.user.username,
        email=result.user.email,
        display_name=result.user.display_name or result.user.username,
        roles=frozenset(r.name for r in result.user.roles),
        permissions=principal_permissions,
        site_ids=user_repo.resolve_site_ids(result.user),
        auth_method=AuthMethod.SESSION,
        session_id=created.session.id,
        must_change_password=result.user.must_change_password,
    )
    return await build_user_response(session, principal)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    principal=Depends(require_authenticated),
) -> dict:
    await verify_csrf(request, session, settings)
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        await SessionService(session, settings).revoke_session(token)
    if principal.user_id is not None:
        await AuthAuditRepository(session).append(
            event_type="LOGOUT",
            action="logout",
            success=True,
            user_id=principal.user_id,
            username=principal.username,
            source_ip=request.client.host if request.client else None,
        )
    await session.commit()
    cookie_kwargs = _cookie_params(settings)
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        secure=cookie_kwargs["secure"],
        samesite=cookie_kwargs["samesite"],
    )
    response.delete_cookie(
        CSRF_COOKIE,
        path="/",
        secure=cookie_kwargs["secure"],
        samesite=cookie_kwargs["samesite"],
    )
    return {"ok": True}


@router.get("/me")
async def me(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    principal=Depends(require_authenticated),
) -> dict:
    return await build_user_response(session, principal)


@router.get("/csrf")
async def csrf_token(
    request: Request,
    _principal=Depends(require_authenticated),
) -> dict:
    csrf = request.cookies.get(CSRF_COOKIE)
    if not csrf:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No CSRF token")
    return {"csrfToken": csrf, "header": CSRF_HEADER}


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    principal=Depends(require_authenticated),
) -> dict:
    await verify_csrf(request, session, settings)
    if principal.user_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Break-glass cannot change password here")

    policy_error = validate_password_policy(body.new_password)
    if policy_error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=policy_error)

    user = await UserRepository(session).get_by_id(principal.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    login_service = LoginService(session, settings)
    try:
        await login_service.change_password(
            user,
            current_password=body.current_password,
            new_password=body.new_password,
            source_ip=request.client.host if request.client else None,
        )
    except ValueError as exc:
        await session.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await SessionService(session, settings).revoke_all_user_sessions(user.id)
    await session.commit()
    return {"ok": True}
