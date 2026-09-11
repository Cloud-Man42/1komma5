"""Internal trusted package catalog (local files only)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from energy_core.config import Settings


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    entry_id: str
    module_id: str
    name: str
    version: str
    publisher: str
    description: str
    package_filename: str
    trusted: bool = True


def list_catalog_entries(settings: Settings) -> tuple[CatalogEntry, ...]:
    catalog_dir = Path(settings.resolved_catalog_path())
    manifest_path = catalog_dir / "catalog.json"
    if not manifest_path.exists():
        return ()
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries: list[CatalogEntry] = []
    for item in raw.get("entries", []):
        filename = str(item["package_filename"])
        package_path = catalog_dir / filename
        if not package_path.exists():
            continue
        entries.append(
            CatalogEntry(
                entry_id=str(item["entry_id"]),
                module_id=str(item["module_id"]),
                name=str(item.get("name", item["module_id"])),
                version=str(item["version"]),
                publisher=str(item.get("publisher", "emic-internal")),
                description=str(item.get("description", "")),
                package_filename=filename,
                trusted=bool(item.get("trusted", True)),
            )
        )
    return tuple(entries)


def resolve_catalog_package(settings: Settings, entry_id: str) -> Path | None:
    for entry in list_catalog_entries(settings):
        if entry.entry_id == entry_id:
            path = Path(settings.resolved_catalog_path()) / entry.package_filename
            return path if path.exists() else None
    return None
