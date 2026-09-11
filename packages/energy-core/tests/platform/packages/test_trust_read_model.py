"""Trust read model tests."""

from __future__ import annotations

from energy_core.platform.modules.packages.trust_read_model import build_install_metadata, trust_view_from_record
from energy_core.platform.modules.packages.types import InstalledPackageRecord, PackageState, SignatureStatus, ValidationResult


def test_trust_view_from_unsigned_metadata() -> None:
    record = InstalledPackageRecord(
        module_id="integration.demo",
        installed_version="1.0.0",
        package_state=PackageState.INSTALLED,
        package_path="/tmp/pkg",
        publisher="emic-tests",
        source="upload",
        checksum_sha256="abc",
        signature_status=SignatureStatus.UNSIGNED,
        rollback_version=None,
        previous_package_path=None,
        module_api_version=1,
        restart_required=True,
        metadata={
            "signed": False,
            "signature_valid": False,
            "publisher_trusted": False,
            "publisher_status": "unsigned",
        },
    )
    trust = trust_view_from_record(record)
    assert trust["signed"] is False
    assert trust["publisher_trusted"] is False
    assert trust["publisher_status"] == "unsigned"


def test_build_install_metadata_from_validation() -> None:
    from energy_core.platform.modules.packages.types import ModuleManifest, PackageIntegritySpec

    manifest = ModuleManifest(
        module_id="integration.demo",
        name="Demo",
        version="1.0.0",
        module_type="integration",
        description="demo",
        publisher="emic-tests",
        entrypoint="demo:build_module",
        module_api_version=1,
        minimum_emic_version="0.1.0",
        provided_capabilities=("read_status",),
        required_capabilities=(),
        optional_capabilities=(),
        module_dependencies=(),
        configuration_schema={"fields": []},
        permissions=("device.read",),
        supports_per_site_activation=True,
        requires_restart_on_update=True,
        integrity=PackageIntegritySpec(archive_sha256="00" * 32),
    )
    validation = ValidationResult(
        valid=True,
        manifest=manifest,
        signed=True,
        signature_valid=True,
        publisher_trusted=True,
        install_allowed=True,
    )
    meta = build_install_metadata(manifest, validation)
    assert meta["publisher_trusted"] is True
    assert meta["permissions"] == ["device.read"]
