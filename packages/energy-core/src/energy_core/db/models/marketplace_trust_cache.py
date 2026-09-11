"""Marketplace trust cache ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from energy_core.db.models.base import Base


class MarketplaceTrustCacheModel(Base):
    __tablename__ = "marketplace_trust_cache"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cache_key: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, default="default")
    enabled: Mapped[bool] = mapped_column(nullable=False, default=False)
    cache_state: Mapped[str] = mapped_column(String(32), nullable=False, default="uninitialized")
    revocation_state: Mapped[str] = mapped_column(String(32), nullable=False, default="unavailable")
    cache_generation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    root_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timestamp_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snapshot_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    targets_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    catalog_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    revocations_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    advisories_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    advisories_generation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    advisories_content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    advisories_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_generation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revocation_content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    catalog_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sync_failed: Mapped[bool] = mapped_column(nullable=False, default=False)
    pinned_root_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = ({"sqlite_autoincrement": True},)
