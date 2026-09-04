"""Financial daily aggregate persistence."""

from __future__ import annotations

from datetime import date

from energy_core.db.models import FinancialDailyModel
from energy_core.financial.aggregation import FinancialDailyAccumulator
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession


class FinancialDailyRepository:
    def __init__(self, session: AsyncSession, *, is_sqlite: bool) -> None:
        self._session = session
        self._is_sqlite = is_sqlite

    async def upsert(self, site_id: int, acc: FinancialDailyAccumulator) -> None:
        day = date.fromisoformat(acc.day)
        values = {
            "site_id": site_id,
            "day": day,
            "solar_self_kwh": acc.solar_self_kwh,
            "battery_self_kwh": acc.battery_self_kwh,
            "export_kwh": acc.export_kwh,
            "import_kwh": acc.import_kwh,
            "solar_savings_sek": acc.solar_savings_sek,
            "battery_savings_sek": acc.battery_savings_sek,
            "grid_import_cost_sek": acc.grid_import_cost_sek,
            "market_priced_kwh": acc.market_priced_kwh,
            "priced_denominator_kwh": acc.priced_denominator_kwh,
            "energy_sale_sek": acc.energy_sale_sek,
            "grid_benefit_sek": acc.grid_benefit_sek,
            "spot_priced_kwh": acc.spot_priced_kwh,
            "fallback_priced_kwh": acc.fallback_priced_kwh,
            "negative_price_kwh": acc.negative_price_kwh,
            "contracted_export_kwh": acc.contracted_export_kwh,
            "uncontracted_export_kwh": acc.uncontracted_export_kwh,
        }
        insert = sqlite_insert if self._is_sqlite else pg_insert
        stmt = insert(FinancialDailyModel).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["site_id", "day"],
            set_={key: getattr(stmt.excluded, key) for key in values if key not in {"site_id", "day"}},
        )
        await self._session.execute(stmt)

    async def list_for_site(
        self,
        site_id: int,
        *,
        from_day: date | None = None,
        to_day: date | None = None,
    ) -> list[FinancialDailyAccumulator]:
        stmt = select(FinancialDailyModel).where(FinancialDailyModel.site_id == site_id)
        if from_day is not None:
            stmt = stmt.where(FinancialDailyModel.day >= from_day)
        if to_day is not None:
            stmt = stmt.where(FinancialDailyModel.day < to_day)
        stmt = stmt.order_by(FinancialDailyModel.day)
        rows = (await self._session.scalars(stmt)).all()
        return [
            FinancialDailyAccumulator(
                day=row.day.isoformat(),
                solar_self_kwh=row.solar_self_kwh,
                battery_self_kwh=row.battery_self_kwh,
                export_kwh=row.export_kwh,
                import_kwh=row.import_kwh,
                solar_savings_sek=row.solar_savings_sek,
                battery_savings_sek=row.battery_savings_sek,
                grid_import_cost_sek=row.grid_import_cost_sek,
                market_priced_kwh=row.market_priced_kwh,
                priced_denominator_kwh=row.priced_denominator_kwh,
                energy_sale_sek=row.energy_sale_sek,
                grid_benefit_sek=row.grid_benefit_sek,
                spot_priced_kwh=row.spot_priced_kwh,
                fallback_priced_kwh=row.fallback_priced_kwh,
                negative_price_kwh=row.negative_price_kwh,
                contracted_export_kwh=row.contracted_export_kwh,
                uncontracted_export_kwh=row.uncontracted_export_kwh,
            )
            for row in rows
        ]
