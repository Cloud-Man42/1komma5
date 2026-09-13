"""Bootstrap first SUPER_ADMIN and RBAC seed."""

from __future__ import annotations

import logging

from energy_core.auth.normalize import normalize_email, normalize_username
from energy_core.auth.passwords import hash_password, validate_password_policy
from energy_core.auth.repos.user_repo import RoleRepository, UserRepository
from energy_core.auth.seed_rbac import ensure_rbac_seed
from energy_core.config import Settings
from energy_core.db.repositories import SiteRepository
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def ensure_emic_auth_bootstrap(session: AsyncSession, settings: Settings) -> None:
    await ensure_rbac_seed(session)

    user_repo = UserRepository(session)
    if await user_repo.count_users() > 0:
        return

    email = (settings.emic_bootstrap_admin_email or "").strip()
    password = settings.emic_bootstrap_admin_password or ""
    if not email or not password:
        logger.info("No EMIC users and bootstrap credentials unset; skipping admin bootstrap")
        return

    policy_error = validate_password_policy(password)
    if policy_error:
        logger.error("Bootstrap admin password rejected by policy: %s", policy_error)
        return

    username = email.split("@")[0] if "@" in email else email
    user = await user_repo.create_user(
        username=username,
        email=email,
        password_hash=hash_password(password),
        display_name=username,
        must_change_password=False,
    )
    user.email_verified = True
    user.username_normalized = normalize_username(username)
    user.email_normalized = normalize_email(email)

    role_repo = RoleRepository(session)
    super_admin = await role_repo.get_by_name("SUPER_ADMIN")
    if super_admin is not None:
        await user_repo.set_roles(user.id, [super_admin.id])

    sites = await SiteRepository(session).list_all()
    if sites:
        await user_repo.set_site_access(user.id, [s.id for s in sites])

    from energy_core.tenancy.sync import sync_tenant_memberships_for_default_tenant

    await sync_tenant_memberships_for_default_tenant(session)

    logger.info("Bootstrap SUPER_ADMIN created for %s", email)
