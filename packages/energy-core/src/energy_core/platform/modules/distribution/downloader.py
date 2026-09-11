"""Streaming secure artifact downloader."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import httpx

from energy_core.config import Settings
from energy_core.platform.modules.distribution.types import (
    ArtifactDescriptor,
    DistributionError,
    DistributionErrorCode,
    DownloadResult,
)
from energy_core.platform.modules.distribution.url_policy import validate_artifact_url
from energy_core.platform.modules.packages.integrity import compute_package_content_sha256

logger = logging.getLogger(__name__)

_download_locks: dict[str, asyncio.Lock] = {}


class SecureArtifactDownloader:
    REDIRECT_STATUS = {301, 302, 303, 307, 308}

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._max_bytes = settings.marketplace_artifact_max_bytes
        self._connect_timeout = settings.marketplace_artifact_connect_timeout_seconds
        self._read_timeout = settings.marketplace_artifact_read_timeout_seconds
        self._require_https = settings.app_env.value == "production"
        self._allow_redirects = settings.marketplace_artifact_allow_redirects
        self._max_redirects = settings.marketplace_artifact_max_redirects
        self._tls_verify = settings.marketplace_artifact_tls_verify
        self._staging_root = Path(settings.resolved_marketplace_staging_path())

    def staging_path_for(self, sha256: str) -> Path:
        return self._staging_root / "verified" / f"{sha256}.emicpkg"

    def partial_path_for(self, sha256: str) -> Path:
        return self._staging_root / "downloads" / f"{sha256}.partial"

    async def download(self, descriptor: ArtifactDescriptor) -> DownloadResult:
        cache_path = self.staging_path_for(descriptor.content_sha256)
        if cache_path.is_file():
            actual = self._artifact_digest(cache_path, artifact_url=descriptor.artifact_url)
            if actual == descriptor.content_sha256:
                if descriptor.artifact_size is not None and cache_path.stat().st_size != descriptor.artifact_size:
                    raise DistributionError(
                        "Cached artifact size mismatch",
                        code=DistributionErrorCode.ARTIFACT_SIZE_MISMATCH,
                    )
                return DownloadResult(
                    path=str(cache_path),
                    sha256=actual,
                    bytes_downloaded=cache_path.stat().st_size,
                    from_cache=True,
                )
            raise DistributionError("Cached artifact digest mismatch", code=DistributionErrorCode.CACHE_CORRUPT)

        lock = _download_locks.setdefault(descriptor.content_sha256, asyncio.Lock())
        async with lock:
            if cache_path.is_file():
                actual = self._artifact_digest(cache_path, artifact_url=descriptor.artifact_url)
                if actual == descriptor.content_sha256:
                    return DownloadResult(
                        path=str(cache_path),
                        sha256=actual,
                        bytes_downloaded=cache_path.stat().st_size,
                        from_cache=True,
                    )

            partial = self.partial_path_for(descriptor.content_sha256)
            partial.parent.mkdir(parents=True, exist_ok=True)
            cache_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                bytes_written, digest = await asyncio.to_thread(
                    self._stream_download,
                    descriptor,
                    partial,
                )
            except DistributionError:
                partial.unlink(missing_ok=True)
                raise
            except Exception as exc:
                partial.unlink(missing_ok=True)
                raise DistributionError(str(exc), code=DistributionErrorCode.DOWNLOAD_TIMEOUT) from exc

            if digest != descriptor.content_sha256:
                partial.unlink(missing_ok=True)
                raise DistributionError(
                    f"Digest mismatch expected={descriptor.content_sha256} actual={digest}",
                    code=DistributionErrorCode.ARTIFACT_DIGEST_MISMATCH,
                )
            if descriptor.artifact_size is not None and bytes_written != descriptor.artifact_size:
                partial.unlink(missing_ok=True)
                raise DistributionError(
                    f"Size mismatch expected={descriptor.artifact_size} actual={bytes_written}",
                    code=DistributionErrorCode.ARTIFACT_SIZE_MISMATCH,
                )

            try:
                os.replace(partial, cache_path)
            except OSError as exc:
                partial.unlink(missing_ok=True)
                cache_path.unlink(missing_ok=True)
                raise DistributionError(
                    f"Failed to promote verified artifact: {exc}",
                    code=DistributionErrorCode.STAGING_FAILED,
                ) from exc
            return DownloadResult(path=str(cache_path), sha256=digest, bytes_downloaded=bytes_written, from_cache=False)

    def _stream_download(self, descriptor: ArtifactDescriptor, dest: Path) -> tuple[int, str]:
        url = descriptor.artifact_url
        redirects = 0
        while True:
            validate_artifact_url(
                url,
                source=descriptor.source,
                require_https=self._require_https,
                internal_cidrs=tuple(self._settings.marketplace_internal_cidrs_list()),
            )
            hasher = hashlib.sha256()
            total = 0
            timeout = httpx.Timeout(self._read_timeout, connect=self._connect_timeout)
            with httpx.Client(timeout=timeout, follow_redirects=False, verify=self._tls_verify) as client:
                with client.stream("GET", url) as response:
                    if response.status_code in self.REDIRECT_STATUS:
                        if not self._allow_redirects:
                            raise DistributionError(
                                f"Redirect rejected: {response.status_code}",
                                code=DistributionErrorCode.ARTIFACT_REDIRECT_REJECTED,
                            )
                        if redirects >= self._max_redirects:
                            raise DistributionError("Too many redirects", code=DistributionErrorCode.ARTIFACT_REDIRECT_REJECTED)
                        location = response.headers.get("location")
                        if not location:
                            raise DistributionError("Redirect missing location", code=DistributionErrorCode.ARTIFACT_REDIRECT_REJECTED)
                        parsed = urlparse(url)
                        next_url = location if location.startswith("http") else f"{parsed.scheme}://{parsed.netloc}{location}"
                        if urlparse(next_url).scheme != "https":
                            raise DistributionError("Redirect must stay HTTPS", code=DistributionErrorCode.ARTIFACT_REDIRECT_REJECTED)
                        url = next_url
                        redirects += 1
                        continue
                    if response.status_code != 200:
                        raise DistributionError(
                            f"HTTP {response.status_code} downloading artifact",
                            code=DistributionErrorCode.ARTIFACT_NOT_FOUND,
                        )
                    cl = response.headers.get("content-length")
                    if cl is not None:
                        try:
                            expected = int(cl)
                            if expected > self._max_bytes:
                                raise DistributionError(
                                    "Content-Length exceeds limit",
                                    code=DistributionErrorCode.DOWNLOAD_SIZE_EXCEEDED,
                                )
                        except ValueError:
                            pass
                    with dest.open("wb") as fh:
                        for chunk in response.iter_bytes():
                            total += len(chunk)
                            if total > self._max_bytes:
                                raise DistributionError(
                                    "Artifact exceeds max size during download",
                                    code=DistributionErrorCode.DOWNLOAD_SIZE_EXCEEDED,
                                )
                            hasher.update(chunk)
                            fh.write(chunk)
            return total, self._artifact_digest(dest, artifact_url=descriptor.artifact_url)

    @staticmethod
    def _artifact_digest(path: Path, *, artifact_url: str | None = None) -> str:
        try:
            if path.suffix == ".emicpkg" or (artifact_url or "").endswith(".emicpkg"):
                return compute_package_content_sha256(path)
            return SecureArtifactDownloader._file_sha256(path)
        except (zipfile.BadZipFile, OSError, ValueError) as exc:
            raise DistributionError("Cached artifact corrupt", code=DistributionErrorCode.CACHE_CORRUPT) from exc

    @staticmethod
    def _file_sha256(path: Path) -> str:
        hasher = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def cleanup_partials(self, *, max_age_seconds: int = 86400) -> int:
        removed = 0
        downloads = self._staging_root / "downloads"
        if not downloads.is_dir():
            return 0
        import time

        now = time.time()
        for partial in downloads.glob("*.partial"):
            try:
                if now - partial.stat().st_mtime > max_age_seconds:
                    partial.unlink()
                    removed += 1
            except OSError:
                continue
        return removed
