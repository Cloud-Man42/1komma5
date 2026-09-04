"""Normalize provider price points to canonical 15-minute periods."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from energy_core.config import Settings, get_settings
from energy_core.market_prices.currency import stored_eur_to_sek_kwh
from energy_core.price_engine.periods import align_period_start, period_end
from energy_core.price_engine.types import (
    Currency,
    PriceArea,
    PricePeriod,
    PriceQuality,
    PriceSource,
    RawPricePoint,
    INTERVAL_MINUTES,
)


def _eur_to_sek(value: float | None, settings: Settings | None = None) -> float | None:
    if value is None:
        return None
    return stored_eur_to_sek_kwh(value, settings)


def normalize_to_periods(
    points: tuple[RawPricePoint, ...],
    *,
    site_id: int,
    price_area: PriceArea,
    currency: Currency = Currency.SEK,
    settings: Settings | None = None,
) -> tuple[PricePeriod, ...]:
    """Expand hourly (or native 15m) provider points into 15-minute PricePeriod rows."""
    cfg = settings or get_settings()
    by_period: dict[datetime, PricePeriod] = {}

    for point in points:
        if point.timestamp.tzinfo is None:
            ts = point.timestamp.replace(tzinfo=UTC)
        else:
            ts = point.timestamp.astimezone(UTC)

        market_sek = _eur_to_sek(point.market_price_eur_kwh, cfg)
        import_sek = _eur_to_sek(point.import_price_eur_kwh, cfg)
        export_sek = _eur_to_sek(point.export_price_eur_kwh, cfg)

        if point.native_resolution_minutes <= INTERVAL_MINUTES:
            starts = (align_period_start(ts),)
            quality = PriceQuality.REAL
            source = PriceSource.HEARTBEAT
            is_estimated = False
        else:
            hour_start = align_period_start(ts.replace(minute=0))
            starts = tuple(
                hour_start + timedelta(minutes=offset)
                for offset in range(0, point.native_resolution_minutes, INTERVAL_MINUTES)
            )
            quality = PriceQuality.ESTIMATED
            source = PriceSource.REPLICATED_HOURLY
            is_estimated = True

        for start in starts:
            existing = by_period.get(start)
            components = dict(point.components)
            if is_estimated:
                components["replication"] = {
                    "from_resolution_minutes": point.native_resolution_minutes,
                    "native_timestamp": ts.isoformat(),
                }

            row = PricePeriod(
                period_start=start,
                period_end=period_end(start),
                site_id=site_id,
                price_area=price_area,
                currency=currency,
                market_price_sek_kwh=market_sek,
                import_price_sek_kwh=import_sek,
                export_price_sek_kwh=export_sek,
                source=source,
                quality=quality,
                is_estimated=is_estimated,
                components=components,
            )
            if existing is None or _quality_rank(row.quality) >= _quality_rank(existing.quality):
                by_period[start] = row

    return tuple(sorted(by_period.values(), key=lambda p: p.period_start))


def merge_period_layers(
    market: tuple[PricePeriod, ...],
    import_rows: tuple[PricePeriod, ...],
    export_rows: tuple[PricePeriod, ...],
) -> tuple[PricePeriod, ...]:
    """Merge market/import/export layers by period_start."""
    by_start: dict[datetime, PricePeriod] = {p.period_start: p for p in market}

    for layer in import_rows:
        existing = by_start.get(layer.period_start)
        if existing is None:
            by_start[layer.period_start] = layer
            continue
        by_start[layer.period_start] = replace(
            existing,
            import_price_sek_kwh=layer.import_price_sek_kwh,
            quality=_merge_quality(existing.quality, layer.quality),
            components={**existing.components, "import": layer.components},
        )

    for layer in export_rows:
        existing = by_start.get(layer.period_start)
        if existing is None:
            by_start[layer.period_start] = layer
            continue
        export_components = dict(existing.components)
        export_components["export"] = layer.components
        by_start[layer.period_start] = replace(
            existing,
            export_price_sek_kwh=layer.export_price_sek_kwh,
            quality=_merge_quality(existing.quality, layer.quality),
            components=export_components,
        )

    return tuple(sorted(by_start.values(), key=lambda p: p.period_start))


def _quality_rank(quality: PriceQuality) -> int:
    order = {
        PriceQuality.REAL: 5,
        PriceQuality.CALCULATED: 4,
        PriceQuality.ESTIMATED: 3,
        PriceQuality.STALE: 2,
        PriceQuality.MISSING: 1,
    }
    return order.get(quality, 0)


def _merge_quality(a: PriceQuality, b: PriceQuality) -> PriceQuality:
    return a if _quality_rank(a) <= _quality_rank(b) else b
