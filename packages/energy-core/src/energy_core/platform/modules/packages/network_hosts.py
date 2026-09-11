"""Manifest network_hosts validation."""

from __future__ import annotations

import re

from energy_core.platform.modules.packages.errors import INVALID_MANIFEST, PackageError

_HOST_PATTERN = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$",
    re.IGNORECASE,
)


def validate_network_hosts(hosts: tuple[str, ...]) -> None:
    for host in hosts:
        normalized = host.strip().lower()
        if not normalized:
            raise PackageError("network_hosts entries must be non-empty", code=INVALID_MANIFEST)
        if "*" in normalized or "?" in normalized or normalized.startswith("."):
            raise PackageError("network_hosts wildcards are not allowed", code=INVALID_MANIFEST)
        if normalized.startswith("http://") or normalized.startswith("https://"):
            raise PackageError("network_hosts must be hostnames only", code=INVALID_MANIFEST)
        if not _HOST_PATTERN.match(normalized):
            raise PackageError(f"invalid network_hosts entry: {host}", code=INVALID_MANIFEST)
