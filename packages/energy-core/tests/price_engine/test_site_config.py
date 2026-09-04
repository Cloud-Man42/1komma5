"""Tests for site price engine config."""

from types import SimpleNamespace

from energy_core.price_engine.site_config import config_from_site, price_area_for_site
from energy_core.price_engine.types import OptimizationMode, PriceArea


def test_price_area_defaults_to_se4():
    site = SimpleNamespace(
        id=1,
        slug="akarp",
        timezone="Europe/Stockholm",
        energy_economics_country="SE",
        external_system_id="sys",
        price_area=None,
        optimization_mode="MONITOR_ONLY",
    )
    assert price_area_for_site(site) == PriceArea.SE4


def test_price_area_dk2_for_denmark():
    site = SimpleNamespace(
        id=2,
        slug="summer-house-denmark",
        timezone="Europe/Copenhagen",
        energy_economics_country="DK",
        external_system_id="sys",
        price_area=None,
        optimization_mode="MONITOR_ONLY",
    )
    assert price_area_for_site(site) == PriceArea.DK2


def test_config_from_site():
    site = SimpleNamespace(
        id=1,
        slug="akarp",
        timezone="Europe/Stockholm",
        energy_economics_country="SE",
        external_system_id="sys-1",
        price_area="SE4",
        optimization_mode="MONITOR_ONLY",
    )
    cfg = config_from_site(site)
    assert cfg.price_area == PriceArea.SE4
    assert cfg.optimization_mode == OptimizationMode.MONITOR_ONLY
