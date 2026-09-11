"""Runtime context passed to packaged module entrypoints."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(slots=True)
class EmicModuleContext:
    site_id: str | None
    module_id: str
    installed_version: str
    configuration: Mapping[str, Any] = field(default_factory=dict)
    services: Mapping[str, Any] = field(default_factory=dict)
