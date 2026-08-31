"""Historical Swedish micro-production tax credit (skattereduktion)."""

from __future__ import annotations

from datetime import date

TAX_CREDIT_RATE_SEK_KWH = 0.60
TAX_CREDIT_YEAR_LIMIT_KWH = 30_000.0
TAX_CREDIT_END_DATE = date(2025, 12, 31)


def compute_yearly_tax_credit_kwh(
    year: int,
    yearly_export_kwh: float,
    yearly_import_kwh: float,
    *,
    country: str = "SE",
    enabled: bool = True,
) -> float:
    """Eligible kWh for tax credit under historical Swedish rules."""
    if not enabled or country.upper() != "SE" or year > TAX_CREDIT_END_DATE.year:
        return 0.0
    if yearly_export_kwh <= 0:
        return 0.0
    return min(yearly_export_kwh, yearly_import_kwh, TAX_CREDIT_YEAR_LIMIT_KWH)


def compute_yearly_tax_credit_sek(
    year: int,
    yearly_export_kwh: float,
    yearly_import_kwh: float,
    *,
    country: str = "SE",
    enabled: bool = True,
) -> float:
    eligible = compute_yearly_tax_credit_kwh(
        year,
        yearly_export_kwh,
        yearly_import_kwh,
        country=country,
        enabled=enabled,
    )
    return round(eligible * TAX_CREDIT_RATE_SEK_KWH, 2)


def allocate_yearly_tax_credit(
    period_export_kwh: float,
    yearly_export_kwh: float,
    yearly_tax_credit_sek: float,
) -> float:
    """Allocate yearly tax credit to a sub-period proportionally by export share."""
    if yearly_tax_credit_sek <= 0 or yearly_export_kwh <= 0 or period_export_kwh <= 0:
        return 0.0
    return round(yearly_tax_credit_sek * (period_export_kwh / yearly_export_kwh), 2)
