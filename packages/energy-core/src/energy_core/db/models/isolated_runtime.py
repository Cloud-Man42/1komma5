"""Isolated module runtime ORM models (Step 5C.5)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from energy_core.db.models.base import Base


class IsolatedRuntimeInstanceModel(Base):
    __tablename__ = "isolated_runtime_instances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    runtime_instance_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    module_id: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    publisher_id: Mapped[str] = mapped_column(String(128), nullable=False)
    artifact_sha256: Mapped[str] = mapped_column(String(128), nullable=False)
    site_id: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="BLOCKED")
    process_identity: Mapped[str | None] = mapped_column(String(128), nullable=True)
    process_pid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sandbox_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    socket_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    package_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    protocol_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    restart_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason_codes_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    permissions_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class RuntimeEventModel(Base):
    __tablename__ = "runtime_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    runtime_instance_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    module_id: Mapped[str] = mapped_column(String(128), nullable=False)
    site_id: Mapped[int] = mapped_column(Integer, nullable=False)
    detail_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RuntimeControlLeaseModel(Base):
    __tablename__ = "runtime_control_leases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    runtime_instance_id: Mapped[str] = mapped_column(String(64), nullable=False)
    module_id: Mapped[str] = mapped_column(String(128), nullable=False)
    site_id: Mapped[int] = mapped_column(Integer, nullable=False)
    device_id: Mapped[str] = mapped_column(String(128), nullable=False)
    capability: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
