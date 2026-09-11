"""Network hardening tests for marketplace metadata client."""

from __future__ import annotations

import asyncio
import socket
import threading
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from energy_core.config import Settings
from energy_core.db.models.base import Base
from energy_core.platform.modules.marketplace.sync_service import MarketplaceSyncService
from energy_core.platform.modules.marketplace.tuf_client import (
    HttpxFetcher,
    MarketplaceMetadataClient,
    MarketplaceMetadataError,
    validate_metadata_base_url,
)
from energy_core.platform.modules.marketplace.types import MetadataErrorCode, SyncOutcome

pytestmark = pytest.mark.integration

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "marketplace_tuf"
PINNED_ROOT = FIXTURE_ROOT / "pinned_root.json"
REPO_DIR = FIXTURE_ROOT / "repository"


class _RedirectHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        self.send_response(302)
        self.send_header("Location", "http://127.0.0.1:9/evil")
        self.end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


class _OversizeHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"x" * 2048)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


class _HangHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        import time

        time.sleep(30)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def _start_custom_server(handler: type[BaseHTTPRequestHandler]) -> tuple[str, ThreadingHTTPServer]:
    host = "127.0.0.1"
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, 0))
    port = sock.getsockname()[1]
    sock.close()
    server = ThreadingHTTPServer((host, port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://{host}:{port}/", server


def _start_tuf_fixture_server() -> tuple[str, str, ThreadingHTTPServer]:
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


@pytest.fixture(scope="module")
def tuf_urls():
    metadata_url, targets_url, server = _start_tuf_fixture_server()
    yield metadata_url, targets_url
    server.shutdown()


def test_production_http_rejected():
    with pytest.raises(MarketplaceMetadataError) as exc:
        validate_metadata_base_url("http://marketplace.example/metadata/", require_https=True)
    assert exc.value.error_code == MetadataErrorCode.INVALID_METADATA


def test_redirect_rejected():
    metadata_url, server = _start_custom_server(_RedirectHandler)
    fetcher = HttpxFetcher(require_https=False, max_bytes=1024, connect_timeout=1.0, read_timeout=1.0)
    try:
        with pytest.raises(MarketplaceMetadataError) as exc:
            next(fetcher._fetch(metadata_url))
        assert exc.value.error_code == MetadataErrorCode.REDIRECT_REJECTED
    finally:
        fetcher.close()
        server.shutdown()


def test_oversize_rejected():
    metadata_url, server = _start_custom_server(_OversizeHandler)
    fetcher = HttpxFetcher(require_https=False, max_bytes=512, connect_timeout=1.0, read_timeout=1.0)
    try:
        with pytest.raises(MarketplaceMetadataError) as exc:
            next(fetcher._fetch(metadata_url))
        assert exc.value.error_code == MetadataErrorCode.SIZE_LIMIT_EXCEEDED
    finally:
        fetcher.close()
        server.shutdown()


def test_timeout_maps_to_stable_code(tmp_path):
    metadata_url, server = _start_custom_server(_HangHandler)
    try:
        client = MarketplaceMetadataClient(
            metadata_base_url=metadata_url,
            targets_base_url=metadata_url,
            pinned_root_bytes=PINNED_ROOT.read_bytes(),
            require_https=False,
            connect_timeout=0.05,
            read_timeout=0.05,
            tuf_state_dir=tmp_path / "tuf-timeout",
        )
        result = client.sync_metadata()
        assert result.outcome in {SyncOutcome.REJECTED, SyncOutcome.FAILED}
        assert result.error_code in {MetadataErrorCode.TIMEOUT, MetadataErrorCode.NETWORK_ERROR}
    finally:
        server.shutdown()


def test_production_client_requires_https(tmp_path):
    with pytest.raises(MarketplaceMetadataError):
        MarketplaceMetadataClient(
            metadata_base_url="http://127.0.0.1/metadata/",
            targets_base_url="http://127.0.0.1/targets/",
            pinned_root_bytes=PINNED_ROOT.read_bytes(),
            require_https=True,
            tuf_state_dir=tmp_path / "tuf-https",
        )


@pytest.mark.asyncio
async def test_sync_in_progress(tmp_path, monkeypatch):
    metadata_url, targets_url, server = _start_tuf_fixture_server()
    db_path = tmp_path / "sync.db"
    engine_url = f"sqlite+aiosqlite:///{db_path}"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=engine_url,
        MARKETPLACE_METADATA_ENABLED=True,
        MARKETPLACE_METADATA_URL=metadata_url,
        MARKETPLACE_TARGETS_URL=targets_url,
        MARKETPLACE_TRUSTED_ROOT_PATH=str(PINNED_ROOT),
        MARKETPLACE_TUF_STATE_PATH=str(tmp_path / "tuf-sync-lock"),
    )
    engine = create_async_engine(engine_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    service = MarketplaceSyncService(settings)

    original_to_thread = asyncio.to_thread
    gate = asyncio.Event()

    async def delayed_to_thread(func, /, *args, **kwargs):
        gate.set()
        await asyncio.sleep(0.2)
        return await original_to_thread(func, *args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", delayed_to_thread)

    async def run_one() -> SyncOutcome:
        async with session_factory() as session:
            result, _ = await service.sync(session)
            return result.outcome

    first = asyncio.create_task(run_one())
    await gate.wait()
    second = asyncio.create_task(run_one())
    outcomes = await asyncio.gather(first, second)
    assert SyncOutcome.IN_PROGRESS in outcomes
    assert outcomes.count(SyncOutcome.SUCCESS) == 1
    await engine.dispose()
    server.shutdown()
