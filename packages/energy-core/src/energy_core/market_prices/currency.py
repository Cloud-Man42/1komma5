"""Market price currency helpers."""

from __future__ import annotations

from energy_core.config import Settings, get_settings

# Migration 041 renamed spot_price_sek_kwh -> spot_price_eur_kwh without converting
# values. Rows with magnitudes typical of SEK/kWh (0.25–3.0) must not be multiplied
# again by EUR_TO_SEK_RATE. True Nord Pool EUR/kWh for SE is usually below 0.25.
LEGACY_SEK_IN_EUR_COLUMN_THRESHOLD = 0.25


def eur_to_sek(value_eur: float, settings: Settings | None = None) -> float:
    cfg = settings or get_settings()
    return value_eur * cfg.eur_to_sek_rate


def sek_to_eur(value_sek: float, settings: Settings | None = None) -> float:
    cfg = settings or get_settings()
    return value_sek / cfg.eur_to_sek_rate


def is_legacy_sek_stored_as_eur(value: float) -> bool:
    """Detect pre-EUR column values that were already SEK/kWh."""
    return value > LEGACY_SEK_IN_EUR_COLUMN_THRESHOLD


def stored_eur_to_sek_kwh(value_eur: float | None, settings: Settings | None = None) -> float | None:
    """Convert a DB ``*_eur_kwh`` column to SEK/kWh, handling legacy SEK rows."""
    if value_eur is None:
        return None
    if is_legacy_sek_stored_as_eur(value_eur):
        return float(value_eur)
    return eur_to_sek(value_eur, settings)


def spot_price_eur(row) -> float | None:
    if row is None:
        return None
    return getattr(row, "spot_price_eur_kwh", None)


def all_in_price_eur(row) -> float | None:
    if row is None:
        return None
    return getattr(row, "all_in_price_eur_kwh", None)


def feed_in_price_eur(row) -> float | None:
    if row is None:
        return None
    return getattr(row, "feed_in_price_eur_kwh", None)


def effective_price_eur(row) -> float | None:
    if row is None:
        return None
    return all_in_price_eur(row) or spot_price_eur(row)


def effective_price_sek_kwh(row, settings: Settings | None = None) -> float | None:
    price = effective_price_eur(row)
    if price is None:
        return None
    return stored_eur_to_sek_kwh(price, settings)


def feed_in_price_sek_kwh(row, settings: Settings | None = None) -> float | None:
    price = feed_in_price_eur(row)
    if price is None:
        return None
    return stored_eur_to_sek_kwh(price, settings)
