"""Load installed packages into ModuleRegistry on startup."""

from __future__ import annotations

import importlib
import json
import logging
import sys
import zipfile
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from energy_core.config import Settings
from energy_core.db.installed_package_repo import InstalledPackageRepository
from energy_core.platform.capabilities.types import Capability
from energy_core.platform.modules.packages.builtin_adapter import BuiltInModuleAdapter
from energy_core.platform.modules.packages.canonical import canonical_manifest_bytes, manifest_sha256
from energy_core.platform.modules.packages.integrity import compute_package_content_sha256
from energy_core.platform.modules.packages.quarantine import quarantine_package
from energy_core.platform.modules.packages.signing import verify_signature_file
from energy_core.platform.modules.packages.trust_store import PublisherTrustStore
from energy_core.platform.modules.packages.types import PackageSource, PackageState
from energy_core.platform.modules.registry import ModuleDescriptor, default_module_registry
from energy_core.platform.modules.sdk.manifest import parse_manifest_dict
from energy_core.platform.modules.types import ModuleType

logger = logging.getLogger(__name__)

_VERIFY_EXCLUDED_SUFFIXES = {".pyc"}
_VERIFY_EXCLUDED_PREFIXES = ("__pycache__/", "integrity/signature.json")


def _include_in_verify_archive(relative_path: str) -> bool:
    if relative_path.startswith(_VERIFY_EXCLUDED_PREFIXES):
        return False
    if relative_path.endswith(tuple(_VERIFY_EXCLUDED_SUFFIXES)):
        return False
    if relative_path == ".verify-loader.zip":
        return False
    return True


def _capability_tuple(values: tuple[str, ...]) -> tuple[Capability, ...]:
    result: list[Capability] = []
    for value in values:
        try:
            result.append(Capability(value))
        except ValueError:
            logger.warning("package module capability unknown: %s", value)
    return tuple(result)


async def _verify_installed_package(
    record,
    trust_store: PublisherTrustStore,
    *,
    allow_unsigned: bool,
) -> tuple[dict, Path] | None:
    package_dir = Path(record.package_path)
    manifest_path = package_dir / "manifest.json"
    if not manifest_path.exists():
        return None
    manifest_raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    buffer_zip = package_dir.parent / ".verify-loader.zip"
    with zipfile.ZipFile(buffer_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(package_dir.rglob("*")):
            if path.is_file():
                rel = path.relative_to(package_dir).as_posix()
                if not _include_in_verify_archive(rel):
                    continue
                if rel == "manifest.json":
                    data = canonical_manifest_bytes(manifest_raw)
                else:
                    data = path.read_bytes()
                zf.writestr(rel, data)
    try:
        actual = compute_package_content_sha256(buffer_zip)
        if actual.lower() != record.checksum_sha256.lower():
            return None
        if manifest_raw.get("integrity", {}).get("manifest_sha256"):
            if manifest_sha256(manifest_raw).lower() != str(manifest_raw["integrity"]["manifest_sha256"]).lower():
                return None
        signature_path = package_dir / "integrity" / "signature.json"
        if signature_path.exists():
            payload = json.loads(signature_path.read_text(encoding="utf-8"))
            public_key = await trust_store.assert_trusted(str(payload["publisher"]), str(payload["key_id"]))
            verify_signature_file(
                package_dir=package_dir,
                manifest_raw=manifest_raw,
                archive_path=buffer_zip,
                public_key_pem=public_key,
            )
        elif not allow_unsigned:
            return None
        return manifest_raw, package_dir
    except Exception:
        return None
    finally:
        buffer_zip.unlink(missing_ok=True)


def _register_from_manifest(manifest_path: Path, package_dir: Path, *, skip_import: bool = False) -> ModuleDescriptor:
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = parse_manifest_dict(raw)

    module_root = package_dir / "module"
    if not skip_import and module_root.exists() and str(module_root) not in sys.path:
        sys.path.insert(0, str(module_root))

    descriptor = ModuleDescriptor(
        module_id=manifest.module_id,
        name=manifest.name,
        version=manifest.version,
        module_type=ModuleType(manifest.module_type),
        description=manifest.description,
        dependencies=tuple(d.module_id for d in manifest.module_dependencies),
        capabilities_provided=_capability_tuple(manifest.provided_capabilities),
        capabilities_required=_capability_tuple(manifest.required_capabilities),
        optional_capabilities=_capability_tuple(manifest.optional_capabilities),
        supports_per_site_activation=manifest.supports_per_site_activation,
        configuration_schema=manifest.configuration_schema,
        onboardable=manifest.onboardable,
        device_categories=manifest.device_categories,
        connection_types=manifest.connection_types,
        can_disable=manifest.can_disable,
        onboard_handler=manifest.onboard_handler,
        supports_discovery=manifest.supports_discovery,
        package_source=PackageSource.INSTALLED,
        installed_version=manifest.version,
        publisher=manifest.publisher,
        package_state="installed",
        removable=True,
        updatable=True,
        entrypoint=manifest.entrypoint,
    )
    default_module_registry.register_package_descriptor(descriptor)

    if not skip_import and manifest.entrypoint and ":" in manifest.entrypoint:
        module_name, attr = manifest.entrypoint.split(":", 1)
        imported = importlib.import_module(module_name)
        getattr(imported, attr)
    return descriptor


async def load_installed_module_packages(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    settings: Settings | None = None,
) -> None:
    BuiltInModuleAdapter.enrich_registry()
    resolved_settings = settings or Settings()
    async with session_factory() as session:
        repo = InstalledPackageRepository(session)
        trust_store = PublisherTrustStore(session)
        records = await repo.list_all()
        for record in records:
            if record.package_state == PackageState.QUARANTINED:
                logger.warning("skipping quarantined package %s", record.module_id)
                continue
            verified = await _verify_installed_package(
                record,
                trust_store,
                allow_unsigned=resolved_settings.emic_allow_unsigned_modules,
            )
            if verified is None:
                await quarantine_package(
                    session,
                    record,
                    reason="startup_integrity_failed",
                    last_error="integrity or signature verification failed",
                )
                continue
            manifest_raw, package_dir = verified
            try:
                from energy_core.platform.modules.governance.publisher_repository import PublisherRepository
                from energy_core.platform.modules.isolation.policy import requires_isolated_runtime

                publisher_row = await PublisherRepository(session).get(
                    manifest_raw.get("publisher", record.publisher)
                )
                publisher_tier = publisher_row.tier if publisher_row else None
                descriptor = _register_from_manifest(
                    package_dir / "manifest.json",
                    package_dir,
                    skip_import=True,
                )
                isolated = requires_isolated_runtime(descriptor, publisher_tier=publisher_tier)
                if isolated:
                    logger.info("registered isolated module metadata without in-process import: %s", record.module_id)
                elif descriptor.entrypoint and ":" in (descriptor.entrypoint or ""):
                    module_root = package_dir / "module"
                    if module_root.exists() and str(module_root) not in sys.path:
                        sys.path.insert(0, str(module_root))
                    module_name, attr = descriptor.entrypoint.split(":", 1)
                    imported = importlib.import_module(module_name)
                    getattr(imported, attr)
            except Exception as exc:
                logger.exception("failed loading package %s: %s", record.module_id, exc)
                await quarantine_package(session, record, reason="load_failed", last_error=str(exc))


def load_installed_module_packages_sync(settings) -> None:
    """Test helper: load packages using a fresh engine from settings."""
    import asyncio

    from energy_core.db.session import create_engine, create_session_factory

    async def _run() -> None:
        engine = create_engine(settings)
        session_factory = create_session_factory(engine)
        try:
            await load_installed_module_packages(session_factory, settings=settings)
        finally:
            await engine.dispose()

    asyncio.run(_run())
