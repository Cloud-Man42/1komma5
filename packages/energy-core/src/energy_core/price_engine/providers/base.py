"""Price provider protocol definitions."""

from __future__ import annotations

from typing import Protocol

from energy_core.price_engine.types import RawPricePoint


class IMarketPriceProvider(Protocol):
    async def fetch(
        self,
        *,
        system_id: str,
        from_iso: str,
        to_iso: str,
        resolution: str = "15m",
    ) -> tuple[RawPricePoint, ...]: ...


class IImportPriceProvider(Protocol):
    async def fetch(
        self,
        *,
        system_id: str,
        from_iso: str,
        to_iso: str,
        resolution: str = "15m",
    ) -> tuple[RawPricePoint, ...]: ...


class IExportPriceProvider(Protocol):
    async def fetch(
        self,
        *,
        system_id: str,
        from_iso: str,
        to_iso: str,
        sell_config: object,
    ) -> tuple[RawPricePoint, ...]: ...
