"""Safe ZIP extraction for .emicpkg archives."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from energy_core.platform.modules.packages.errors import PATH_TRAVERSAL, PackageError
from energy_core.platform.modules.packages.paths import ModulePackagePaths


class PackageExtractor:
    def __init__(self, paths: ModulePackagePaths) -> None:
        self._paths = paths

    def extract(self, archive_path: Path, target_dir: Path) -> None:
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_path, "r") as zf:
            for member in zf.namelist():
                if member.endswith("/"):
                    continue
                try:
                    dest = ModulePackagePaths.safe_join(target_dir, member)
                except ValueError as exc:
                    raise PackageError(str(exc), code=PATH_TRAVERSAL) from exc
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, dest.open("wb") as out:
                    shutil.copyfileobj(src, out)
