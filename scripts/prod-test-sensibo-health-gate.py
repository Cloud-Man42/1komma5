#!/usr/bin/env python3
"""One-off prod health gate check for Sensibo package."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

from energy_core.config import Settings
from energy_core.platform.modules.packages.extractor import PackageExtractor
from energy_core.platform.modules.packages.health_gate import evaluate_package_health
from energy_core.platform.modules.packages.paths import ModulePackagePaths

archive = Path("/app/sprint-b-fixtures/integration.sensibo-1.0.0.emicpkg")
if not archive.exists():
    archive = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/integration.sensibo-1.0.0.emicpkg")

print("archive", archive, "exists", archive.exists())
with zipfile.ZipFile(archive) as zf:
    module_src = zf.read("module/module.py").decode()
print("health_gate_fix", "_health_gate_only" in module_src)

settings = Settings()
paths = ModulePackagePaths(settings.resolved_modules_path())
staging = paths.staging_dir("integration.sensibo", "1.0.0")
PackageExtractor(paths).extract(archive, staging)
evaluate_package_health(staging)
print("HEALTH_GATE_OK")
