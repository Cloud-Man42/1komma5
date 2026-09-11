"""Full SSRF / URL policy matrix for PUBLIC artifact sources (Sprint B.5)."""

from __future__ import annotations

import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import pytest

from energy_core.config import Settings
from energy_core.platform.modules.distribution.downloader import SecureArtifactDownloader
from energy_core.platform.modules.distribution.types import (
    ArtifactDescriptor,
    ArtifactSourceType,
    DistributionError,
    DistributionErrorCode,
)
from energy_core.platform.modules.distribution.url_policy import validate_artifact_url

pytestmark = pytest.mark.integration

PUBLIC = ArtifactSourceType.PUBLIC
PROD = True  # require_https


def _reject(url: str, *, require_https: bool = PROD) -> DistributionErrorCode:
    with pytest.raises(DistributionError) as exc:
        validate_artifact_url(url, source=PUBLIC, require_https=require_https)
    return exc.value.code


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1/pkg.emicpkg",
        "https://localhost/pkg.emicpkg",
        "https://10.0.0.1/pkg.emicpkg",
        "https://172.16.0.1/pkg.emicpkg",
        "https://192.168.1.10/pkg.emicpkg",
        "https://169.254.169.254/latest/meta-data/",
        "https://[::1]/pkg.emicpkg",
        "https://[fe80::1]/pkg.emicpkg",
    ],
)
def test_public_rejects_private_and_loopback_ips(url: str) -> None:
    assert _reject(url) == DistributionErrorCode.ARTIFACT_SSRF_BLOCKED


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/pkg.emicpkg",
        "data:text/plain,evil",
    ],
)
def test_public_rejects_forbidden_schemes(url: str) -> None:
    assert _reject(url) == DistributionErrorCode.ARTIFACT_URL_INVALID


def test_public_rejects_embedded_credentials() -> None:
    assert _reject("https://user:pass@example.com/pkg.emicpkg") == DistributionErrorCode.ARTIFACT_URL_INVALID


def test_public_rejects_http_in_production_mode() -> None:
    assert _reject("http://203.0.113.10/pkg.emicpkg", require_https=True) == DistributionErrorCode.ARTIFACT_URL_INVALID


def test_dns_multi_address_public_private_rejected() -> None:
    def fake_getaddrinfo(host: str, port, *args, **kwargs):
        if host == "dual.example.test":
            return [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("203.0.113.10", 0)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.50.99", 0)),
            ]
        raise socket.gaierror("unknown host")

    with patch("energy_core.platform.modules.distribution.url_policy.socket.getaddrinfo", fake_getaddrinfo):
        assert (
            _reject("https://dual.example.test/pkg.emicpkg")
            == DistributionErrorCode.ARTIFACT_SSRF_BLOCKED
        )


class _RedirectPrivateHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        self.send_response(302)
        self.send_header("Location", "https://192.168.1.50/private.emicpkg")
        self.end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def test_redirect_public_to_private_rejected(tmp_path) -> None:
    import socket as sock
    import threading

    host = "127.0.0.1"
    s = sock.socket(sock.AF_INET, sock.SOCK_STREAM)
    s.bind((host, 0))
    port = s.getsockname()[1]
    s.close()
    server = ThreadingHTTPServer((host, port), _RedirectPrivateHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        MARKETPLACE_STAGING_PATH=str(tmp_path / "staging"),
        MARKETPLACE_ARTIFACT_ALLOW_REDIRECTS=True,
        MARKETPLACE_ARTIFACT_MAX_REDIRECTS=3,
    )
    downloader = SecureArtifactDownloader(settings)
    descriptor = ArtifactDescriptor(
        module_id="integration.demo",
        publisher_id="emic-tests",
        version="1.0.0",
        release_id="r1",
        artifact_url=f"http://{host}:{port}/start.emicpkg",
        content_sha256="a" * 64,
        artifact_size=None,
        source=PUBLIC,
    )
    try:
        with pytest.raises(DistributionError) as exc:
            import asyncio

            asyncio.run(downloader.download(descriptor))
        assert exc.value.code in {
            DistributionErrorCode.ARTIFACT_SSRF_BLOCKED,
            DistributionErrorCode.ARTIFACT_REDIRECT_REJECTED,
        }
    finally:
        server.shutdown()
