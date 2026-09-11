"""Shared helpers for marketplace TUF tests."""

from __future__ import annotations

import contextlib
import shutil
import socket
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "marketplace_tuf"
REPO_DIR = FIXTURE_ROOT / "repository"
METADATA_DIR = REPO_DIR / "metadata"
ROLLBACK_METADATA_DIR = REPO_DIR / "rollback_v1" / "metadata"
TARGETS_DIR = REPO_DIR / "targets"
PINNED_ROOT = FIXTURE_ROOT / "pinned_root.json"


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
    """Temporarily serve v1 rollback metadata from the live repository."""
    backups: dict[Path, bytes] = {}
    files = ("timestamp.json", "snapshot.json", "targets.json")
    source_dir = ROLLBACK_METADATA_DIR if version == 1 else METADATA_DIR
    try:
        for name in files:
            live = METADATA_DIR / name
            backups[live] = live.read_bytes()
            live.write_bytes((source_dir / name).read_bytes())
        if version == 1:
            for path in TARGETS_DIR.rglob("*"):
                if path.is_file():
                    backups[path] = path.read_bytes()
            v1_targets = FIXTURE_ROOT / "repository" / "targets"
            for path in v1_targets.rglob("*"):
                if path.is_file():
                    rel = path.relative_to(v1_targets)
                    dest = TARGETS_DIR / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if dest.exists() and dest not in backups:
                        backups[dest] = dest.read_bytes()
                    dest.write_bytes(path.read_bytes())
        yield
    finally:
        for path, content in backups.items():
            path.write_bytes(content)


def restore_metadata_from_backups(backups: dict[Path, bytes]) -> None:
    for path, content in backups.items():
        path.write_bytes(content)
