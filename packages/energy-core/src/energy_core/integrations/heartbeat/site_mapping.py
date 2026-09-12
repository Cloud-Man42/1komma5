"""Resolve Heartbeat external IDs from EMIC site records."""

from __future__ import annotations

from energy_core.db.models import SiteModel


def resolve_heartbeat_system_id(site: SiteModel) -> str | None:
    """Canonical system UUID for Heartbeat API calls."""
    for value in (site.heartbeat_system_id, site.external_system_id):
        if value and str(value).strip():
            return str(value).strip()
    return None


def sync_external_system_id_alias(site: SiteModel) -> None:
    """Keep legacy external_system_id aligned with heartbeat_system_id when set."""
    system_id = (site.heartbeat_system_id or "").strip() or None
    if system_id:
        site.external_system_id = system_id
