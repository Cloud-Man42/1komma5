"""Remote artifact staging orchestration (Step 5C.3 + 5C.4)."""

from __future__ import annotations

import json
import logging
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from energy_core.config import AppEnvironment, Settings
from energy_core.platform.modules.distribution.artifact_repository import ArtifactRepository
from energy_core.platform.modules.distribution.catalog_resolver import CatalogReleaseResolver
from energy_core.platform.modules.distribution.downloader import SecureArtifactDownloader
from energy_core.platform.modules.distribution.types import (
    ArtifactProvenance,
    ArtifactState,
    DistributionError,
    DistributionErrorCode,
    StagingResult,
)
from energy_core.platform.modules.governance.evaluation_service import GovernanceEvaluationService
from energy_core.platform.modules.governance.types import PolicyAction, PolicyDecision
from energy_core.platform.modules.governance.policy_repository import PolicyRepository
from energy_core.platform.modules.marketplace.trust_cache import MarketplaceTrustCacheRepository
from energy_core.platform.modules.packages.trust_store import PublisherTrustStore
from energy_core.platform.modules.packages.validator import PackageValidator
from energy_core.platform.modules.supply_chain.advisory_policy import parse_advisory_bundle
from energy_core.platform.modules.supply_chain.release_security_evaluator import (
    ReleaseSecurityEvaluator,
    SupplyChainPolicy,
)
from energy_core.platform.modules.supply_chain.sbom_parser import parse_sbom, sbom_digest
from energy_core.platform.modules.supply_chain.types import AdvisoryStatus, SbomStatus
from energy_core.platform.modules.supply_chain.vulnerability_matcher import match_vulnerabilities
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ArtifactStagingService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._artifacts = ArtifactRepository(session)
        self._trust_cache = MarketplaceTrustCacheRepository(session)
        self._downloader = SecureArtifactDownloader(settings)
        self._security = ReleaseSecurityEvaluator()

    async def fetch_release(self, module_id: str, version: str) -> StagingResult:
        cache_row = await self._trust_cache.get_or_create()
        if not cache_row.catalog_json:
            raise DistributionError("Trusted catalog unavailable", code=DistributionErrorCode.CATALOG_ENTRY_NOT_FOUND)

        resolver = CatalogReleaseResolver.from_cache_json(cache_row.catalog_json)
        descriptor = resolver.resolve(module_id, version)

        row = await self._artifacts.get_or_create(
            module_id=descriptor.module_id,
            publisher_id=descriptor.publisher_id,
            version=descriptor.version,
            release_id=descriptor.release_id,
            content_sha256=descriptor.content_sha256,
            source_type=descriptor.source.value,
            artifact_size=descriptor.artifact_size,
            catalog_version=descriptor.catalog_version,
        )
        reason_codes: list[str] = []

        try:
            await self._artifacts.set_state(row, ArtifactState.DOWNLOAD_PENDING)
            await self._session.commit()

            await self._artifacts.set_state(row, ArtifactState.DOWNLOADING)
            download = await self._downloader.download(descriptor)
            await self._artifacts.set_state(row, ArtifactState.DOWNLOADED, cache_path=download.path)
            await self._session.commit()

            await self._artifacts.set_state(row, ArtifactState.VERIFYING)
            archive_path = Path(download.path)
            trust_store = PublisherTrustStore(self._session)
            validator = PackageValidator(self._settings, trust_store=trust_store, session=self._session)
            validation = await validator.validate_archive(archive_path, allow_reinstall=True)

            if validation.manifest is None:
                reason_codes.append(DistributionErrorCode.PACKAGE_SIGNATURE_INVALID.value)
                permissions: tuple[str, ...] = ()
                provided_capabilities: tuple[str, ...] = ()
            else:
                manifest = validation.manifest
                if descriptor.module_id != manifest.module_id:
                    reason_codes.append(DistributionErrorCode.PACKAGE_IDENTITY_MISMATCH.value)
                if descriptor.version != manifest.version:
                    reason_codes.append(DistributionErrorCode.PACKAGE_IDENTITY_MISMATCH.value)
                if descriptor.publisher_id != manifest.publisher:
                    reason_codes.append(DistributionErrorCode.PACKAGE_IDENTITY_MISMATCH.value)
                permissions = tuple(manifest.permissions)
                provided_capabilities = tuple(manifest.provided_capabilities)

            archive_integrity_ok = validation.valid
            if validation.errors:
                reason_codes.extend(validation.errors)

            ownership = await GovernanceEvaluationService(self._session).evaluate(
                action=PolicyAction.INSTALL,
                module_id=descriptor.module_id,
                publisher_id=descriptor.publisher_id,
                permissions=permissions,
                provided_capabilities=provided_capabilities,
                marketplace_enabled=self._settings.marketplace_metadata_enabled,
                app_env_production=self._settings.app_env == AppEnvironment.PRODUCTION,
            )
            if ownership.reason_codes:
                reason_codes.extend(ownership.reason_codes)
            if ownership.decision == PolicyDecision.DENY:
                reason_codes.append(DistributionErrorCode.POLICY_DENIED.value)

            if not validation.signature_valid and not (
                self._settings.emic_allow_unsigned_modules and archive_integrity_ok
            ):
                reason_codes.append(DistributionErrorCode.PACKAGE_SIGNATURE_INVALID.value)

            sbom_status = SbomStatus.MISSING
            parsed_sbom = None
            sbom_raw: bytes | None = None
            if descriptor.sbom_reference and descriptor.sbom_reference.embedded:
                sbom_raw = self._read_embedded_sbom(archive_path)
            elif descriptor.sbom_reference and descriptor.sbom_reference.url:
                sbom_desc = descriptor.sbom_reference
                if sbom_desc.sha256:
                    sbom_path = self._downloader.staging_path_for(f"sbom-{sbom_desc.sha256}")
                    if not sbom_path.is_file():
                        from energy_core.platform.modules.distribution.types import ArtifactDescriptor as AD
                        from energy_core.platform.modules.distribution.types import ArtifactSourceType, SbomReference

                        sbom_descriptor = AD(
                            module_id=descriptor.module_id,
                            publisher_id=descriptor.publisher_id,
                            version=descriptor.version,
                            release_id=f"{descriptor.release_id}:sbom",
                            artifact_url=sbom_desc.url,
                            content_sha256=sbom_desc.sha256,
                            artifact_size=None,
                            source=descriptor.source,
                            sbom_reference=SbomReference(embedded=True),
                        )
                        sbom_dl = await self._downloader.download(sbom_descriptor)
                        sbom_path = Path(sbom_dl.path)
                    sbom_raw = sbom_path.read_bytes()
            if sbom_raw:
                try:
                    expected = descriptor.sbom_reference.sha256 if descriptor.sbom_reference else None
                    parsed_sbom = parse_sbom(sbom_raw, expected_digest=expected)
                    sbom_status = SbomStatus.VALID
                    await self._artifacts.save_sbom(
                        artifact_id=row.id,
                        module_id=descriptor.module_id,
                        version=descriptor.version,
                        artifact_digest=descriptor.content_sha256,
                        sbom_digest=parsed_sbom.raw_digest,
                        fmt=parsed_sbom.format,
                        spec_version=parsed_sbom.spec_version,
                        raw_json=sbom_raw.decode("utf-8"),
                        components=[
                            (c.name, c.version, c.purl, c.cpe, c.supplier, json.dumps(list(c.licenses)))
                            for c in parsed_sbom.components
                        ],
                    )
                except Exception:
                    sbom_status = SbomStatus.INVALID
                    reason_codes.append("SBOM_INVALID")

            advisory_status = AdvisoryStatus.UNAVAILABLE
            advisories = ()
            if cache_row.advisories_json:
                try:
                    bundle = parse_advisory_bundle(json.loads(cache_row.advisories_json))
                    advisories = bundle.advisories
                    advisory_status = AdvisoryStatus.TRUSTED
                except Exception:
                    advisory_status = AdvisoryStatus.UNTRUSTED
                    reason_codes.append("ADVISORY_DATA_UNTRUSTED")

            vulnerabilities = ()
            if parsed_sbom and advisories:
                vulnerabilities = match_vulnerabilities(parsed_sbom.components, advisories)

            policy_row = await PolicyRepository(self._session).get_or_create()
            sc_policy = SupplyChainPolicy.from_json(
                json.loads(getattr(policy_row, "supply_chain_policy_json", None) or "{}")
            )
            security = self._security.evaluate(
                sbom_status=sbom_status,
                advisory_status=advisory_status,
                vulnerabilities=vulnerabilities,
                supply_chain_policy=sc_policy,
                governance_decision=ownership.decision,
                integrity_verified=archive_integrity_ok,
            )
            if security.reason_codes:
                reason_codes.extend(security.reason_codes)

            provenance = ArtifactProvenance(
                publisher_id=descriptor.publisher_id,
                module_id=descriptor.module_id,
                version=descriptor.version,
                release_id=descriptor.release_id,
                artifact_digest=descriptor.content_sha256,
                source=descriptor.source.value,
                catalog_metadata_version=descriptor.catalog_version,
                download_timestamp=datetime.now(UTC),
                signature_key_id=None,
                sbom_digest=parsed_sbom.raw_digest if parsed_sbom else None,
                security_evaluation_timestamp=datetime.now(UTC),
            )

            await self._artifacts.upsert_security(
                row.id,
                integrity_verified=security.integrity_verified,
                sbom_status=security.sbom_status.value,
                advisory_status=security.advisory_status.value,
                highest_severity=security.highest_severity.value,
                vulnerability_count=security.vulnerability_count,
                critical_count=security.critical_count,
                high_count=security.high_count,
                security_review_required=security.security_review_required,
                policy_decision=security.policy_decision,
                reason_codes=tuple(dict.fromkeys(reason_codes)),
                snapshot_json=json.dumps(
                    {
                        "vulnerabilities": [
                            {
                                "advisory_id": v.advisory_id,
                                "component": v.component_name,
                                "severity": v.severity.value,
                            }
                            for v in security.vulnerabilities
                        ]
                    }
                ),
            )
            await self._artifacts.replace_vulnerabilities(
                row.id,
                [
                    (v.advisory_id, v.component_name, v.component_version, v.purl, v.severity.value, v.matched, v.version_status)
                    for v in security.vulnerabilities
                ],
            )

            blocks = (
                self._security.blocks_staging(security, sc_policy)
                or ownership.decision == PolicyDecision.DENY
                or bool(
                    [
                        c
                        for c in reason_codes
                        if c
                        in {
                            DistributionErrorCode.PACKAGE_IDENTITY_MISMATCH.value,
                            DistributionErrorCode.PACKAGE_SIGNATURE_INVALID.value,
                            DistributionErrorCode.ARTIFACT_DIGEST_MISMATCH.value,
                        }
                    ]
                )
            )

            final_state = ArtifactState.QUARANTINED if blocks else ArtifactState.STAGED

            quarantine_dir = Path(self._settings.resolved_marketplace_staging_path()) / "quarantine"
            quarantine_dir.mkdir(parents=True, exist_ok=True)
            quarantine_path = None
            if final_state == ArtifactState.QUARANTINED:
                dest = quarantine_dir / f"{descriptor.content_sha256}.emicpkg"
                shutil.copy2(archive_path, dest)
                quarantine_path = str(dest)

            await self._artifacts.set_state(
                row,
                final_state,
                cache_path=download.path,
                quarantine_path=quarantine_path,
                reason_codes=tuple(dict.fromkeys(reason_codes)),
                provenance=provenance,
            )
            await self._session.commit()

            return StagingResult(
                artifact_id=row.id,
                state=final_state,
                reason_codes=tuple(dict.fromkeys(reason_codes)),
                security_status=security.highest_severity.value,
                policy_decision=security.policy_decision,
                message=f"Artifact {final_state.value.lower()}",
            )
        except DistributionError as exc:
            await self._artifacts.set_state(
                row,
                ArtifactState.REJECTED,
                reason_codes=(exc.code.value,),
            )
            await self._session.commit()
            raise
        except Exception as exc:
            logger.exception("Artifact staging failed")
            await self._artifacts.set_state(row, ArtifactState.REJECTED, reason_codes=("STAGING_FAILED",))
            await self._session.commit()
            raise DistributionError(str(exc), code=DistributionErrorCode.ARTIFACT_NOT_FOUND) from exc

    @staticmethod
    def _read_embedded_sbom(archive_path: Path) -> bytes | None:
        with zipfile.ZipFile(archive_path, "r") as zf:
            for name in ("sbom.json", "cyclonedx.json", "bom.json"):
                if name in zf.namelist():
                    return zf.read(name)
        return None
