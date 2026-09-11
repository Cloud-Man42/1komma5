#!/usr/bin/env python3
"""Apply Sensibo package update on prod using trusted fixture path."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from energy_core.config import Settings
from energy_core.db.session import create_engine, create_session_factory
from energy_core.platform.modules.packages.updater import PackageUpdater


async def main() -> int:
    archive = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "/app/sprint-b-fixtures/integration.sensibo-1.0.0.emicpkg"
    )
    if not archive.exists():
        print(f"archive missing: {archive}")
        return 1

    settings = Settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        result = await PackageUpdater(session, settings).update("integration.sensibo", archive)
        print(
            "UPDATE_OK",
            result.module_id,
            result.installed_version,
            result.package_state,
            result.message,
        )
    await engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
