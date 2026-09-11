"""Config migration hooks for packaged modules."""

from __future__ import annotations

from typing import Any, Protocol


class ModuleMigration(Protocol):
    def upgrade(
        self,
        *,
        from_version: str,
        to_version: str,
        session: Any,
    ) -> None: ...

    def downgrade(
        self,
        *,
        from_version: str,
        to_version: str,
        session: Any,
    ) -> None: ...
