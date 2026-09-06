"""Solar site configuration validation for forecast read paths."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from energy_core.db.solar_forecast_repo import SolarSiteConfigRepository
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class SolarSiteConfigIssue:
    status_code: int
    detail: str


def solar_site_config_issue(record: Any | None) -> SolarSiteConfigIssue | None:
    """Return a config problem for API layers, or None when the site is ready."""
    if record is None or not record.enabled:
        return SolarSiteConfigIssue(
            status_code=404,
            detail=(
                "Solprognos är inte aktiverad. Gå till Inställningar → Anläggningar, "
                "fyll i koordinater och kWp, och aktivera prognosen."
            ),
        )
    if (
        record.latitude is None
        or record.longitude is None
        or record.installed_peak_power_kw is None
        or record.installed_peak_power_kw <= 0
    ):
        return SolarSiteConfigIssue(
            status_code=404,
            detail=(
                "Solprofilen är ofullständig. Ange latitud, longitud och installerad effekt (kWp) "
                "under Inställningar → Anläggningar."
            ),
        )
    return None


async def load_solar_site_config(session: AsyncSession, site) -> tuple[Any | None, SolarSiteConfigIssue | None]:
    repo = SolarSiteConfigRepository(session)
    record = await repo.get(site.id, timezone=site.timezone)
    return record, solar_site_config_issue(record)
