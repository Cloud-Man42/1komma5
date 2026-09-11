"""Installation-scoped organization policy."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from energy_core.db.models.base import Base


class ModuleInstallationPolicyModel(Base):
    __tablename__ = "module_installation_policy"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_scope: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, default="installation")
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    allowed_tiers_json: Mapped[str] = mapped_column(Text, nullable=False)
    publisher_allowlist_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    publisher_denylist_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    module_allowlist_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    module_denylist_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    blocked_permissions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    control_module_policy: Mapped[str] = mapped_column(String(32), nullable=False, default="VERIFIED_OK")
    break_glass_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    supply_chain_policy_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ModulePolicyHistoryModel(Base):
    __tablename__ = "module_policy_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_scope: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
