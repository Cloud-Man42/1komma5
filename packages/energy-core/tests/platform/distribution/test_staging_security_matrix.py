"""Remote staging security integration matrix (Sprint B.5)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
import socket
import threading
import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from energy_core.config import Settings
from energy_core.db.models.module_ownership import ModuleOwnershipModel
from energy_core.db.models.module_publisher_key import ModulePublisherKeyModel
from energy_core.platform.modules.distribution.staging_service import ArtifactStagingService
from energy_core.platform.modules.distribution.types import (
    ArtifactState,
    DistributionError,
    DistributionErrorCode,
)
from energy_core.platform.modules.governance.break_glass import get_break_glass_store
from energy_core.platform.modules.governance.types import PolicyDecision, PublisherTier
from energy_core.platform.modules.packages.integrity import compute_package_content_sha256
from energy_core.platform.modules.packages.signing import generate_ed25519_keypair
from energy_core.platform.modules.packages.trust_store import PublisherKeyRecord, PublisherKeyStatus, PublisherTrustStore

import importlib.util
from pathlib import Path

_helpers_path = Path(__file__).resolve().parent / "distribution_helpers.py"
_spec = importlib.util.spec_from_file_location("distribution_helpers", _helpers_path)
_helpers = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_helpers)
build_emicpkg = _helpers.build_emicpkg
critical_advisories_bundle = _helpers.critical_advisories_bundle
cyclonedx_sbom = _helpers.cyclonedx_sbom
high_advisories_bundle = _helpers.high_advisories_bundle
seed_trusted_catalog = _helpers.seed_trusted_catalog

pytestmark = pytest.mark.integration


def _catalog_digest(path: Path) -> str:
    return compute_package_content_sha256(path)


def _serve_dir(directory: Path):
    host = "127.0.0.1"
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, 0))
    port = sock.getsockname()[1]
    sock.close()
    serve_root = str(directory)

    class _DirHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=serve_root, **kwargs)

    server = ThreadingHTTPServer((host, port), _DirHandler)
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
    return f"http://{host}:{port}", server


@pytest.fixture
async def prod_distribution_session(tmp_path):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from energy_core.db.models import Base

    db_file = tmp_path / "distribution.db"
    staging = tmp_path / "staging"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        EMIC_ALLOW_UNSIGNED_MODULES=False,
        MARKETPLACE_METADATA_ENABLED=True,
        MARKETPLACE_STAGING_PATH=str(staging),
    )
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session, settings, session_factory, tmp_path
    await engine.dispose()


async def _stage_custom_package(session, settings, tmp_path, *, manifest_overrides=None, extra_files=None, **seed_kw):
    private_key, public_key = generate_ed25519_keypair()
    pkg_dir = tmp_path / "artifacts"
    pkg_dir.mkdir(parents=True)
    pkg_path = pkg_dir / "test.emicpkg"
    _build_digest, size = build_emicpkg(
        pkg_path,
        manifest_overrides=manifest_overrides,
        extra_files=extra_files,
        private_key=private_key,
    )
    digest = _catalog_digest(pkg_path)
    pub_id = (manifest_overrides or {}).get("publisher", "emic-tests")
    session.add(
        ModulePublisherKeyModel(
            publisher_id=pub_id,
            key_id="test-1",
            public_key_hex=public_key.hex(),
            status=PublisherKeyStatus.TRUSTED.value,
        )
    )
    base, server = _serve_dir(pkg_dir)
    await seed_trusted_catalog(
        session,
        artifact_base=base,
        artifact_name="test.emicpkg",
        content_sha256=digest,
        artifact_size=size,
        **seed_kw,
    )
    await session.commit()
    return ArtifactStagingService(session, settings), server


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "override",
    [
        {"module_id": "other.module"},
        {"version": "9.9.9"},
        {"publisher": "wrong-publisher"},
    ],
)
async def test_identity_mismatch_quarantined(prod_distribution_session, override):
    session, settings, _, tmp_path = prod_distribution_session
    service, server = await _stage_custom_package(session, settings, tmp_path, manifest_overrides=override)
    try:
        result = await service.fetch_release("integration.demo", "1.0.0")
        assert result.state == ArtifactState.QUARANTINED
        assert DistributionErrorCode.PACKAGE_IDENTITY_MISMATCH.value in result.reason_codes
    finally:
        server.shutdown()


@pytest.mark.asyncio
async def test_ownership_mismatch_quarantined(prod_distribution_session, tmp_path):
    session, settings, _, tmp_path = prod_distribution_session
    service, server = await _stage_custom_package(session, settings, tmp_path)
    session.add(ModuleOwnershipModel(module_id="integration.demo", publisher_id="other-owner"))
    await session.commit()
    try:
        result = await service.fetch_release("integration.demo", "1.0.0")
        assert result.state == ArtifactState.QUARANTINED
        assert any("OWNERSHIP" in c for c in result.reason_codes)
    finally:
        server.shutdown()


@pytest.mark.asyncio
async def test_community_remote_fetch_denied(prod_distribution_session, tmp_path):
    session, settings, _, tmp_path = prod_distribution_session
    service, server = await _stage_custom_package(
        session,
        settings,
        tmp_path,
        publisher_id="community-pub",
        publisher_tier=PublisherTier.COMMUNITY.value,
        manifest_overrides={"publisher": "community-pub"},
    )
    try:
        result = await service.fetch_release("integration.demo", "1.0.0")
        assert result.state == ArtifactState.QUARANTINED
        assert result.state != ArtifactState.STAGED
        assert any("COMMUNITY" in c or "POLICY_DENIED" in c for c in result.reason_codes)
    finally:
        server.shutdown()


@pytest.mark.asyncio
async def test_revoked_key_remote_fetch_rejected(prod_distribution_session, tmp_path):
    session, settings, _, tmp_path = prod_distribution_session
    private_key, public_key = generate_ed25519_keypair()
    pkg_dir = tmp_path / "artifacts"
    pkg_dir.mkdir(parents=True)
    pkg_path = pkg_dir / "test.emicpkg"
    _build_digest, size = build_emicpkg(pkg_path, private_key=private_key)
    digest = _catalog_digest(pkg_path)
    session.add(
        ModulePublisherKeyModel(
            publisher_id="emic-tests",
            key_id="test-1",
            public_key_hex=public_key.hex(),
            status=PublisherKeyStatus.REVOKED.value,
        )
    )
    base, server = _serve_dir(pkg_dir)
    await seed_trusted_catalog(
        session,
        artifact_base=base,
        artifact_name="test.emicpkg",
        content_sha256=digest,
        artifact_size=size,
    )
    await session.commit()
    try:
        result = await ArtifactStagingService(session, settings).fetch_release("integration.demo", "1.0.0")
        assert result.state in {ArtifactState.QUARANTINED, ArtifactState.REJECTED}
        assert result.state != ArtifactState.STAGED
    finally:
        server.shutdown()


@pytest.mark.asyncio
async def test_critical_advisory_quarantined(prod_distribution_session, tmp_path):
    session, settings, _, tmp_path = prod_distribution_session
    sbom = cyclonedx_sbom()
    service, server = await _stage_custom_package(
        session,
        settings,
        tmp_path,
        extra_files={"sbom.json": sbom},
        advisories=critical_advisories_bundle(),
    )
    try:
        result = await service.fetch_release("integration.demo", "1.0.0")
        assert result.state == ArtifactState.QUARANTINED
        assert result.state != ArtifactState.STAGED
        assert "VULNERABILITY_CRITICAL" in result.reason_codes or result.security_status == "CRITICAL"
    finally:
        server.shutdown()


@pytest.mark.asyncio
async def test_high_advisory_requires_security_review(prod_distribution_session, tmp_path):
    session, settings, _, tmp_path = prod_distribution_session
    sbom = cyclonedx_sbom()
    service, server = await _stage_custom_package(
        session,
        settings,
        tmp_path,
        extra_files={"sbom.json": sbom},
        advisories=high_advisories_bundle(),
    )
    try:
        result = await service.fetch_release("integration.demo", "1.0.0")
        assert PolicyDecision.REQUIRE_SECURITY_REVIEW.value in (result.policy_decision or "")
        assert result.state != ArtifactState.STAGED or "VULNERABILITY_HIGH" in result.reason_codes
    finally:
        server.shutdown()


@pytest.mark.asyncio
async def test_sbom_digest_substitution_rejected(prod_distribution_session, tmp_path):
    session, settings, _, tmp_path = prod_distribution_session
    sbom = cyclonedx_sbom()
    private_key, public_key = generate_ed25519_keypair()
    pkg_dir = tmp_path / "artifacts"
    pkg_dir.mkdir(parents=True)
    pkg_path = pkg_dir / "test.emicpkg"
    _build_digest, size = build_emicpkg(pkg_path, extra_files={"sbom.json": sbom}, private_key=private_key)
    digest = _catalog_digest(pkg_path)
    session.add(
        ModulePublisherKeyModel(
            publisher_id="emic-tests",
            key_id="test-1",
            public_key_hex=public_key.hex(),
            status=PublisherKeyStatus.TRUSTED.value,
        )
    )
    base, server = _serve_dir(pkg_dir)
    catalog = {
        "snapshot": {"version": 2},
        "modules": {
            "integration.demo": {
                "publisher_id": "emic-tests",
                "releases": {
                    "1.0.0": {
                        "release_id": "integration.demo@1.0.0",
                        "publisher_id": "emic-tests",
                        "artifact_url": f"{base}/test.emicpkg",
                        "content_sha256": digest,
                        "artifact_size": size,
                        "sbom_ref": {"embedded": True, "sha256": "0" * 64},
                    }
                },
            }
        },
    }
    await seed_trusted_catalog(session, artifact_base=base, catalog_overrides=catalog)
    await session.commit()
    try:
        result = await ArtifactStagingService(session, settings).fetch_release("integration.demo", "1.0.0")
        assert result.state == ArtifactState.QUARANTINED
        assert any("SBOM" in c for c in result.reason_codes)
    finally:
        server.shutdown()


@pytest.mark.asyncio
async def test_archive_traversal_quarantined(prod_distribution_session, tmp_path):
    session, settings, _, tmp_path = prod_distribution_session
    pkg_dir = tmp_path / "artifacts"
    pkg_dir.mkdir(parents=True)
    evil = pkg_dir / "evil.emicpkg"
    with zipfile.ZipFile(evil, "w") as zf:
        zf.writestr("../../outside.txt", "bad")
        zf.writestr("manifest.json", "{}")
    digest = _catalog_digest(evil)
    size = evil.stat().st_size
    base, server = _serve_dir(pkg_dir)
    await seed_trusted_catalog(
        session,
        artifact_base=base,
        artifact_name="evil.emicpkg",
        content_sha256=digest,
        artifact_size=size,
    )
    await session.commit()
    try:
        result = await ArtifactStagingService(session, settings).fetch_release("integration.demo", "1.0.0")
        assert result.state in {ArtifactState.QUARANTINED, ArtifactState.REJECTED}
        assert result.state != ArtifactState.STAGED
    finally:
        server.shutdown()


@pytest.mark.asyncio
async def test_break_glass_cannot_override_digest_mismatch(distribution_session, artifact_server):
    session, settings, _ = distribution_session
    get_break_glass_store().activate(
        reason="test",
        actor="admin",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    row = await seed_trusted_catalog(session, artifact_base=artifact_server)
    catalog = json.loads(row.catalog_json)
    catalog["modules"]["integration.demo"]["releases"]["1.0.0"]["content_sha256"] = "0" * 64
    row.catalog_json = json.dumps(catalog, sort_keys=True)
    await session.commit()
    try:
        with pytest.raises(DistributionError) as exc:
            await ArtifactStagingService(session, settings).fetch_release("integration.demo", "1.0.0")
        assert exc.value.code == DistributionErrorCode.ARTIFACT_DIGEST_MISMATCH
    finally:
        get_break_glass_store().clear()


async def _stage_evil_zip(session, settings, tmp_path, evil_name: str, build_fn):
    pkg_dir = tmp_path / "artifacts"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    evil = pkg_dir / evil_name
    build_fn(evil)
    digest = _catalog_digest(evil)
    size = evil.stat().st_size
    base, server = _serve_dir(pkg_dir)
    await seed_trusted_catalog(
        session,
        artifact_base=base,
        artifact_name=evil_name,
        content_sha256=digest,
        artifact_size=size,
    )
    await session.commit()
    return ArtifactStagingService(session, settings), server


def _build_abs_path_zip(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("/etc/passwd", "bad")


def _build_duplicate_paths_zip(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("manifest.json", "{}")
    with zipfile.ZipFile(path, "a") as zf:
        zf.writestr("manifest.json", '{"module_id":"x"}')


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "evil_name,build_fn",
    [
        ("abs.emicpkg", _build_abs_path_zip),
        ("dup.emicpkg", _build_duplicate_paths_zip),
    ],
)
async def test_remote_archive_path_rejected(prod_distribution_session, tmp_path, evil_name, build_fn):
    session, settings, _, tmp_path = prod_distribution_session
    service, server = await _stage_evil_zip(session, settings, tmp_path, evil_name, build_fn)
    try:
        result = await service.fetch_release("integration.demo", "1.0.0")
        assert result.state in {ArtifactState.QUARANTINED, ArtifactState.REJECTED}
        assert result.state != ArtifactState.STAGED
    finally:
        server.shutdown()


@pytest.mark.asyncio
async def test_remote_archive_too_many_entries_rejected(prod_distribution_session, tmp_path):
    session, settings, _, tmp_path = prod_distribution_session

    def build(p: Path) -> None:
        with zipfile.ZipFile(p, "w") as zf:
            for i in range(10_001):
                zf.writestr(f"f{i}.txt", "x")

    service, server = await _stage_evil_zip(session, settings, tmp_path, "many.emicpkg", build)
    try:
        result = await service.fetch_release("integration.demo", "1.0.0")
        assert result.state in {ArtifactState.QUARANTINED, ArtifactState.REJECTED}
    finally:
        server.shutdown()


@pytest.mark.asyncio
async def test_remote_archive_compression_bomb_rejected(prod_distribution_session, tmp_path):
    session, settings, _, tmp_path = prod_distribution_session

    def build(p: Path) -> None:
        with zipfile.ZipFile(p, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("zeros.bin", b"\0" * (512 * 1024))

    service, server = await _stage_evil_zip(session, settings, tmp_path, "bomb.emicpkg", build)
    try:
        result = await service.fetch_release("integration.demo", "1.0.0")
        assert result.state in {ArtifactState.QUARANTINED, ArtifactState.REJECTED}
    finally:
        server.shutdown()


@pytest.mark.asyncio
async def test_break_glass_cannot_override_critical_advisory(prod_distribution_session, tmp_path):
    session, settings, _, tmp_path = prod_distribution_session
    get_break_glass_store().activate(
        reason="test",
        actor="admin",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    sbom = cyclonedx_sbom()
    service, server = await _stage_custom_package(
        session,
        settings,
        tmp_path,
        extra_files={"sbom.json": sbom},
        advisories=critical_advisories_bundle(),
    )
    try:
        result = await service.fetch_release("integration.demo", "1.0.0")
        assert result.state == ArtifactState.QUARANTINED
        assert result.state != ArtifactState.STAGED
    finally:
        server.shutdown()
        get_break_glass_store().clear()


@pytest.mark.asyncio
async def test_break_glass_cannot_override_revoked_key(prod_distribution_session, tmp_path):
    session, settings, _, tmp_path = prod_distribution_session
    get_break_glass_store().activate(
        reason="test",
        actor="admin",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    private_key, public_key = generate_ed25519_keypair()
    pkg_dir = tmp_path / "artifacts"
    pkg_dir.mkdir(parents=True)
    pkg_path = pkg_dir / "test.emicpkg"
    _build_digest, size = build_emicpkg(pkg_path, private_key=private_key)
    digest = _catalog_digest(pkg_path)
    session.add(
        ModulePublisherKeyModel(
            publisher_id="emic-tests",
            key_id="test-1",
            public_key_hex=public_key.hex(),
            status=PublisherKeyStatus.REVOKED.value,
        )
    )
    base, server = _serve_dir(pkg_dir)
    await seed_trusted_catalog(
        session,
        artifact_base=base,
        artifact_name="test.emicpkg",
        content_sha256=digest,
        artifact_size=size,
    )
    await session.commit()
    try:
        result = await ArtifactStagingService(session, settings).fetch_release("integration.demo", "1.0.0")
        assert result.state in {ArtifactState.QUARANTINED, ArtifactState.REJECTED}
        assert result.state != ArtifactState.STAGED
    finally:
        server.shutdown()
        get_break_glass_store().clear()


@pytest.mark.asyncio
async def test_break_glass_cannot_override_ownership_mismatch(prod_distribution_session, tmp_path):
    session, settings, _, tmp_path = prod_distribution_session
    get_break_glass_store().activate(
        reason="test",
        actor="admin",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    service, server = await _stage_custom_package(session, settings, tmp_path)
    session.add(ModuleOwnershipModel(module_id="integration.demo", publisher_id="other-owner"))
    await session.commit()
    try:
        result = await service.fetch_release("integration.demo", "1.0.0")
        assert result.state == ArtifactState.QUARANTINED
    finally:
        server.shutdown()
        get_break_glass_store().clear()
