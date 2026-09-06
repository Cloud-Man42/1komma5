#!/usr/bin/env python3
"""Repair orphaned multiline schema import tails."""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT / "backend" / "app" / "schemas"
AFFECTED = [
    ROOT / "backend" / "app" / "dashboard_compute.py",
    * (ROOT / "backend" / "app" / "api").glob("*.py"),
    ROOT / "backend" / "tests" / "test_solar_forecast_snapshot_api.py",
]

ORPHAN_BLOCK = re.compile(
    r"(?:^[ \t]+([A-Z][A-Za-z0-9_]*),?[ \t]*\r?\n)+^\)[ \t]*\r?\n",
    re.MULTILINE,
)


def _collect_symbol_modules() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for path in sorted(SCHEMAS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        module = f"app.schemas.{path.stem}"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                mapping[node.name] = module
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        mapping[target.id] = module
    return mapping


def _replace_block(match: re.Match[str], symbol_modules: dict[str, str]) -> str:
    block = match.group(0)
    symbols = re.findall(r"^[ \t]+([A-Z][A-Za-z0-9_]*)", block, re.MULTILINE)
    if not symbols or any(symbol not in symbol_modules for symbol in symbols):
        return block
    grouped: dict[str, list[str]] = defaultdict(list)
    for symbol in symbols:
        grouped[symbol_modules[symbol]].append(symbol)
    lines = [f"from {module} import {', '.join(sorted(names))}" for module, names in sorted(grouped.items())]
    return "\n".join(lines) + "\n"


def _repair_file(path: Path, symbol_modules: dict[str, str]) -> bool:
    text = path.read_text(encoding="utf-8")
    if not ORPHAN_BLOCK.search(text):
        return False
    new_text = ORPHAN_BLOCK.sub(lambda match: _replace_block(match, symbol_modules), text)
    path.write_text(new_text, encoding="utf-8")
    return True


def main() -> None:
    symbol_modules = _collect_symbol_modules()
    for path in AFFECTED:
        if path.exists() and _repair_file(path, symbol_modules):
            print(f"repaired {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
