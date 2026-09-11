"""Module ownership transfer workflow."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from energy_core.db.models.base import Base


class ModuleOwnershipTransferModel(Base):
    __tablename__ = "module_ownership_transfers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    module_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    from_publisher_id: Mapped[str] = mapped_column(String(128), nullable=False)
    to_publisher_id: Mapped[str] = mapped_column(String(128), nullable=False)
    from_tier: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_tier: Mapped[str | None] = mapped_column(String(32), nullable=True)
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
