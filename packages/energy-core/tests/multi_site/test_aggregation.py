"""Multi-site aggregation math tests."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.multi_site.aggregation import aggregate_sites, weighted_battery_soc
from energy_core.multi_site.models import SiteOverviewEntry


def _site(
    slug: str,
    *,
    solar_kw: float | None = None,
    load_kw: float | None = None,
    import_kw: float | None = None,
    export_kw: float | None = None,
    cap: float | None = None,
    stored: float | None = None,
    soc: float | None = None,
    available: bool = True,
) -> SiteOverviewEntry:
    return SiteOverviewEntry(
        slug=slug,
        name=slug,
        timezone="Europe/Stockholm",
        currency="SEK",
        price_area="SE4",
        available=available,
        health="healthy" if available else "offline",
        health_detail=None,
        updated_at=datetime.now(UTC),
        data_age_seconds=30,
        is_stale=False,
        solar_power_kw=solar_kw,
        consumption_power_kw=load_kw,
        grid_import_power_kw=import_kw,
        grid_export_power_kw=export_kw,
        battery_soc_percent=soc,
        battery_power_kw=None,
        battery_capacity_kwh=cap,
        battery_stored_kwh=stored,
        battery_state=None,
        solar_today_kwh=None,
        consumption_today_kwh=None,
        grid_import_today_kwh=None,
        grid_export_today_kwh=None,
        battery_charged_today_kwh=None,
        battery_discharged_today_kwh=None,
        cost_today=None,
        savings_today=None,
        ev_power_kw=None,
        ev_state=None,
    )


def test_weighted_battery_soc_not_average():
    # Åkarp 80% of 15 kWh = 12 kWh; Danmark 50% of 10 kWh = 5 kWh
    soc = weighted_battery_soc([(15.0, 12.0), (10.0, 5.0)])
    assert soc == 68.0
    assert soc != 65.0


def test_grid_import_export_simultaneous():
    sites = [
        _site("akarp", export_kw=3.0),
        _site("denmark", import_kw=2.0),
    ]
    parts = aggregate_sites(sites)
    assert parts.aggregate.grid_import_power_kw == 2.0
    assert parts.aggregate.grid_export_power_kw == 3.0
    assert parts.aggregate.grid_net_power_kw == 1.0


def test_solar_consumption_sum():
    sites = [
        _site("akarp", solar_kw=5.0, load_kw=4.0),
        _site("denmark", solar_kw=2.0, load_kw=3.0),
    ]
    parts = aggregate_sites(sites)
    assert parts.aggregate.solar_power_kw == 7.0
    assert parts.aggregate.consumption_power_kw == 7.0


def test_currency_grouping_no_cross_sum():
    sites = [
        SiteOverviewEntry(
            slug="akarp",
            name="Åkarp",
            timezone="Europe/Stockholm",
            currency="SEK",
            price_area="SE4",
            available=True,
            health="healthy",
            health_detail=None,
            updated_at=None,
            data_age_seconds=None,
            is_stale=False,
            solar_power_kw=None,
            consumption_power_kw=None,
            grid_import_power_kw=None,
            grid_export_power_kw=None,
            battery_soc_percent=None,
            battery_power_kw=None,
            battery_capacity_kwh=None,
            battery_stored_kwh=None,
            battery_state=None,
            solar_today_kwh=None,
            consumption_today_kwh=None,
            grid_import_today_kwh=None,
            grid_export_today_kwh=None,
            battery_charged_today_kwh=None,
            battery_discharged_today_kwh=None,
            cost_today=100.0,
            savings_today=20.0,
            ev_power_kw=None,
            ev_state=None,
        ),
        SiteOverviewEntry(
            slug="denmark",
            name="Danmark",
            timezone="Europe/Copenhagen",
            currency="DKK",
            price_area="DK2",
            available=True,
            health="healthy",
            health_detail=None,
            updated_at=None,
            data_age_seconds=None,
            is_stale=False,
            solar_power_kw=None,
            consumption_power_kw=None,
            grid_import_power_kw=None,
            grid_export_power_kw=None,
            battery_soc_percent=None,
            battery_power_kw=None,
            battery_capacity_kwh=None,
            battery_stored_kwh=None,
            battery_state=None,
            solar_today_kwh=None,
            consumption_today_kwh=None,
            grid_import_today_kwh=None,
            grid_export_today_kwh=None,
            battery_charged_today_kwh=None,
            battery_discharged_today_kwh=None,
            cost_today=81.0,
            savings_today=10.0,
            ev_power_kw=None,
            ev_state=None,
        ),
    ]
    parts = aggregate_sites(sites)
    assert len(parts.currencies) == 2
    by_cur = {c.currency: c for c in parts.currencies}
    assert by_cur["SEK"].cost_today == 100.0
    assert by_cur["DKK"].cost_today == 81.0


def test_partial_data_when_site_offline():
    sites = [
        _site("akarp", solar_kw=4.8, available=True),
        _site("denmark", solar_kw=None, available=False),
    ]
    parts = aggregate_sites(sites)
    assert parts.data_quality.partial is True
    assert parts.data_quality.sites_available == 1
    assert parts.aggregate.solar_power_kw == 4.8
