"""Marketplace TUF metadata client (Step 5C.1 / 5C.1.5)."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import httpx
from tuf.api.exceptions import DownloadError, DownloadHTTPError, RepositoryError
from tuf.api.metadata import Metadata, Root, Snapshot, Targets, Timestamp
from tuf.ngclient import Updater, UpdaterConfig
from tuf.ngclient.fetcher import FetcherInterface

from energy_core.platform.modules.marketplace.types import (
    ALLOWED_METADATA_TARGETS,
    ADVISORIES_TARGET_PATH,
    CATALOG_TARGET_PATH,
    REVOCATIONS_TARGET_PATH,
    MarketplaceMetadataVersions,
    MarketplaceSyncResult,
    MetadataErrorCode,
    SyncOutcome,
)

logger = logging.getLogger(__name__)


class MarketplaceMetadataError(Exception):
    """Metadata sync or verification failure."""

    def __init__(self, message: str, *, error_code: MetadataErrorCode | None = None) -> None:
        super().__init__(message)
        self.error_code = error_code or MetadataErrorCode.INVALID_METADATA


class HttpxFetcher(FetcherInterface):
    """TUF FetcherInterface with HTTPS, no redirects, and size limits."""

    REDIRECT_STATUS = {301, 302, 303, 307, 308}

    def __init__(
        self,
        *,
        require_https: bool,
        max_bytes: int,
        connect_timeout: float,
        read_timeout: float,
    ) -> None:
        self._require_https = require_https
        self._max_bytes = max_bytes
        self._client = httpx.Client(
            timeout=httpx.Timeout(read_timeout, connect=connect_timeout),
            follow_redirects=False,
        )

    def close(self) -> None:
        self._client.close()

    def _fetch(self, url: str) -> Iterator[bytes]:
        parsed = urlparse(url)
        if self._require_https and parsed.scheme != "https":
            raise MarketplaceMetadataError(
                "HTTPS required for marketplace metadata",
                error_code=MetadataErrorCode.INVALID_METADATA,
            )
        try:
            response = self._client.get(url)
        except httpx.TimeoutException as exc:
            raise MarketplaceMetadataError(
                f"Marketplace metadata timeout for {url}",
                error_code=MetadataErrorCode.TIMEOUT,
            ) from exc
        except httpx.ConnectError as exc:
            raise MarketplaceMetadataError(
                f"Marketplace metadata connect error for {url}",
                error_code=MetadataErrorCode.NETWORK_ERROR,
            ) from exc
        except httpx.HTTPError as exc:
            raise MarketplaceMetadataError(
                f"Marketplace metadata network error for {url}: {exc}",
                error_code=MetadataErrorCode.NETWORK_ERROR,
            ) from exc

        if response.status_code in self.REDIRECT_STATUS:
            location = response.headers.get("location", "")
            raise MarketplaceMetadataError(
                f"Redirect rejected for {url} -> {location}",
                error_code=MetadataErrorCode.REDIRECT_REJECTED,
            )
        if response.status_code != 200:
            raise DownloadHTTPError(
                f"HTTP {response.status_code} for {url}",
                response.status_code,
            )
        content = response.content
        if len(content) > self._max_bytes:
            raise MarketplaceMetadataError(
                f"Metadata response exceeds {self._max_bytes} bytes",
                error_code=MetadataErrorCode.SIZE_LIMIT_EXCEEDED,
            )
        yield content


def validate_metadata_base_url(url: str, *, require_https: bool) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise MarketplaceMetadataError(
            "Invalid marketplace metadata URL scheme",
            error_code=MetadataErrorCode.INVALID_METADATA,
        )
    if require_https and parsed.scheme != "https":
        raise MarketplaceMetadataError(
            "HTTPS required for marketplace metadata URL",
            error_code=MetadataErrorCode.INVALID_METADATA,
        )
    if not parsed.netloc:
        raise MarketplaceMetadataError(
            "Invalid marketplace metadata URL",
            error_code=MetadataErrorCode.INVALID_METADATA,
        )
    return url.rstrip("/") + "/"


def map_sync_exception(exc: Exception) -> MarketplaceSyncResult:
    if isinstance(exc, MarketplaceMetadataError):
        return MarketplaceSyncResult(
            outcome=SyncOutcome.REJECTED,
            message=str(exc),
            error_code=exc.error_code,
            error_category=exc.error_code.value if exc.error_code else exc.__class__.__name__,
        )
    if isinstance(exc, DownloadHTTPError):
        return MarketplaceSyncResult(
            outcome=SyncOutcome.REJECTED,
            message=str(exc),
            error_code=MetadataErrorCode.HTTP_ERROR,
            error_category=MetadataErrorCode.HTTP_ERROR.value,
        )
    if isinstance(exc, DownloadError):
        message = str(exc)
        code = MetadataErrorCode.INVALID_METADATA
        if "exceeds" in message.lower():
            code = MetadataErrorCode.SIZE_LIMIT_EXCEEDED
        return MarketplaceSyncResult(
            outcome=SyncOutcome.REJECTED,
            message=message,
            error_code=code,
            error_category=code.value,
        )
    if isinstance(exc, RepositoryError):
        message = str(exc)
        code = MetadataErrorCode.INVALID_SIGNATURE
        lowered = message.lower()
        if "expired" in lowered:
            code = MetadataErrorCode.EXPIRED_METADATA
        elif "rollback" in lowered or "insufficient" in lowered:
            code = MetadataErrorCode.METADATA_ROLLBACK_DETECTED
        elif "root" in lowered:
            code = MetadataErrorCode.UNKNOWN_ROOT
        return MarketplaceSyncResult(
            outcome=SyncOutcome.REJECTED,
            message=message,
            error_code=code,
            error_category=code.value,
        )
    if isinstance(exc, OSError):
        return MarketplaceSyncResult(
            outcome=SyncOutcome.FAILED,
            message=str(exc),
            error_code=MetadataErrorCode.NETWORK_ERROR,
            error_category=MetadataErrorCode.NETWORK_ERROR.value,
        )
    return MarketplaceSyncResult(
        outcome=SyncOutcome.FAILED,
        message=str(exc),
        error_code=MetadataErrorCode.INVALID_METADATA,
        error_category=MetadataErrorCode.INVALID_METADATA.value,
    )


class MarketplaceMetadataClient:
    """Verify TUF metadata chain and fetch allowed metadata JSON targets only."""

    def __init__(
        self,
        *,
        metadata_base_url: str,
        targets_base_url: str,
        pinned_root_bytes: bytes,
        require_https: bool = True,
        max_metadata_bytes: int = 1_048_576,
        connect_timeout: float = 5.0,
        read_timeout: float = 15.0,
        max_root_rotations: int = 2,
        tuf_state_dir: str | Path | None = None,
        fetcher_factory: Callable[..., HttpxFetcher] | None = None,
    ) -> None:
        self._metadata_base_url = validate_metadata_base_url(metadata_base_url, require_https=require_https)
        self._targets_base_url = validate_metadata_base_url(targets_base_url, require_https=require_https)
        self._pinned_root_bytes = pinned_root_bytes
        self._require_https = require_https
        self._max_metadata_bytes = max_metadata_bytes
        self._connect_timeout = connect_timeout
        self._read_timeout = read_timeout
        self._max_root_rotations = max_root_rotations
        self._tuf_state_dir = Path(tuf_state_dir) if tuf_state_dir else None
        self._fetcher_factory = fetcher_factory or HttpxFetcher

    def sync_metadata(self) -> MarketplaceSyncResult:
        fetcher = self._fetcher_factory(
            require_https=self._require_https,
            max_bytes=self._max_metadata_bytes,
            connect_timeout=self._connect_timeout,
            read_timeout=self._read_timeout,
        )
        metadata_dir = self._resolve_metadata_dir()
        target_dir = metadata_dir / "targets"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            config = UpdaterConfig(
                max_root_rotations=self._max_root_rotations,
                root_max_length=self._max_metadata_bytes,
                timestamp_max_length=65536,
                snapshot_max_length=65536,
                targets_max_length=self._max_metadata_bytes,
            )
            updater = Updater(
                str(metadata_dir),
                self._metadata_base_url,
                target_dir=str(target_dir),
                target_base_url=self._targets_base_url,
                fetcher=fetcher,
                config=config,
                bootstrap=self._pinned_root_bytes,
            )
            updater.refresh()

            catalog = self._download_metadata_target(updater, CATALOG_TARGET_PATH)
            revocations = self._download_metadata_target(updater, REVOCATIONS_TARGET_PATH)
            advisories = self._try_download_metadata_target(updater, ADVISORIES_TARGET_PATH)
            versions = self._read_versions(metadata_dir)
            expires = self._read_expiry(metadata_dir)

            return MarketplaceSyncResult(
                outcome=SyncOutcome.SUCCESS,
                message="Metadata sync succeeded",
                versions=versions,
                catalog=catalog,
                revocations=revocations,
                advisories=advisories,
                metadata_expires_at=expires,
            )
        except Exception as exc:
            logger.warning("Marketplace metadata rejected: %s", exc)
            return map_sync_exception(exc)
        finally:
            fetcher.close()

    def _resolve_metadata_dir(self) -> Path:
        if self._tuf_state_dir is not None:
            return self._tuf_state_dir
        return Path.cwd() / ".emic-marketplace-tuf"

    @staticmethod
    def _read_versions(metadata_dir: Path) -> MarketplaceMetadataVersions:
        root_md = Metadata[Root].from_file(str(metadata_dir / "root.json"))
        ts_md = Metadata[Timestamp].from_file(str(metadata_dir / "timestamp.json"))
        snap_md = Metadata[Snapshot].from_file(str(metadata_dir / "snapshot.json"))
        tgt_md = Metadata[Targets].from_file(str(metadata_dir / "targets.json"))
        return MarketplaceMetadataVersions(
            root_version=root_md.signed.version,
            timestamp_version=ts_md.signed.version,
            snapshot_version=snap_md.signed.version,
            targets_version=tgt_md.signed.version,
        )

    @staticmethod
    def _read_expiry(metadata_dir: Path) -> datetime:
        root_md = Metadata[Root].from_file(str(metadata_dir / "root.json"))
        ts_md = Metadata[Timestamp].from_file(str(metadata_dir / "timestamp.json"))
        snap_md = Metadata[Snapshot].from_file(str(metadata_dir / "snapshot.json"))
        tgt_md = Metadata[Targets].from_file(str(metadata_dir / "targets.json"))
        return min(
            root_md.signed.expires,
            ts_md.signed.expires,
            snap_md.signed.expires,
            tgt_md.signed.expires,
        )

    @staticmethod
    def _try_download_metadata_target(updater: Updater, target_path: str) -> dict[str, Any] | None:
        try:
            return MarketplaceMetadataClient._download_metadata_target(updater, target_path)
        except MarketplaceMetadataError:
            return None

    @staticmethod
    def _download_metadata_target(updater: Updater, target_path: str) -> dict[str, Any]:
        if target_path not in ALLOWED_METADATA_TARGETS:
            raise MarketplaceMetadataError(f"Target path not allowed: {target_path}")
        target_info = updater.get_targetinfo(target_path)
        if target_info is None:
            raise MarketplaceMetadataError(f"Missing metadata target: {target_path}")
        filepath = updater.download_target(target_info)
        raw = Path(filepath).read_bytes()
        return json.loads(raw.decode("utf-8"))

    @staticmethod
    def load_pinned_root(path: str | Path) -> bytes:
        root_path = Path(path)
        if not root_path.is_file():
            raise MarketplaceMetadataError(f"Pinned root not found: {root_path}")
        return root_path.read_bytes()
