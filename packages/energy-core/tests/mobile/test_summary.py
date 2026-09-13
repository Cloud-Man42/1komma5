from datetime import UTC, datetime

from energy_core.auth.permissions import PERMISSION_ALL
from energy_core.auth.principal import AuthMethod, Principal
from energy_core.mobile.summary import build_mobile_summary, build_quick_actions, build_warnings
from energy_core.multi_site.models import (
    CurrencyAmount,
    DataQualitySummary,
    FreshnessSummary,
    MultiSiteAggregate,
    MultiSiteHealth,
    MultiSiteOverview,
    SiteOverviewEntry,
)


def _site(**kwargs) -> SiteOverviewEntry:
    defaults = {
        "slug": "akarp",
        "name": "Åkarp",
        "timezone": "Europe/Stockholm",
        "currency": "SEK",
        "price_area": "SE3",
        "available": True,
        "health": "healthy",
        "health_detail": None,
        "updated_at": datetime.now(UTC),
        "data_age_seconds": 20,
        "is_stale": False,
        "solar_power_kw": 4.8,
        "consumption_power_kw": 3.2,
        "grid_import_power_kw": 0.0,
        "grid_export_power_kw": 1.1,
        "battery_soc_percent": 82.0,
        "battery_power_kw": 0.0,
        "battery_capacity_kwh": 15.0,
        "battery_stored_kwh": 12.3,
        "battery_state": "idle",
        "solar_today_kwh": 21.4,
        "consumption_today_kwh": 17.2,
        "grid_import_today_kwh": 0.0,
        "grid_export_today_kwh": 2.0,
        "battery_charged_today_kwh": 1.0,
        "battery_discharged_today_kwh": 0.5,
        "cost_today": 112.0,
        "savings_today": 20.0,
        "ev_power_kw": None,
        "ev_state": None,
        "error": None,
    }
    defaults.update(kwargs)
    return SiteOverviewEntry(**defaults)


def _overview(sites: list[SiteOverviewEntry]) -> MultiSiteOverview:
    return MultiSiteOverview(
        sites=tuple(sites),
        aggregate=MultiSiteAggregate(
            solar_power_kw=4.8,
            consumption_power_kw=3.2,
            grid_import_power_kw=0.0,
            grid_export_power_kw=1.1,
            grid_net_power_kw=1.1,
            battery_charge_power_kw=None,
            battery_discharge_power_kw=None,
            battery_capacity_kwh=15.0,
            battery_stored_kwh=12.3,
            battery_soc_percent=82.0,
            solar_today_kwh=21.4,
            consumption_today_kwh=17.2,
            grid_import_today_kwh=0.0,
            grid_export_today_kwh=2.0,
            battery_charged_today_kwh=1.0,
            battery_discharged_today_kwh=0.5,
            ev_power_kw=None,
            self_consumption_percent=None,
            self_sufficiency_percent=None,
            best_solar_site_slug="akarp",
            best_solar_site_kwh=21.4,
            highest_load_site_slug="akarp",
            highest_load_site_kw=3.2,
        ),
        health=MultiSiteHealth(healthy=1, degraded=0, offline=0),
        data_quality=DataQualitySummary(
            partial=False,
            sites_requested=1,
            sites_available=1,
            sites_stale=0,
            message=None,
        ),
        freshness=FreshnessSummary(
            freshest_at=datetime.now(UTC),
            oldest_at=datetime.now(UTC),
            max_data_age_seconds=20,
        ),
        currencies=(CurrencyAmount(currency="SEK", cost_today=112.0, savings_today=20.0),),
        generated_at=datetime.now(UTC),
    )


def test_build_warnings_offline_and_charging():
    sites = (
        _site(health="offline", health_detail="Heartbeat unreachable"),
        _site(slug="denmark", name="Danmark", ev_state="WAITING_TO_START"),
    )
    warnings = build_warnings(sites)
    assert any(w["severity"] == "critical" for w in warnings)
    assert any(w.get("category") == "charging" for w in warnings)


def _principal(**kwargs) -> Principal:
    defaults = {
        "user_id": 1,
        "username": "test",
        "email": "test@example.com",
        "display_name": "Test",
        "roles": frozenset({"OPERATOR"}),
        "permissions": frozenset({PERMISSION_ALL}),
        "site_ids": frozenset({1, 2}),
        "auth_method": AuthMethod.SESSION,
    }
    defaults.update(kwargs)
    return Principal(**defaults)


def test_build_quick_actions_respects_permissions():
    viewer = _principal(permissions=frozenset({"dashboard.read", "spa.read"}))
    actions = build_quick_actions(viewer)
    ids = {a["id"] for a in actions}
    assert "spa" in ids
    assert "charging" not in ids


def test_build_mobile_summary_includes_freshness_label():
    principal = _principal()
    payload = build_mobile_summary(_overview([_site()]), principal)
    assert payload["freshnessLabel"] == "Live"
    assert "warnings" in payload
    assert "quickActions" in payload
