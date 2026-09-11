"""Manifest and compatibility validation."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from packaging.version import InvalidVersion, Version

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import AppEnvironment, Settings
from energy_core.platform.capabilities.types import Capability
from energy_core.platform.modules.packages.archive_guard import inspect_archive_limits
from energy_core.platform.modules.packages.dependency_resolver import PackageDependencyResolver
from energy_core.platform.modules.packages.errors import (
    INCOMPATIBLE_EMIC_VERSION,
    INCOMPATIBLE_MODULE_API_VERSION,
    INVALID_CAPABILITY,
    INVALID_MANIFEST,
    MODULE_ALREADY_INSTALLED,
    MODULE_ID_PROTECTED,
    PACKAGE_TOO_LARGE,
    PackageError,
)
from energy_core.platform.modules.packages.integrity import PackageIntegrityVerifier, compute_package_content_sha256
from energy_core.platform.modules.packages.network_hosts import validate_network_hosts
from energy_core.platform.modules.packages.paths import is_protected_module_id
from energy_core.platform.modules.packages.permissions import (
    validate_capability_permissions,
    validate_permissions,
)
from energy_core.platform.modules.packages.trust_store import PublisherTrustStore
from energy_core.platform.modules.packages.types import ModuleManifest, SignatureStatus, ValidationResult
from energy_core.platform.modules.sdk.manifest import parse_manifest_dict
from energy_core.platform.modules.types import ModuleType


class PackageValidator:
    def __init__(
        self,
        settings: Settings,
        *,
        trust_store: PublisherTrustStore | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        self._settings = settings
        self._trust_store = trust_store
        self._session = session
        self._integrity = PackageIntegrityVerifier(
            allow_unsigned=settings.emic_allow_unsigned_modules,
            trust_store=trust_store,
        )
        self._deps = PackageDependencyResolver()

    async def validate_archive(
        self,
        archive_path: Path,
        *,
        installed_versions: dict[str, str] | None = None,
        allow_reinstall: bool = False,
    ) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        signed = False
        signature_valid = False
        publisher_trusted = False

        if not archive_path.exists():
            return ValidationResult(valid=False, errors=("archive not found",))

        size = archive_path.stat().st_size
        if size > self._settings.emic_module_package_max_bytes:
            return ValidationResult(valid=False, errors=(PACKAGE_TOO_LARGE,))

        try:
            inspect_archive_limits(archive_path)
        except PackageError as exc:
            return ValidationResult(valid=False, errors=(exc.code,))

        try:
            with zipfile.ZipFile(archive_path, "r") as zf:
                if "manifest.json" not in zf.namelist():
                    raise PackageError("manifest.json missing", code=INVALID_MANIFEST)
                manifest_raw = json.loads(zf.read("manifest.json").decode("utf-8"))
        except zipfile.BadZipFile:
            return ValidationResult(valid=False, errors=("invalid zip archive",))
        except json.JSONDecodeError:
            return ValidationResult(valid=False, errors=(INVALID_MANIFEST,))

        try:
            manifest = parse_manifest_dict(manifest_raw)
        except PackageError as exc:
            return ValidationResult(valid=False, errors=(exc.code,))

        if is_protected_module_id(manifest.module_id):
            return ValidationResult(valid=False, errors=(MODULE_ID_PROTECTED,))

        installed = installed_versions or {}
        if manifest.module_id in installed and not allow_reinstall:
            return ValidationResult(valid=False, errors=(MODULE_ALREADY_INSTALLED,))

        try:
            emic_version = Version(self._settings.emic_version)
            if Version(manifest.minimum_emic_version) > emic_version:
                errors.append(INCOMPATIBLE_EMIC_VERSION)
            if manifest.maximum_emic_version and Version(manifest.maximum_emic_version) < emic_version:
                errors.append(INCOMPATIBLE_EMIC_VERSION)
        except InvalidVersion:
            errors.append(INCOMPATIBLE_EMIC_VERSION)

        if manifest.module_api_version > self._settings.emic_module_api_version:
            errors.append(INCOMPATIBLE_MODULE_API_VERSION)

        try:
            validate_permissions(manifest.permissions)
            validate_capability_permissions(
                provided=manifest.provided_capabilities,
                permissions=manifest.permissions,
            )
            validate_network_hosts(manifest.network_hosts)
            for cap in manifest.provided_capabilities + manifest.required_capabilities + manifest.optional_capabilities:
                Capability(cap)
        except PackageError as exc:
            errors.append(exc.code)

        try:
            ModuleType(manifest.module_type)
        except ValueError:
            errors.append(INVALID_MANIFEST)

        try:
            self._integrity.verify_content_hashes(
                archive_path,
                manifest_raw,
                expected_content_sha256=manifest.integrity.archive_sha256,
                expected_manifest_sha256=manifest.integrity.manifest_sha256,
            )
        except PackageError as exc:
            errors.append(exc.code)

        try:
            self._deps.resolve(manifest.module_dependencies, installed_versions=installed)
        except PackageError as exc:
            errors.append(exc.code)

        graph = {manifest.module_id: tuple(d.module_id for d in manifest.module_dependencies)}
        try:
            self._deps.detect_cycles(graph)
        except PackageError as exc:
            errors.append(exc.code)

        signature_status = SignatureStatus.MISSING
        if not errors:
            import tempfile
            import shutil
            from energy_core.platform.modules.packages.extractor import PackageExtractor
            from energy_core.platform.modules.packages.paths import ModulePackagePaths

            paths = ModulePackagePaths(self._settings.resolved_modules_path())
            staging = paths.staging_dir(manifest.module_id, f"validate-{manifest.version}")
            try:
                PackageExtractor(paths).extract(archive_path, staging)
                signature_status = await self._integrity.verify_signature(
                    package_dir=staging,
                    manifest_raw=manifest_raw,
                    archive_path=archive_path,
                )
            except PackageError as exc:
                errors.append(exc.code)
            finally:
                shutil.rmtree(staging, ignore_errors=True)

        if signature_status in {SignatureStatus.UNSIGNED, SignatureStatus.MISSING}:
            signed = False
            signature_valid = False
            publisher_trusted = False
            if not self._settings.emic_allow_unsigned_modules:
                errors.append("SIGNATURE_INVALID")
        elif signature_status == SignatureStatus.INVALID:
            signed = True
            signature_valid = False
            publisher_trusted = False
            errors.append("SIGNATURE_INVALID")
        elif signature_status == SignatureStatus.VALID:
            signed = True
            signature_valid = True
            publisher_trusted = True

        install_allowed = not errors and (
            signature_valid or (self._settings.emic_allow_unsigned_modules and signature_status == SignatureStatus.UNSIGNED)
        )
        publisher_identity_valid = signature_valid and publisher_trusted

        policy_decision = None
        policy_reason_codes: tuple[str, ...] = ()
        policy_explanation = None
        publisher_tier = None
        control_capable = False
        policy_version = None
        if manifest is not None and self._session is not None and not errors:
            from energy_core.platform.modules.governance.evaluation_service import GovernanceEvaluationService
            from energy_core.platform.modules.governance.types import PolicyAction

            evaluation = await GovernanceEvaluationService(self._session).evaluate(
                action=PolicyAction.INSTALL,
                module_id=manifest.module_id,
                publisher_id=manifest.publisher,
                permissions=tuple(manifest.permissions),
                provided_capabilities=manifest.provided_capabilities,
                marketplace_enabled=self._settings.marketplace_metadata_enabled,
                app_env_production=self._settings.app_env == AppEnvironment.PRODUCTION,
            )
            policy_decision = evaluation.decision.value
            policy_reason_codes = evaluation.reason_codes
            policy_explanation = evaluation.explanation
            publisher_tier = evaluation.publisher_tier
            control_capable = evaluation.control_capable
            policy_version = evaluation.policy_version

        if errors:
            return ValidationResult(
                valid=False,
                errors=tuple(errors),
                warnings=warnings,
                signed=signed,
                signature_valid=signature_valid,
                publisher_trusted=publisher_trusted,
                publisher_identity_valid=publisher_identity_valid,
                install_allowed=False,
                policy_decision=policy_decision,
                policy_reason_codes=policy_reason_codes,
                policy_explanation=policy_explanation,
                publisher_tier=publisher_tier,
                control_capable=control_capable,
                policy_version=policy_version,
            )

        return ValidationResult(
            valid=True,
            manifest=manifest,
            warnings=warnings,
            signed=signed,
            signature_valid=signature_valid,
            publisher_trusted=publisher_trusted,
            publisher_identity_valid=publisher_identity_valid,
            install_allowed=install_allowed,
            policy_decision=policy_decision,
            policy_reason_codes=policy_reason_codes,
            policy_explanation=policy_explanation,
            publisher_tier=publisher_tier,
            control_capable=control_capable,
            policy_version=policy_version,
        )

    @staticmethod
    def compute_archive_checksum(archive_path: Path) -> str:
        return compute_package_content_sha256(archive_path)
