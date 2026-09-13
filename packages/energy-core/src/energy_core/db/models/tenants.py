"""Multi-tenant ORM models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from energy_core.db.models.base import Base


class TenantModel(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Stockholm")
    default_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="SEK")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    sites: Mapped[list["SiteModel"]] = relationship(back_populates="tenant")
    tenant_users: Mapped[list["TenantUserModel"]] = relationship(back_populates="tenant")


class TenantUserModel(Base):
    __tablename__ = "tenant_users"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", name="uq_tenant_users_tenant_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("emic_users.id", ondelete="CASCADE"), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    tenant: Mapped[TenantModel] = relationship(back_populates="tenant_users")
    user: Mapped["EmicUserModel"] = relationship(back_populates="tenant_memberships")
    roles: Mapped[list["EmicRoleModel"]] = relationship(
        secondary="tenant_user_roles", back_populates="tenant_users"
    )
    site_access: Mapped[list["TenantUserSiteAccessModel"]] = relationship(
        back_populates="tenant_user", cascade="all, delete-orphan"
    )


class TenantUserRoleModel(Base):
    __tablename__ = "tenant_user_roles"
    __table_args__ = (UniqueConstraint("tenant_user_id", "role_id", name="uq_tenant_user_roles"),)

    tenant_user_id: Mapped[int] = mapped_column(
        ForeignKey("tenant_users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("emic_roles.id", ondelete="CASCADE"), primary_key=True
    )


class TenantUserSiteAccessModel(Base):
    __tablename__ = "tenant_user_site_access"
    __table_args__ = (UniqueConstraint("tenant_user_id", "site_id", name="uq_tenant_user_site_access"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_user_id: Mapped[int] = mapped_column(
        ForeignKey("tenant_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)

    tenant_user: Mapped[TenantUserModel] = relationship(back_populates="site_access")
    site: Mapped["SiteModel"] = relationship()


class PlatformUserRoleModel(Base):
    __tablename__ = "platform_user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_name", name="uq_platform_user_roles"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("emic_users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_name: Mapped[str] = mapped_column(String(64), nullable=False)

    user: Mapped["EmicUserModel"] = relationship(back_populates="platform_roles")
