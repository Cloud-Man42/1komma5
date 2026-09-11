"""TUF metadata security tests (Step 5C.1 / 5C.1.5)."""

from __future__ import annotations

import contextlib
import socket
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from tuf.api.metadata import Metadata, Timestamp

from energy_core.platform.modules.marketplace.tuf_client import MarketplaceMetadataClient
from energy_core.platform.modules.marketplace.types import MetadataErrorCode, SyncOutcome

pytestmark = pytest.mark.integration

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "marketplace_tuf"
METADATA_DIR = FIXTURE_ROOT / "repository" / "metadata"
ROLLBACK_METADATA_DIR = FIXTURE_ROOT / "repository" / "rollback_v1" / "metadata"
PINNED_ROOT = FIXTURE_ROOT / "pinned_root.json"
REPO_DIR = FIXTURE_ROOT / "repository"
TARGETS_DIR = REPO_DIR / "targets"


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def start_tuf_fixture_server() -> tuple[str, str, ThreadingHTTPServer]:
    host = "127.0.0.1"
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, 0))
    port = sock.getsockname()[1]
    sock.close()
    server = ThreadingHTTPServer((host, port), _QuietHandler)
    server.daemon_threads = True

    def serve() -> None:
        import os

        os.chdir(REPO_DIR)
        server.serve_forever(poll_interval=0.01)

    threading.Thread(target=serve, daemon=True).start()
    base = f"http://{host}:{port}/"
    return f"{base}metadata/", f"{base}targets/", server


@contextlib.contextmanager
def serve_metadata_version(version: int):
    backups: dict[Path, bytes] = {}
    files = ("timestamp.json", "snapshot.json", "targets.json")
    source_dir = ROLLBACK_METADATA_DIR if version == 1 else METADATA_DIR
    try:
        for name in files:
            live = METADATA_DIR / name
            backups[live] = live.read_bytes()
            live.write_bytes((source_dir / name).read_bytes())
        yield
    finally:
        for path, content in backups.items():
            path.write_bytes(content)


@pytest.fixture(scope="module")
def tuf_urls():
    metadata_url, targets_url, server = start_tuf_fixture_server()
    yield metadata_url, targets_url
    server.shutdown()


def _client(metadata_url: str, targets_url: str, *, tuf_state_dir: Path | None = None) -> MarketplaceMetadataClient:
    return MarketplaceMetadataClient(
        metadata_base_url=metadata_url,
        targets_base_url=targets_url,
        pinned_root_bytes=PINNED_ROOT.read_bytes(),
        require_https=False,
        tuf_state_dir=tuf_state_dir,
    )


def test_sync_success(tuf_urls, tmp_path):
    metadata_url, targets_url = tuf_urls
    result = _client(metadata_url, targets_url, tuf_state_dir=tmp_path / "tuf-a").sync_metadata()
    assert result.outcome == SyncOutcome.SUCCESS
    assert result.catalog is not None
    assert result.revocations is not None
    assert result.versions is not None
    assert result.versions.root_version == 2
    assert result.versions.snapshot_version == 2
    assert result.versions.targets_version == 2
    assert result.revocations["bundle"]["generation"] == 2


def test_bad_signature_rejected(tuf_urls, tmp_path):
    metadata_url, targets_url = tuf_urls
    backup = METADATA_DIR / "timestamp.json.bak"
    original = METADATA_DIR / "timestamp.json"
    backup.write_bytes(original.read_bytes())
    try:
        original.write_text(original.read_text().replace('"sig":', '"sigx":'), encoding="utf-8")
        result = _client(metadata_url, targets_url, tuf_state_dir=tmp_path / "tuf-bad").sync_metadata()
        assert result.outcome == SyncOutcome.REJECTED
    finally:
        original.write_bytes(backup.read_bytes())
        backup.unlink(missing_ok=True)


def test_expired_timestamp_rejected(tuf_urls, tmp_path):
    metadata_url, targets_url = tuf_urls
    ts_path = METADATA_DIR / "timestamp.json"
    backup = ts_path.read_bytes()
    try:
        md = Metadata[Timestamp].from_file(str(ts_path))
        md.signed.expires = md.signed.expires.replace(year=2000)
        md.to_file(str(ts_path))
        result = _client(metadata_url, targets_url, tuf_state_dir=tmp_path / "tuf-exp").sync_metadata()
        assert result.outcome == SyncOutcome.REJECTED
        assert result.error_code in {MetadataErrorCode.EXPIRED_METADATA, MetadataErrorCode.INVALID_SIGNATURE}
    finally:
        ts_path.write_bytes(backup)


def test_rollback_snapshot_rejected(tuf_urls, tmp_path):
    metadata_url, targets_url = tuf_urls
    state_dir = tmp_path / "tuf-snap-rollback"
    client = _client(metadata_url, targets_url, tuf_state_dir=state_dir)
    ok = client.sync_metadata()
    assert ok.outcome == SyncOutcome.SUCCESS
    assert ok.versions is not None
    assert ok.versions.snapshot_version == 2

    with serve_metadata_version(1):
        bad = client.sync_metadata()
    assert bad.outcome == SyncOutcome.REJECTED
    assert bad.error_code in {
        MetadataErrorCode.METADATA_ROLLBACK_DETECTED,
        MetadataErrorCode.INVALID_SIGNATURE,
        MetadataErrorCode.EXPIRED_METADATA,
    }


def test_rollback_targets_rejected(tuf_urls, tmp_path):
    metadata_url, targets_url = tuf_urls
    state_dir = tmp_path / "tuf-targets-rollback"
    client = _client(metadata_url, targets_url, tuf_state_dir=state_dir)
    assert client.sync_metadata().outcome == SyncOutcome.SUCCESS
    with serve_metadata_version(1):
        bad = client.sync_metadata()
    assert bad.outcome == SyncOutcome.REJECTED


def test_rollback_timestamp_rejected(tuf_urls, tmp_path):
    metadata_url, targets_url = tuf_urls
    state_dir = tmp_path / "tuf-ts-rollback"
    client = _client(metadata_url, targets_url, tuf_state_dir=state_dir)
    assert client.sync_metadata().outcome == SyncOutcome.SUCCESS
    with serve_metadata_version(1):
        bad = client.sync_metadata()
    assert bad.outcome == SyncOutcome.REJECTED


def test_root_rotation_accepted(tuf_urls, tmp_path):
    metadata_url, targets_url = tuf_urls
    result = _client(metadata_url, targets_url, tuf_state_dir=tmp_path / "tuf-root").sync_metadata()
    assert result.outcome == SyncOutcome.SUCCESS
    assert result.versions is not None
    assert result.versions.root_version == 2


@pytest.mark.asyncio
async def test_root_rollback_rejected(tuf_urls, tmp_path):
    metadata_url, targets_url = tuf_urls
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from energy_core.config import Settings
    from energy_core.db.models.base import Base
    from energy_core.platform.modules.marketplace.sync_service import MarketplaceSyncService

    db_path = tmp_path / "root-rollback.db"
    engine_url = f"sqlite+aiosqlite:///{db_path}"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=engine_url,
        MARKETPLACE_METADATA_ENABLED=True,
        MARKETPLACE_METADATA_URL=metadata_url,
        MARKETPLACE_TARGETS_URL=targets_url,
        MARKETPLACE_TRUSTED_ROOT_PATH=str(PINNED_ROOT),
        MARKETPLACE_TUF_STATE_PATH=str(tmp_path / "tuf-root-rollback"),
    )
    engine = create_async_engine(engine_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    service = MarketplaceSyncService(settings)
    async with session_factory() as session:
        result, _ = await service.sync(session)
        assert result.outcome == SyncOutcome.SUCCESS
        assert result.versions is not None
        assert result.versions.root_version == 2
    with serve_metadata_version(1):
        async with session_factory() as session:
            bad, apply = await service.sync(session)
    assert bad.outcome == SyncOutcome.REJECTED
    assert apply is not None
    assert apply.promoted is False
    await engine.dispose()


def test_unknown_root_rejected(tuf_urls, tmp_path):
    metadata_url, targets_url = tuf_urls
    bogus = b'{"signed":{"_type":"root","version":99,"expires":"2099-01-01T00:00:00Z","keys":{},"roles":{}},"signatures":[]}'
    client = MarketplaceMetadataClient(
        metadata_base_url=metadata_url,
        targets_base_url=targets_url,
        pinned_root_bytes=bogus,
        require_https=False,
        tuf_state_dir=tmp_path / "tuf-unknown",
    )
    assert client.sync_metadata().outcome == SyncOutcome.REJECTED


def test_mix_and_match_snapshot_rejected(tuf_urls, tmp_path):
    metadata_url, targets_url = tuf_urls
    backups: dict[Path, bytes] = {}
    try:
        for fname in ("snapshot.json", "2.snapshot.json"):
            snap_path = METADATA_DIR / fname
            backups[snap_path] = snap_path.read_bytes()
            data = bytearray(backups[snap_path])
            data[-20] ^= 0xFF
            snap_path.write_bytes(bytes(data))
        result = _client(metadata_url, targets_url, tuf_state_dir=tmp_path / "tuf-mix").sync_metadata()
        assert result.outcome == SyncOutcome.REJECTED
    finally:
        for path, content in backups.items():
            path.write_bytes(content)


def test_persistent_state_rejects_rollback_after_restart(tuf_urls, tmp_path):
    metadata_url, targets_url = tuf_urls
    state_dir = tmp_path / "persistent-tuf"
    client_a = _client(metadata_url, targets_url, tuf_state_dir=state_dir)
    assert client_a.sync_metadata().outcome == SyncOutcome.SUCCESS

    client_b = _client(metadata_url, targets_url, tuf_state_dir=state_dir)
    with serve_metadata_version(1):
        bad = client_b.sync_metadata()
    assert bad.outcome == SyncOutcome.REJECTED


def test_cache_unchanged_on_rejected_sync(tuf_urls, tmp_path):
    metadata_url, targets_url = tuf_urls
    client = _client(metadata_url, targets_url, tuf_state_dir=tmp_path / "tuf-reject")
    assert client.sync_metadata().outcome == SyncOutcome.SUCCESS
    ts_path = METADATA_DIR / "timestamp.json"
    backup = ts_path.read_bytes()
    try:
        data = bytearray(backup)
        data[-20] ^= 0xFF
        ts_path.write_bytes(bytes(data))
        assert client.sync_metadata().outcome == SyncOutcome.REJECTED
    finally:
        ts_path.write_bytes(backup)
    assert client.sync_metadata().outcome == SyncOutcome.SUCCESS


@pytest.mark.asyncio
async def test_trust_metadata_updated_event_emitted(tmp_path):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from energy_core.config import Settings
    from energy_core.db.models.base import Base
    from energy_core.platform.modules.marketplace.sync_service import MarketplaceSyncService
    from energy_core.platform.modules.marketplace.types import TrustMetadataUpdatedEvent, trust_metadata_listeners

    metadata_url, targets_url, server = start_tuf_fixture_server()
    events: list[TrustMetadataUpdatedEvent] = []
    trust_metadata_listeners.register(events.append)
    db_path = tmp_path / "event.db"
    engine_url = f"sqlite+aiosqlite:///{db_path}"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=engine_url,
        MARKETPLACE_METADATA_ENABLED=True,
        MARKETPLACE_METADATA_URL=metadata_url,
        MARKETPLACE_TARGETS_URL=targets_url,
        MARKETPLACE_TRUSTED_ROOT_PATH=str(PINNED_ROOT),
        MARKETPLACE_TUF_STATE_PATH=str(tmp_path / "tuf-event"),
    )
    engine = create_async_engine(engine_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    service = MarketplaceSyncService(settings)
    async with session_factory() as session:
        result, apply = await service.sync(session)
    assert result.outcome == SyncOutcome.SUCCESS
    assert apply is not None and apply.promoted
    assert len(events) == 1
    assert events[0].cache_generation >= 1
    await engine.dispose()
    server.shutdown()


def test_no_package_installer_import():
    from energy_core.platform.modules.marketplace import tuf_client as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    assert "PackageInstaller" not in source
    assert "PackageValidator" not in source
