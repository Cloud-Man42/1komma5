"""Reconcile installed Sensibo package checksum on production."""

from __future__ import annotations

import asyncio
import json
import zipfile
from pathlib import Path

from sqlalchemy import select

from energy_core.config import get_settings
from energy_core.db.installed_package_repo import InstalledPackageRepository
from energy_core.db.models import Base
from energy_core.db.session import create_engine, create_session_factory
from energy_core.platform.modules.packages.integrity import compute_package_content_sha256
from energy_core.platform.modules.packages.loader import _include_in_verify_archive
from energy_core.platform.modules.packages.types import PackageState


async def main() -> int:
    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        row = await InstalledPackageRepository(session).get("integration.sensibo")
        if row is None:
            print(json.dumps({"error": "not installed"}))
            return 1
        package_dir = Path(row.package_path)
        buffer_zip = package_dir.parent / ".verify-reconcile.zip"
        with zipfile.ZipFile(buffer_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(package_dir.rglob("*")):
                if path.is_file():
                    rel = path.relative_to(package_dir).as_posix()
                    if not _include_in_verify_archive(rel):
                        continue
                    zf.write(path, rel)
        digest = compute_package_content_sha256(buffer_zip)
        buffer_zip.unlink(missing_ok=True)
        row.checksum_sha256 = digest
        row.package_state = PackageState.INSTALLED.value
        await session.commit()
        print(json.dumps({"module_id": row.module_id, "checksum_sha256": digest, "package_state": row.package_state}))
    await engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
