"""Resolve trusted catalog releases from TUF trust cache."""

from __future__ import annotations

import json
from typing import Any

from energy_core.platform.modules.distribution.types import (
    ArtifactDescriptor,
    ArtifactSourceType,
    DistributionError,
    DistributionErrorCode,
    SbomReference,
)
from energy_core.platform.modules.packages.paths import is_protected_module_id


def _parse_sbom_ref(raw: Any) -> SbomReference | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        return SbomReference(url=raw)
    if isinstance(raw, dict):
        return SbomReference(
            url=raw.get("url"),
            sha256=raw.get("sha256") or raw.get("content_sha256"),
            format=str(raw.get("format", "CycloneDX")),
            embedded=bool(raw.get("embedded", False)),
        )
    return None


class CatalogReleaseResolver:
    """Resolve artifact descriptors only from trusted catalog JSON."""

    def __init__(self, catalog: dict[str, Any] | None, *, source: ArtifactSourceType = ArtifactSourceType.PUBLIC) -> None:
        self._catalog = catalog or {}
        raw_source = self._catalog.get("artifact_source")
        if isinstance(raw_source, str):
            try:
                source = ArtifactSourceType(raw_source.upper())
            except ValueError:
                pass
        self._source = source
        self._version = int(self._catalog.get("snapshot", {}).get("version", 0))

    def list_modules(self) -> list[dict[str, Any]]:
        modules = self._catalog.get("modules", {})
        if not isinstance(modules, dict):
            return []
        result: list[dict[str, Any]] = []
        for module_id, entry in modules.items():
            if not isinstance(entry, dict):
                continue
            publisher_id = entry.get("publisher_id", "")
            releases = self._release_map(entry)
            for version, rel in releases.items():
                result.append(
                    {
                        "module_id": module_id,
                        "publisher_id": rel.get("publisher_id", publisher_id),
                        "version": version,
                        "release_id": rel.get("release_id", f"{module_id}@{version}"),
                        "content_sha256": rel.get("content_sha256"),
                        "artifact_size": rel.get("artifact_size"),
                        "source": self._source.value,
                    }
                )
        return result

    def resolve(self, module_id: str, version: str) -> ArtifactDescriptor:
        if is_protected_module_id(module_id):
            raise DistributionError(
                f"Protected module namespace cannot be resolved from public catalog: {module_id}",
                code=DistributionErrorCode.NAMESPACE_SHADOWING,
            )
        modules = self._catalog.get("modules", {})
        if not isinstance(modules, dict):
            raise DistributionError("Invalid catalog", code=DistributionErrorCode.CATALOG_ENTRY_NOT_FOUND)
        entry = modules.get(module_id)
        if not isinstance(entry, dict):
            raise DistributionError(
                f"Module not in trusted catalog: {module_id}",
                code=DistributionErrorCode.CATALOG_ENTRY_NOT_FOUND,
            )
        releases = self._release_map(entry)
        rel = releases.get(version)
        if rel is None:
            raise DistributionError(
                f"Version {version} not in trusted catalog for {module_id}",
                code=DistributionErrorCode.CATALOG_ENTRY_NOT_FOUND,
            )
        artifact_url = rel.get("artifact_url")
        content_sha256 = rel.get("content_sha256")
        if not isinstance(artifact_url, str) or not artifact_url:
            raise DistributionError("Missing artifact_url in catalog", code=DistributionErrorCode.CATALOG_ENTRY_NOT_FOUND)
        if not isinstance(content_sha256, str) or len(content_sha256) != 64:
            raise DistributionError("Missing content_sha256 in catalog", code=DistributionErrorCode.CATALOG_ENTRY_NOT_FOUND)
        publisher_id = rel.get("publisher_id") or entry.get("publisher_id", "")
        if not publisher_id:
            raise DistributionError("Missing publisher_id in catalog", code=DistributionErrorCode.CATALOG_ENTRY_NOT_FOUND)
        size = rel.get("artifact_size")
        artifact_size = int(size) if isinstance(size, int) else None
        return ArtifactDescriptor(
            module_id=module_id,
            publisher_id=str(publisher_id),
            version=version,
            release_id=str(rel.get("release_id", f"{module_id}@{version}")),
            artifact_url=artifact_url,
            content_sha256=content_sha256.lower(),
            artifact_size=artifact_size,
            source=self._source,
            sbom_reference=_parse_sbom_ref(rel.get("sbom_ref")),
            published_at=rel.get("published_at"),
            catalog_version=self._version,
        )

    @staticmethod
    def _release_map(entry: dict[str, Any]) -> dict[str, dict[str, Any]]:
        releases = entry.get("releases")
        if isinstance(releases, dict):
            return {str(k): v for k, v in releases.items() if isinstance(v, dict)}
        latest = entry.get("latest_stable")
        if latest and isinstance(latest, str):
            inline = {
                "version": latest,
                "release_id": entry.get("release_id", f"{entry.get('module_id', '')}@{latest}"),
                "artifact_url": entry.get("artifact_url"),
                "content_sha256": entry.get("content_sha256"),
                "artifact_size": entry.get("artifact_size"),
                "publisher_id": entry.get("publisher_id"),
                "sbom_ref": entry.get("sbom_ref"),
                "published_at": entry.get("published_at"),
            }
            if inline.get("artifact_url") and inline.get("content_sha256"):
                return {latest: inline}
        return {}

    @staticmethod
    def from_cache_json(catalog_json: str | None, *, source: ArtifactSourceType = ArtifactSourceType.PUBLIC) -> CatalogReleaseResolver:
        if not catalog_json:
            return CatalogReleaseResolver({}, source=source)
        return CatalogReleaseResolver(json.loads(catalog_json), source=source)
