"""Vendor-neutral mock price provider."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from energy_core.price_engine.types import RawPricePoint


@dataclass
class MockPriceProvider:
    points: list[RawPricePoint] = field(default_factory=list)

    async def fetch(
        self,
        *,
        system_id: str,
        from_iso: str,
        to_iso: str,
        resolution: str = "15m",
    ) -> tuple[RawPricePoint, ...]:
        if self.points:
            return tuple(self.points)
        now = datetime.now(UTC)
        resolution_minutes = 15 if resolution == "15m" else 60
        return (
            RawPricePoint(
                timestamp=now,
                market_price_eur_kwh=0.12,
                import_price_eur_kwh=0.15,
                export_price_eur_kwh=0.05,
                native_resolution_minutes=resolution_minutes,
                components={"system_id": system_id, "from": from_iso, "to": to_iso},
            ),
        )
