"""Installed module package ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from energy_core.db.models.base import Base


class InstalledModulePackageModel(Base):
    __tablename__ = "installed_module_packages"

    module_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    installed_version: Mapped[str] = mapped_column(String(64), nullable=False)
    package_state: Mapped[str] = mapped_column(String(32), nullable=False, default="installed")
    package_path: Mapped[str] = mapped_column(Text, nullable=False)
    staging_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    publisher: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="upload")
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    signature_status: Mapped[str] = mapped_column(String(16), nullable=False, default="unsigned")
    rollback_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    previous_package_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    module_api_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    restart_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
