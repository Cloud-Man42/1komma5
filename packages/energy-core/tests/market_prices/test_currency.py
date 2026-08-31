"""Tests for market price currency conversion."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from energy_core.config import Settings
from energy_core.market_prices.currency import (
    effective_price_eur,
    effective_price_sek_kwh,
    eur_to_sek,
    feed_in_price_sek_kwh,
    is_legacy_sek_stored_as_eur,
    sek_to_eur,
    stored_eur_to_sek_kwh,
)


@dataclass
class _PriceRow:
    spot_price_eur_kwh: float | None = None
    all_in_price_eur_kwh: float | None = None
    feed_in_price_eur_kwh: float | None = None


def test_eur_to_sek_uses_config_rate():
    settings = Settings(EUR_TO_SEK_RATE=10.0)
    assert eur_to_sek(0.5, settings) == pytest.approx(5.0)


def test_sek_to_eur_inverts_rate():
    settings = Settings(EUR_TO_SEK_RATE=10.0)
    assert sek_to_eur(5.0, settings) == pytest.approx(0.5)


def test_effective_price_prefers_all_in():
    row = _PriceRow(spot_price_eur_kwh=0.2, all_in_price_eur_kwh=0.3)
    assert effective_price_eur(row) == pytest.approx(0.3)


def test_effective_price_sek_converts():
    row = _PriceRow(all_in_price_eur_kwh=0.2)
    settings = Settings(EUR_TO_SEK_RATE=11.0)
    assert effective_price_sek_kwh(row, settings) == pytest.approx(2.2)


def test_effective_price_sek_none_when_missing():
    assert effective_price_sek_kwh(None) is None
    assert effective_price_sek_kwh(_PriceRow()) is None


def test_legacy_sek_values_are_not_converted_again():
    settings = Settings(EUR_TO_SEK_RATE=11.0)
    assert is_legacy_sek_stored_as_eur(0.72) is True
    assert is_legacy_sek_stored_as_eur(0.20) is False
    assert stored_eur_to_sek_kwh(0.72, settings) == pytest.approx(0.72)
    assert stored_eur_to_sek_kwh(0.075, settings) == pytest.approx(0.825)


def test_feed_in_price_sek_converts_eur():
    row = _PriceRow(feed_in_price_eur_kwh=0.075)
    settings = Settings(EUR_TO_SEK_RATE=11.0)
    assert feed_in_price_sek_kwh(row, settings) == pytest.approx(0.825)
