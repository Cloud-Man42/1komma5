"""Artifact persistence repository."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models.marketplace_distribution import (
    MarketplaceArtifactModel,
    MarketplaceArtifactSecurityModel,
    MarketplaceReleaseVulnerabilityModel,
    MarketplaceSbomComponentModel,
    MarketplaceSbomModel,
)
from energy_core.platform.modules.distribution.types import ArtifactProvenance, ArtifactState


class ArtifactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, artifact_id: int) -> MarketplaceArtifactModel | None:
        return await self._session.get(MarketplaceArtifactModel, artifact_id)

    async def get_by_digest(self, digest: str) -> MarketplaceArtifactModel | None:
        return await self._session.scalar(
            select(MarketplaceArtifactModel).where(MarketplaceArtifactModel.content_sha256 == digest)
        )

    async def get_or_create(
        self,
        *,
        module_id: str,
        publisher_id: str,
        version: str,
        release_id: str,
        content_sha256: str,
        source_type: str,
        artifact_size: int | None,
        catalog_version: int | None,
    ) -> MarketplaceArtifactModel:
        row = await self.get_by_digest(content_sha256)
        if row is not None:
            return row
        row = MarketplaceArtifactModel(
            module_id=module_id,
            publisher_id=publisher_id,
            version=version,
            release_id=release_id,
            content_sha256=content_sha256,
            source_type=source_type,
            artifact_size=artifact_size,
            catalog_version=catalog_version,
            state=ArtifactState.DISCOVERED.value,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def set_state(
        self,
        row: MarketplaceArtifactModel,
        state: ArtifactState,
        *,
        cache_path: str | None = None,
        quarantine_path: str | None = None,
        reason_codes: tuple[str, ...] = (),
        provenance: ArtifactProvenance | None = None,
    ) -> MarketplaceArtifactModel:
        row.state = state.value
        if cache_path is not None:
            row.cache_path = cache_path
        if quarantine_path is not None:
            row.quarantine_path = quarantine_path
        if reason_codes:
            row.reason_codes_json = json.dumps(list(reason_codes))
        if provenance is not None:
            row.provenance_json = json.dumps(
                {
                    "publisher_id": provenance.publisher_id,
                    "module_id": provenance.module_id,
                    "version": provenance.version,
                    "release_id": provenance.release_id,
                    "artifact_digest": provenance.artifact_digest,
                    "source": provenance.source,
                    "catalog_metadata_version": provenance.catalog_metadata_version,
                    "download_timestamp": provenance.download_timestamp.isoformat() if provenance.download_timestamp else None,
                    "signature_key_id": provenance.signature_key_id,
                    "sbom_digest": provenance.sbom_digest,
                    "security_evaluation_timestamp": (
                        provenance.security_evaluation_timestamp.isoformat()
                        if provenance.security_evaluation_timestamp
                        else None
                    ),
                    "extra": provenance.extra,
                },
                sort_keys=True,
            )
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        return row

    async def upsert_security(
        self,
        artifact_id: int,
        *,
        integrity_verified: bool,
        sbom_status: str,
        advisory_status: str,
        highest_severity: str,
        vulnerability_count: int,
        critical_count: int,
        high_count: int,
        security_review_required: bool,
        policy_decision: str | None,
        reason_codes: tuple[str, ...],
        snapshot_json: str,
    ) -> MarketplaceArtifactSecurityModel:
        row = await self._session.scalar(
            select(MarketplaceArtifactSecurityModel).where(MarketplaceArtifactSecurityModel.artifact_id == artifact_id)
        )
        now = datetime.now(UTC)
        if row is None:
            row = MarketplaceArtifactSecurityModel(artifact_id=artifact_id)
            self._session.add(row)
        row.integrity_verified = integrity_verified
        row.integrity_verified_at = now if integrity_verified else row.integrity_verified_at
        row.sbom_status = sbom_status
        row.advisory_status = advisory_status
        row.highest_severity = highest_severity
        row.vulnerability_count = vulnerability_count
        row.critical_count = critical_count
        row.high_count = high_count
        row.security_review_required = security_review_required
        row.policy_decision = policy_decision
        row.reason_codes_json = json.dumps(list(reason_codes))
        row.snapshot_json = snapshot_json
        row.risk_evaluated_at = now
        await self._session.flush()
        return row

    async def replace_vulnerabilities(
        self,
        artifact_id: int,
        matches: list[tuple[str, str, str | None, str | None, str, bool, str]],
    ) -> None:
        existing = await self._session.scalars(
            select(MarketplaceReleaseVulnerabilityModel).where(
                MarketplaceReleaseVulnerabilityModel.artifact_id == artifact_id
            )
        )
        for item in existing:
            await self._session.delete(item)
        for advisory_id, comp_name, comp_ver, purl, severity, matched, version_status in matches:
            self._session.add(
                MarketplaceReleaseVulnerabilityModel(
                    artifact_id=artifact_id,
                    advisory_id=advisory_id,
                    component_name=comp_name,
                    component_version=comp_ver,
                    purl=purl,
                    severity=severity,
                    matched=matched,
                    version_status=version_status,
                )
            )
        await self._session.flush()

    async def list_quarantined(self) -> list[MarketplaceArtifactModel]:
        return list(
            await self._session.scalars(
                select(MarketplaceArtifactModel).where(
                    MarketplaceArtifactModel.state == ArtifactState.QUARANTINED.value
                )
            )
        )

    async def list_staged(self) -> list[MarketplaceArtifactModel]:
        return list(
            await self._session.scalars(
                select(MarketplaceArtifactModel).where(MarketplaceArtifactModel.state == ArtifactState.STAGED.value)
            )
        )

    async def save_sbom(
        self,
        *,
        artifact_id: int,
        module_id: str,
        version: str,
        artifact_digest: str,
        sbom_digest: str,
        fmt: str,
        spec_version: str,
        raw_json: str,
        components: list[tuple[str, str | None, str | None, str | None, str | None, str | None]],
    ) -> MarketplaceSbomModel:
        existing = await self._session.scalar(
            select(MarketplaceSbomModel).where(MarketplaceSbomModel.artifact_id == artifact_id)
        )
        if existing:
            old_id = existing.id
            comps = await self._session.scalars(
                select(MarketplaceSbomComponentModel).where(MarketplaceSbomComponentModel.sbom_id == old_id)
            )
            for c in comps:
                await self._session.delete(c)
            await self._session.delete(existing)
            await self._session.flush()
        row = MarketplaceSbomModel(
            artifact_id=artifact_id,
            module_id=module_id,
            version=version,
            artifact_digest=artifact_digest,
            sbom_digest=sbom_digest,
            format=fmt,
            spec_version=spec_version,
            raw_json=raw_json,
        )
        self._session.add(row)
        await self._session.flush()
        for name, ver, purl, cpe, supplier, licenses_json in components:
            self._session.add(
                MarketplaceSbomComponentModel(
                    sbom_id=row.id,
                    component_name=name,
                    component_version=ver,
                    purl=purl,
                    cpe=cpe,
                    supplier=supplier,
                    licenses_json=licenses_json,
                )
            )
        await self._session.flush()
        return row
