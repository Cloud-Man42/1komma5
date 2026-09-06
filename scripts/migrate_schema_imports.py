#!/usr/bin/env python3
"""Rewrite barrel `from app.schemas import ...` to domain-specific imports."""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT / "backend" / "app" / "schemas"
TARGET_DIRS = [ROOT / "backend" / "app", ROOT / "backend" / "tests"]


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


def _extract_import_blocks(text: str) -> list[tuple[int, int, list[str]]]:
    pattern = re.compile(
        r"^from app\.schemas import\s*(?:\((?P<paren>[\s\S]*?)\)|(?P<single>[^\n]+))\s*$",
        re.MULTILINE,
    )
    blocks: list[tuple[int, int, list[str]]] = []
    for match in pattern.finditer(text):
        body = match.group("paren") or match.group("single") or ""
        symbols = [part.strip() for part in body.replace("\n", " ").split(",") if part.strip()]
        blocks.append((match.start(), match.end(), symbols))
    return blocks


def _rewrite_file(path: Path, symbol_modules: dict[str, str]) -> bool:
    text = path.read_text(encoding="utf-8")
    blocks = _extract_import_blocks(text)
    if not blocks:
        return False
    for start, end, symbols in reversed(blocks):
        grouped: dict[str, list[str]] = defaultdict(list)
        missing = [symbol for symbol in symbols if symbol not in symbol_modules]
        if missing:
            raise RuntimeError(f"{path}: unknown schema symbols {missing}")
        for symbol in symbols:
            grouped[symbol_modules[symbol]].append(symbol)
        replacement = "\n".join(
            f"from {module} import {', '.join(sorted(names))}"
            for module, names in sorted(grouped.items())
        )
        text = text[:start] + replacement + text[end:]
    path.write_text(text, encoding="utf-8")
    return True


def main() -> None:
    symbol_modules = _collect_symbol_modules()
    for target_dir in TARGET_DIRS:
        for path in target_dir.rglob("*.py"):
            if _rewrite_file(path, symbol_modules):
                print(f"updated {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
    print("done")
