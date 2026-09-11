"""Per-site module activation overlay."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from energy_core.db.models.base import Base


class SiteModuleConfigurationModel(Base):
    __tablename__ = "site_module_configurations"
    __table_args__ = (UniqueConstraint("site_id", "module_id", name="uq_site_module"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    module_id: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled_override: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
