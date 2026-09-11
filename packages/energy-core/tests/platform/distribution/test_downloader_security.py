"""Downloader security: concurrent fetch, cache tamper, partial files, crash safety."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from energy_core.platform.modules.distribution.downloader import SecureArtifactDownloader
from energy_core.platform.modules.distribution.types import (
    ArtifactDescriptor,
    ArtifactSourceType,
    DistributionError,
    DistributionErrorCode,
)
import importlib.util
from pathlib import Path

_helpers_path = Path(__file__).resolve().parent / "distribution_helpers.py"
_spec = importlib.util.spec_from_file_location("distribution_helpers", _helpers_path)
_helpers = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_helpers)
ARTIFACT_MANIFEST = _helpers.ARTIFACT_MANIFEST
seed_trusted_catalog = _helpers.seed_trusted_catalog
from energy_core.platform.modules.distribution.staging_service import ArtifactStagingService
from energy_core.platform.modules.distribution.types import ArtifactState

pytestmark = pytest.mark.integration


def _descriptor(url: str) -> ArtifactDescriptor:
    return ArtifactDescriptor(
        module_id="integration.demo",
        publisher_id="emic-tests",
        version="1.0.0",
        release_id="integration.demo@1.0.0",
        artifact_url=f"{url}/{ARTIFACT_MANIFEST['artifact_name']}",
        content_sha256=ARTIFACT_MANIFEST["content_sha256"],
        artifact_size=ARTIFACT_MANIFEST["artifact_size"],
        source=ArtifactSourceType.PUBLIC,
    )


@pytest.mark.asyncio
async def test_concurrent_fetch_single_download(artifact_server, distribution_session):
    session, settings, _ = distribution_session
    downloader = SecureArtifactDownloader(settings)
    desc = _descriptor(artifact_server)
    calls = {"n": 0}
    original = downloader._stream_download

    def counting_stream(descriptor, dest):
        calls["n"] += 1
        return original(descriptor, dest)

    with patch.object(downloader, "_stream_download", side_effect=counting_stream):
        results = await asyncio.gather(downloader.download(desc), downloader.download(desc))
    assert calls["n"] == 1
    assert results[0].sha256 == results[1].sha256
    assert results[0].path == results[1].path


@pytest.mark.asyncio
async def test_cache_tamper_detected_on_reuse(artifact_server, distribution_session):
    session, settings, _ = distribution_session
    downloader = SecureArtifactDownloader(settings)
    desc = _descriptor(artifact_server)
    first = await downloader.download(desc)
    cache = Path(first.path)
    data = bytearray(cache.read_bytes())
    data[0] ^= 0xFF
    cache.write_bytes(bytes(data))
    with pytest.raises(DistributionError) as exc:
        await downloader.download(desc)
    assert exc.value.code == DistributionErrorCode.CACHE_CORRUPT


@pytest.mark.asyncio
async def test_partial_file_not_promoted(artifact_server, distribution_session):
    session, settings, _ = distribution_session
    downloader = SecureArtifactDownloader(settings)
    partial = downloader.partial_path_for(ARTIFACT_MANIFEST["content_sha256"])
    partial.parent.mkdir(parents=True, exist_ok=True)
    partial.write_bytes(b"incomplete")
    verified = downloader.staging_path_for(ARTIFACT_MANIFEST["content_sha256"])
    assert not verified.exists()
    result = await downloader.download(_descriptor(artifact_server))
    assert result.from_cache is False or verified.is_file()
    assert not partial.exists() or partial.stat().st_size == 0 or not partial.exists()


@pytest.mark.asyncio
async def test_crash_before_promotion_leaves_no_verified(artifact_server, distribution_session):
    session, settings, _ = distribution_session
    downloader = SecureArtifactDownloader(settings)
    desc = _descriptor(artifact_server)
    verified = downloader.staging_path_for(desc.content_sha256)

    def boom(descriptor, dest):
        dest.write_bytes(b"x" * 10)
        raise RuntimeError("simulated crash")

    with patch.object(downloader, "_stream_download", side_effect=boom):
        with pytest.raises(DistributionError):
            await downloader.download(desc)
    assert not verified.exists()


@pytest.mark.asyncio
async def test_os_replace_failure_does_not_leave_verified(artifact_server, distribution_session):
    session, settings, _ = distribution_session
    downloader = SecureArtifactDownloader(settings)
    desc = _descriptor(artifact_server)
    verified = downloader.staging_path_for(desc.content_sha256)
    with patch("energy_core.platform.modules.distribution.downloader.os.replace", side_effect=OSError("fail")):
        with pytest.raises(DistributionError):
            await downloader.download(desc)
    assert not verified.exists()


@pytest.mark.asyncio
async def test_staging_db_failure_after_verify_not_staged(artifact_server, distribution_session):
    session, settings, _ = distribution_session
    await seed_trusted_catalog(session, artifact_base=artifact_server)
    await session.commit()
    service = ArtifactStagingService(session, settings)
    with patch.object(service._artifacts, "upsert_security", side_effect=RuntimeError("db fail")):
        with pytest.raises(DistributionError):
            await service.fetch_release("integration.demo", "1.0.0")
    row = await service._artifacts.get_by_digest(ARTIFACT_MANIFEST["content_sha256"])
    assert row is not None
    assert row.state != ArtifactState.STAGED.value


@pytest.mark.asyncio
async def test_cleanup_partials_safe(distribution_session):
    _, settings, _ = distribution_session
    downloader = SecureArtifactDownloader(settings)
    partial = downloader.partial_path_for("abc")
    partial.parent.mkdir(parents=True, exist_ok=True)
    partial.write_bytes(b"old")
    os.utime(partial, (0, 0))
    removed = downloader.cleanup_partials(max_age_seconds=1)
    assert removed >= 1
    assert not partial.exists()
