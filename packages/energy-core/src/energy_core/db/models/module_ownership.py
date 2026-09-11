"""Canonical module ownership."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from energy_core.db.models.base import Base


class ModuleOwnershipModel(Base):
    __tablename__ = "module_ownership"

    module_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    publisher_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    protected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
