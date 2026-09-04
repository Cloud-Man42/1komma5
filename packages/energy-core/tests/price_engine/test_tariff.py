"""Tests for import price tariff breakdown."""

from energy_core.price_engine.tariff import tariff_breakdown_from_period
from energy_core.price_engine.types import (
    Currency,
    PriceArea,
    PricePeriod,
    PriceQuality,
    PriceSource,
)


def _period(**overrides) -> PricePeriod:
    base = dict(
        period_start=__import__("datetime").datetime(2026, 8, 13, 13, 0, tzinfo=__import__("datetime").UTC),
        period_end=__import__("datetime").datetime(2026, 8, 13, 13, 15, tzinfo=__import__("datetime").UTC),
        site_id=1,
        price_area=PriceArea.SE4,
        currency=Currency.SEK,
        market_price_sek_kwh=0.32,
        import_price_sek_kwh=1.21,
        export_price_sek_kwh=0.39,
        source=PriceSource.HEARTBEAT,
        quality=PriceQuality.REAL,
        is_estimated=False,
        components={},
    )
    base.update(overrides)
    return PricePeriod(**base)


def test_tariff_grid_surcharge_from_import_minus_market():
    breakdown = tariff_breakdown_from_period(_period())
    assert breakdown is not None
    assert breakdown.grid_surcharge_sek_kwh == 0.89


def test_tariff_none_when_period_missing():
    assert tariff_breakdown_from_period(None) is None


def test_tariff_reads_vat_from_components():
    breakdown = tariff_breakdown_from_period(
        _period(components={"import": {"vat_rate": 0.25, "uses_fallback_grid_costs": False}})
    )
    assert breakdown is not None
    assert breakdown.vat_rate == 0.25
    assert breakdown.uses_fallback_grid_costs is False
