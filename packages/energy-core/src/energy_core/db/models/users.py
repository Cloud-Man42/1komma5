"""EMIC application users, RBAC, sessions, and auth audit."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from energy_core.db.models.base import Base


class EmicUserModel(Base):
    __tablename__ = "emic_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    username_normalized: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    email_normalized: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lockout_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    roles: Mapped[list[EmicRoleModel]] = relationship(
        secondary="emic_user_roles", back_populates="users", lazy="selectin"
    )
    site_access: Mapped[list[EmicUserSiteAccessModel]] = relationship(
        back_populates="user", lazy="selectin", cascade="all, delete-orphan"
    )


class EmicRoleModel(Base):
    __tablename__ = "emic_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_system_role: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    users: Mapped[list[EmicUserModel]] = relationship(
        secondary="emic_user_roles", back_populates="roles", lazy="selectin"
    )
    permissions: Mapped[list[EmicPermissionModel]] = relationship(
        secondary="emic_role_permissions", back_populates="roles", lazy="selectin"
    )


class EmicPermissionModel(Base):
    __tablename__ = "emic_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    group_name: Mapped[str | None] = mapped_column(String(64), nullable=True)

    roles: Mapped[list[EmicRoleModel]] = relationship(
        secondary="emic_role_permissions", back_populates="permissions", lazy="selectin"
    )


class EmicUserRoleModel(Base):
    __tablename__ = "emic_user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_emic_user_roles"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("emic_users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("emic_roles.id", ondelete="CASCADE"), primary_key=True)


class EmicRolePermissionModel(Base):
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_emic_role_permissions"),)
    __tablename__ = "emic_role_permissions"

    role_id: Mapped[int] = mapped_column(ForeignKey("emic_roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[int] = mapped_column(ForeignKey("emic_permissions.id", ondelete="CASCADE"), primary_key=True)


class EmicUserSiteAccessModel(Base):
    __tablename__ = "emic_user_site_access"
    __table_args__ = (UniqueConstraint("user_id", "site_id", name="uq_emic_user_site_access"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("emic_users.id", ondelete="CASCADE"), nullable=False, index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)

    user: Mapped[EmicUserModel] = relationship(back_populates="site_access")


class EmicUserSessionModel(Base):
    __tablename__ = "emic_user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("emic_users.id", ondelete="CASCADE"), nullable=False, index=True)
    user: Mapped[EmicUserModel] = relationship(lazy="selectin")
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    token_prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    csrf_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class EmicUserSitePreferencesModel(Base):
    __tablename__ = "emic_user_site_preferences"

    user_id: Mapped[int] = mapped_column(ForeignKey("emic_users.id", ondelete="CASCADE"), primary_key=True)
    selected_site_slugs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  # type: ignore[name-defined]
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class EmicAuthAuditEventModel(Base):
    __tablename__ = "emic_auth_audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("emic_users.id", ondelete="SET NULL"), nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
