"""Distribution test fixtures."""

from __future__ import annotations

import json
import socket
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from energy_core.config import Settings
from energy_core.db.models import Base

import importlib.util
from pathlib import Path

_helpers_path = Path(__file__).resolve().parent / "distribution_helpers.py"
_spec = importlib.util.spec_from_file_location("distribution_helpers", _helpers_path)
_helpers = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_helpers)
ARTIFACT_MANIFEST = _helpers.ARTIFACT_MANIFEST
FIXTURE_ROOT = _helpers.FIXTURE_ROOT
seed_trusted_catalog = _helpers.seed_trusted_catalog

ARTIFACTS_DIR = FIXTURE_ROOT / "repository" / "artifacts"

__all__ = ["ARTIFACT_MANIFEST", "seed_trusted_catalog"]


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


@pytest.fixture
def artifact_server():
    host = "127.0.0.1"
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, 0))
    port = sock.getsockname()[1]
    sock.close()
    serve_root = str(ARTIFACTS_DIR)

    class _ArtifactHandler(_QuietHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=serve_root, **kwargs)

    server = ThreadingHTTPServer((host, port), _ArtifactHandler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    yield f"http://{host}:{port}"
    server.shutdown()


@pytest.fixture
async def distribution_session(tmp_path):
    db_file = tmp_path / "distribution.db"
    staging = tmp_path / "staging"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        EMIC_ALLOW_UNSIGNED_MODULES=True,
        MARKETPLACE_METADATA_ENABLED=True,
        MARKETPLACE_STAGING_PATH=str(staging),
    )
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session, settings, session_factory
    await engine.dispose()
