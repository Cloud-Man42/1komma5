"""Marketplace artifact ORM models (Step 5C.3 / 5C.4)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from energy_core.db.models.base import Base


class MarketplaceArtifactModel(Base):
    __tablename__ = "marketplace_artifacts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    module_id: Mapped[str] = mapped_column(String(128), nullable=False)
    publisher_id: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    release_id: Mapped[str] = mapped_column(String(256), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    artifact_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="PUBLIC")
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="DISCOVERED")
    cache_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    quarantine_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    provenance_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason_codes_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    catalog_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("module_id", "version", "content_sha256", name="uq_marketplace_artifact_release_digest"),
        Index("ix_marketplace_artifacts_module_version", "module_id", "version"),
        Index("ix_marketplace_artifacts_state", "state"),
    )


class MarketplaceArtifactSecurityModel(Base):
    __tablename__ = "marketplace_artifact_security"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    artifact_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    integrity_verified: Mapped[bool] = mapped_column(nullable=False, default=False)
    integrity_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sbom_status: Mapped[str] = mapped_column(String(32), nullable=False, default="MISSING")
    advisory_status: Mapped[str] = mapped_column(String(32), nullable=False, default="UNAVAILABLE")
    highest_severity: Mapped[str] = mapped_column(String(32), nullable=False, default="UNKNOWN")
    vulnerability_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    critical_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    high_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    security_review_required: Mapped[bool] = mapped_column(nullable=False, default=False)
    policy_decision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason_codes_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snapshot_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class MarketplaceSbomModel(Base):
    __tablename__ = "marketplace_sboms"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    artifact_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    module_id: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    sbom_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    format: Mapped[str] = mapped_column(String(32), nullable=False, default="CycloneDX")
    spec_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (Index("ix_marketplace_sboms_digest", "sbom_digest"),)


class MarketplaceSbomComponentModel(Base):
    __tablename__ = "marketplace_sbom_components"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sbom_id: Mapped[int] = mapped_column(Integer, nullable=False)
    component_name: Mapped[str] = mapped_column(String(256), nullable=False)
    component_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    purl: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cpe: Mapped[str | None] = mapped_column(String(512), nullable=True)
    supplier: Mapped[str | None] = mapped_column(String(256), nullable=True)
    licenses_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_marketplace_sbom_components_purl", "purl"),)


class MarketplaceAdvisoryModel(Base):
    __tablename__ = "marketplace_advisories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    advisory_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="emic")
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    published_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    withdrawn: Mapped[bool] = mapped_column(nullable=False, default=False)
    references_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (Index("ix_marketplace_advisories_severity", "severity"),)


class MarketplaceAdvisoryAffectedModel(Base):
    __tablename__ = "marketplace_advisory_affected"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    advisory_id: Mapped[str] = mapped_column(String(128), nullable=False)
    affected_purl: Mapped[str | None] = mapped_column(String(512), nullable=True)
    affected_package: Mapped[str | None] = mapped_column(String(256), nullable=True)
    version_range: Mapped[str | None] = mapped_column(String(256), nullable=True)
    fixed_versions_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_marketplace_advisory_affected_purl", "affected_purl"),)


class MarketplaceReleaseVulnerabilityModel(Base):
    __tablename__ = "marketplace_release_vulnerabilities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    artifact_id: Mapped[int] = mapped_column(Integer, nullable=False)
    advisory_id: Mapped[str] = mapped_column(String(128), nullable=False)
    component_name: Mapped[str] = mapped_column(String(256), nullable=False)
    component_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    purl: Mapped[str | None] = mapped_column(String(512), nullable=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    matched: Mapped[bool] = mapped_column(nullable=False, default=False)
    version_status: Mapped[str] = mapped_column(String(32), nullable=False, default="UNKNOWN")

    __table_args__ = (
        Index("ix_marketplace_release_vuln_artifact", "artifact_id"),
        Index("ix_marketplace_release_vuln_advisory", "advisory_id"),
    )
