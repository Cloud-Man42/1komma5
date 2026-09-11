"""ZIP archive safety guards."""

from __future__ import annotations

import zipfile
from pathlib import Path

from energy_core.platform.modules.packages.errors import PACKAGE_TOO_LARGE, PackageError


def inspect_archive_limits(
    archive_path: Path,
    *,
    max_entries: int = 10_000,
    max_uncompressed_bytes: int = 200_000_000,
    max_compression_ratio: float = 200.0,
) -> None:
    total_uncompressed = 0
    with zipfile.ZipFile(archive_path, "r") as zf:
        if len(zf.infolist()) > max_entries:
            raise PackageError("too many archive entries", code=PACKAGE_TOO_LARGE)
        for info in zf.infolist():
            if info.is_dir():
                continue
            total_uncompressed += info.file_size
            if info.file_size > 0 and info.compress_size > 0:
                ratio = info.file_size / max(info.compress_size, 1)
                if ratio > max_compression_ratio:
                    raise PackageError("archive compression ratio too high", code=PACKAGE_TOO_LARGE)
            if ".." in info.filename or info.filename.startswith(("/", "\\")):
                from energy_core.platform.modules.packages.errors import PATH_TRAVERSAL

                raise PackageError("unsafe archive path", code=PATH_TRAVERSAL)
        if total_uncompressed > max_uncompressed_bytes:
            raise PackageError("archive uncompressed size too large", code=PACKAGE_TOO_LARGE)
