"""Remote artifact distribution types (Step 5C.3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class ArtifactSourceType(StrEnum):
    LOCAL = "LOCAL"
    INTERNAL = "INTERNAL"
    ORG = "ORG"
    PUBLIC = "PUBLIC"


class ArtifactState(StrEnum):
    DISCOVERED = "DISCOVERED"
    DOWNLOAD_PENDING = "DOWNLOAD_PENDING"
    DOWNLOADING = "DOWNLOADING"
    DOWNLOADED = "DOWNLOADED"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    POLICY_REVIEW = "POLICY_REVIEW"
    STAGED = "STAGED"
    QUARANTINED = "QUARANTINED"
    REJECTED = "REJECTED"


class DistributionErrorCode(StrEnum):
    ARTIFACT_NOT_FOUND = "ARTIFACT_NOT_FOUND"
    ARTIFACT_DIGEST_MISMATCH = "ARTIFACT_DIGEST_MISMATCH"
    ARTIFACT_SIZE_MISMATCH = "ARTIFACT_SIZE_MISMATCH"
    ARTIFACT_SOURCE_FORBIDDEN = "ARTIFACT_SOURCE_FORBIDDEN"
    ARTIFACT_REDIRECT_REJECTED = "ARTIFACT_REDIRECT_REJECTED"
    ARTIFACT_SSRF_BLOCKED = "ARTIFACT_SSRF_BLOCKED"
    ARTIFACT_URL_INVALID = "ARTIFACT_URL_INVALID"
    CATALOG_ENTRY_NOT_FOUND = "CATALOG_ENTRY_NOT_FOUND"
    PACKAGE_SIGNATURE_INVALID = "PACKAGE_SIGNATURE_INVALID"
    PACKAGE_IDENTITY_MISMATCH = "PACKAGE_IDENTITY_MISMATCH"
    OWNERSHIP_MISMATCH = "OWNERSHIP_MISMATCH"
    NAMESPACE_SHADOWING = "NAMESPACE_SHADOWING"
    DOWNLOAD_TIMEOUT = "DOWNLOAD_TIMEOUT"
    DOWNLOAD_SIZE_EXCEEDED = "DOWNLOAD_SIZE_EXCEEDED"
    POLICY_DENIED = "POLICY_DENIED"
    CACHE_CORRUPT = "CACHE_CORRUPT"
    CONCURRENT_FETCH = "CONCURRENT_FETCH"
    STAGING_FAILED = "STAGING_FAILED"


class DistributionError(Exception):
    def __init__(self, message: str, *, code: DistributionErrorCode) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class SbomReference:
    url: str | None = None
    sha256: str | None = None
    format: str = "CycloneDX"
    embedded: bool = False


@dataclass(frozen=True, slots=True)
class ArtifactDescriptor:
    module_id: str
    publisher_id: str
    version: str
    release_id: str
    artifact_url: str
    content_sha256: str
    artifact_size: int | None
    source: ArtifactSourceType
    sbom_reference: SbomReference | None = None
    published_at: str | None = None
    package_format: str = "emicpkg"
    catalog_version: int | None = None


@dataclass(frozen=True, slots=True)
class DownloadResult:
    path: str
    sha256: str
    bytes_downloaded: int
    from_cache: bool = False


@dataclass(frozen=True, slots=True)
class StagingResult:
    artifact_id: int
    state: ArtifactState
    reason_codes: tuple[str, ...] = ()
    security_status: str | None = None
    policy_decision: str | None = None
    message: str = ""


@dataclass
class ArtifactProvenance:
    publisher_id: str
    module_id: str
    version: str
    release_id: str
    artifact_digest: str
    source: str
    catalog_metadata_version: int | None = None
    download_timestamp: datetime | None = None
    signature_key_id: str | None = None
    sbom_digest: str | None = None
    security_evaluation_timestamp: datetime | None = None
    extra: dict[str, Any] = field(default_factory=dict)
