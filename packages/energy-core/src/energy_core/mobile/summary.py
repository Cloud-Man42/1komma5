"""Mobile PWA summary helpers — warnings and quick actions on top of multi-site overview."""

from __future__ import annotations

from typing import Any

from energy_core.auth.permissions import PERMISSION_ALL
from energy_core.auth.principal import Principal
from energy_core.multi_site.models import MultiSiteOverview, SiteOverviewEntry


def build_warnings(sites: tuple[SiteOverviewEntry, ...]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for site in sites:
        if site.health == "offline":
            warnings.append(
                {
                    "slug": site.slug,
                    "name": site.name,
                    "severity": "critical",
                    "message": site.health_detail or site.error or "Offline",
                }
            )
        elif site.health == "degraded":
            warnings.append(
                {
                    "slug": site.slug,
                    "name": site.name,
                    "severity": "warning",
                    "message": site.health_detail or "Degraded",
                }
            )
        if site.is_stale and site.health == "healthy":
            age = site.data_age_seconds
            label = f"Data {age // 60} min old" if age and age >= 60 else "Data delayed"
            warnings.append(
                {
                    "slug": site.slug,
                    "name": site.name,
                    "severity": "warning",
                    "message": label,
                }
            )
        if site.ev_state and "waiting" in site.ev_state.lower():
            warnings.append(
                {
                    "slug": site.slug,
                    "name": site.name,
                    "severity": "info",
                    "message": "Vehicle connected — not charging",
                    "category": "charging",
                }
            )
    return warnings


def build_quick_actions(principal: Principal) -> list[dict[str, str]]:
    perms = set(principal.permissions)

    def allowed(code: str) -> bool:
        return PERMISSION_ALL in perms or code in perms

    actions: list[dict[str, str]] = []
    if allowed("charging.read"):
        actions.append({"id": "charging", "label": "Smart charging", "route": "/app/control"})
    if allowed("dashboard.read"):
        actions.append({"id": "battery", "label": "Battery", "route": "/app/energy"})
    if allowed("spa.read"):
        actions.append({"id": "spa", "label": "SPA", "route": "/app/control"})
    actions.append({"id": "sites", "label": "Sites", "route": "/app/sites"})
    return actions


def freshness_label(overview: MultiSiteOverview) -> str:
    age = overview.freshness.max_data_age_seconds
    if age is None:
        return "Unknown"
    if age <= 60:
        return "Live"
    if age <= 300:
        return f"Updated {age}s ago"
    if age < 3600:
        return f"Stale · {age // 60} min old"
    return f"Stale · {age // 3600}h old"


def build_mobile_summary(overview: MultiSiteOverview, principal: Principal) -> dict[str, Any]:
    base = overview.to_dict()
    base["freshnessLabel"] = freshness_label(overview)
    base["warnings"] = build_warnings(overview.sites)
    base["quickActions"] = build_quick_actions(principal)
    return base
