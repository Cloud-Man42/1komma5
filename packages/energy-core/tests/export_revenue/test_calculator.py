"""Tests for export revenue calculator."""

from __future__ import annotations

import pytest

from energy_core.export_revenue.calculator import (
    ExportRevenueAccumulator,
    SellPriceConfig,
    accumulate_export_interval,
    effective_sell_price_sek_kwh,
    finalize_export_totals,
)
from energy_core.export_revenue.tax_credit import (
    allocate_yearly_tax_credit,
    compute_yearly_tax_credit_kwh,
    compute_yearly_tax_credit_sek,
)


class TestEffectiveSellPrice:
    def test_positive_spot_price(self):
        config = SellPriceConfig(fallback_flat_price_sek_kwh=0.8)
        price, spot_q, adj_q = effective_sell_price_sek_kwh(0.72, config)
        assert price == pytest.approx(0.72)
        assert spot_q == "ACTUAL"

    def test_negative_spot_price_not_clamped(self):
        config = SellPriceConfig()
        price, _, _ = effective_sell_price_sek_kwh(-0.20, config)
        assert price == pytest.approx(-0.20)

    def test_zero_spot_price(self):
        config = SellPriceConfig()
        price, _, _ = effective_sell_price_sek_kwh(0.0, config)
        assert price == 0.0

    def test_supplier_adjustment_ore(self):
        config = SellPriceConfig(spot_price_adjustment_ore_per_kwh=5.0)
        price, _, _ = effective_sell_price_sek_kwh(0.50, config)
        assert price == pytest.approx(0.55)

    def test_supplier_deduction_ore(self):
        config = SellPriceConfig(supplier_deduction_ore_per_kwh=3.0)
        price, _, _ = effective_sell_price_sek_kwh(0.50, config)
        assert price == pytest.approx(0.47)

    def test_missing_spot_uses_fallback(self):
        config = SellPriceConfig(fallback_flat_price_sek_kwh=0.8)
        price, spot_q, _ = effective_sell_price_sek_kwh(None, config)
        assert price == pytest.approx(0.8)
        assert spot_q == "ESTIMATED"

    def test_flat_pricing_mode(self):
        config = SellPriceConfig(pricing_mode="flat", fallback_flat_price_sek_kwh=0.29)
        price, spot_q, _ = effective_sell_price_sek_kwh(0.72, config)
        assert price == pytest.approx(0.29)
        assert spot_q == "CALCULATED"

    def test_feed_in_pricing_mode(self):
        config = SellPriceConfig(pricing_mode="feed_in")
        price, spot_q, _ = effective_sell_price_sek_kwh(0.83, config)
        assert price == pytest.approx(0.83)
        assert spot_q == "ACTUAL"


class TestIntervalAccumulation:
    def test_single_interval_positive(self):
        config = SellPriceConfig()
        result, acc = accumulate_export_interval(2.40, 0.72, config)
        assert result.energy_sale_revenue_sek == pytest.approx(1.728)
        assert result.grid_benefit_revenue_sek == 0.0

    def test_multiple_intervals_weighted_average(self):
        config = SellPriceConfig()
        acc = ExportRevenueAccumulator()
        accumulate_export_interval(2.40, 0.72, config, acc)
        accumulate_export_interval(1.80, 0.31, config, acc)
        totals = finalize_export_totals(acc)
        assert totals.energy_sale_revenue_sek == pytest.approx(2.286, abs=0.001)
        assert totals.exported_kwh == pytest.approx(4.20)
        assert totals.effective_sell_price_sek_kwh == pytest.approx(2.286 / 4.20, abs=0.001)

    def test_negative_spot_revenue(self):
        config = SellPriceConfig()
        result, _ = accumulate_export_interval(2.0, -0.20, config)
        assert result.energy_sale_revenue_sek == pytest.approx(-0.40)

    def test_grid_benefit_separate(self):
        config = SellPriceConfig(grid_benefit_ore_per_kwh=8.0)
        result, acc = accumulate_export_interval(10.0, 0.50, config)
        assert result.energy_sale_revenue_sek == pytest.approx(5.0)
        assert result.grid_benefit_revenue_sek == pytest.approx(0.80)
        totals = finalize_export_totals(acc)
        assert totals.export_revenue_sek == pytest.approx(5.80)

    def test_no_export(self):
        config = SellPriceConfig()
        result, acc = accumulate_export_interval(0.0, 0.50, config)
        assert result.energy_sale_revenue_sek == 0.0
        totals = finalize_export_totals(acc)
        assert totals.effective_sell_price_sek_kwh is None

    def test_spot_priced_fraction(self):
        config = SellPriceConfig(fallback_flat_price_sek_kwh=0.8)
        acc = ExportRevenueAccumulator()
        accumulate_export_interval(1.0, 0.50, config, acc)
        accumulate_export_interval(1.0, None, config, acc)
        totals = finalize_export_totals(acc)
        assert totals.spot_priced_fraction == pytest.approx(0.5)


class TestTaxCredit:
    def test_2025_eligible_min_of_export_import_cap(self):
        eligible = compute_yearly_tax_credit_kwh(2025, 40000, 20000)
        assert eligible == 20000

    def test_2025_cap_30000(self):
        eligible = compute_yearly_tax_credit_kwh(2025, 50000, 50000)
        assert eligible == 30000

    def test_2026_no_tax_credit(self):
        eligible = compute_yearly_tax_credit_kwh(2026, 1000, 1000)
        assert eligible == 0.0
        assert compute_yearly_tax_credit_sek(2026, 1000, 1000) == 0.0

    def test_2025_tax_credit_amount(self):
        assert compute_yearly_tax_credit_sek(2025, 5000, 5000) == pytest.approx(3000.0)

    def test_non_sweden_no_tax_credit(self):
        assert compute_yearly_tax_credit_sek(2025, 5000, 5000, country="DK") == 0.0

    def test_proportional_allocation(self):
        yearly = compute_yearly_tax_credit_sek(2025, 1000, 1000)
        assert allocate_yearly_tax_credit(250, 1000, yearly) == pytest.approx(yearly * 0.25)

    def test_year_boundary_2025_vs_2026(self):
        assert compute_yearly_tax_credit_sek(2025, 100, 100) == 60.0
        assert compute_yearly_tax_credit_sek(2026, 100, 100) == 0.0


class TestNoDoubleCounting:
    def test_export_revenue_excludes_tax_credit(self):
        config = SellPriceConfig(grid_benefit_ore_per_kwh=5.0)
        _, acc = accumulate_export_interval(10.0, 0.40, config)
        totals = finalize_export_totals(acc)
        tax = compute_yearly_tax_credit_sek(2025, 10.0, 10.0)
        assert totals.export_revenue_sek == pytest.approx(4.0 + 0.50)
        assert tax == pytest.approx(6.0)
        assert totals.export_revenue_sek != tax + totals.export_revenue_sek
