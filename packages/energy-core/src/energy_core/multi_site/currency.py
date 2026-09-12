"""Currency resolution for site economics."""

from __future__ import annotations

_COUNTRY_CURRENCY = {
    "SE": "SEK",
    "DK": "DKK",
    "NO": "NOK",
    "FI": "EUR",
    "DE": "EUR",
}


def currency_for_country(country: str | None) -> str:
    if not country:
        return "SEK"
    return _COUNTRY_CURRENCY.get(country.upper(), "SEK")


def currency_for_site(site) -> str:
    return currency_for_country(getattr(site, "energy_economics_country", None))
