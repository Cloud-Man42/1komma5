"""Debug Sensibo package verification on production."""

from __future__ import annotations

import asyncio
import json
import traceback
import zipfile
from pathlib import Path

from energy_core.config import get_settings
from energy_core.db.installed_package_repo import InstalledPackageRepository
from energy_core.db.session import create_engine, create_session_factory
from energy_core.platform.modules.packages.loader import _include_in_verify_archive, _verify_installed_package
from energy_core.platform.modules.packages.trust_store import PublisherTrustStore


async def main() -> int:
    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        row = await InstalledPackageRepository(session).get("integration.sensibo")
        if row is None:
            print(json.dumps({"error": "missing"}))
            return 1
        trust = PublisherTrustStore(session)
        try:
            verified = await _verify_installed_package(row, trust, allow_unsigned=settings.emic_allow_unsigned_modules)
            print(json.dumps({"verified": verified is not None, "package_state": row.package_state, "path": row.package_path}))
        except Exception as exc:
            print(json.dumps({"verified": False, "error": str(exc), "trace": traceback.format_exc()}))
    await engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
