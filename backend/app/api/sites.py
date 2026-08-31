from app.deps import get_db_session, get_reading_repository
from app.schemas import (
    HistoricalEnergyMonth,
    HistoricalEnergyYearResponse,
    HistoricalEnergyYearUpdate,
    ReadingResponse,
    SiteCreateRequest,
    SiteEnergyConfigResponse,
    SiteEnergyConfigUpdateRequest,
    SiteResponse,
    SiteUpdateRequest,
)
from energy_core.db.energy_balance_repo import SiteEnergyConfigRepository
from energy_core.db.repositories import (
    EnergyReadingRepository,
    HistoricalEnergyRepository,
    HistoricalMonthlyEnergy,
    SiteRepository,
)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["sites"])


def _site_response(site, latest_reading) -> SiteResponse:
    return SiteResponse(
        slug=site.slug,
        name=site.name,
        timezone=site.timezone,
        external_system_id=site.external_system_id,
        fallback_purchase_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
        export_compensation_sek_kwh=site.export_compensation_sek_kwh,
        main_fuse_a=site.main_fuse_a,
        safety_margin_a=site.safety_margin_a,
        sell_contract_start_date=getattr(site, "sell_contract_start_date", None),
        latest_reading=(
            ReadingResponse(
                recorded_at=latest_reading.recorded_at,
                solar_production_w=latest_reading.solar_production_w,
                consumption_w=latest_reading.consumption_w,
                grid_import_w=latest_reading.grid_import_w,
                grid_export_w=latest_reading.grid_export_w,
                battery_soc_pct=latest_reading.battery_soc_pct,
                battery_power_w=latest_reading.battery_power_w,
            )
            if latest_reading
            else None
        ),
    )


@router.put(
    "/sites/{slug}/historical-energy/{year}",
    response_model=HistoricalEnergyYearResponse,
)
async def update_historical_energy(
    slug: str,
    year: int,
    payload: HistoricalEnergyYearUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> HistoricalEnergyYearResponse:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    if not 2000 <= year <= 2100:
        raise HTTPException(status_code=422, detail="Year must be between 2000 and 2100")
    if {month.month for month in payload.months} != set(range(1, 13)):
        raise HTTPException(status_code=422, detail="Exactly one value is required for every month")
    repository = HistoricalEnergyRepository(
        session,
        is_sqlite=session.bind is not None and session.bind.dialect.name == "sqlite",
    )
    await repository.upsert_months(
        site.id,
        [
            HistoricalMonthlyEnergy(
                year=year,
                month=month.month,
                imported_kwh=month.imported_kwh,
                imported_cost_sek=month.imported_cost_sek,
                source=payload.source,
                estimated=payload.estimated,
            )
            for month in payload.months
        ],
    )
    await session.commit()
    return HistoricalEnergyYearResponse(
        slug=slug,
        year=year,
        source=payload.source,
        estimated=payload.estimated,
        total_imported_kwh=round(sum(month.imported_kwh for month in payload.months), 3),
        total_imported_cost_sek=(
            round(sum(month.imported_cost_sek or 0 for month in payload.months), 2)
            if all(month.imported_cost_sek is not None for month in payload.months)
            else None
        ),
        months=payload.months,
    )


@router.get(
    "/sites/{slug}/historical-energy/{year}",
    response_model=HistoricalEnergyYearResponse,
)
async def get_historical_energy(
    slug: str,
    year: int,
    session: AsyncSession = Depends(get_db_session),
) -> HistoricalEnergyYearResponse:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    records = [
        record
        for record in await HistoricalEnergyRepository(
            session,
            is_sqlite=session.bind is not None and session.bind.dialect.name == "sqlite",
        ).list_for_site(site.id)
        if record.year == year
    ]
    if not records:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Historical year not found")
    return HistoricalEnergyYearResponse(
        slug=slug,
        year=year,
        source=records[0].source,
        estimated=records[0].estimated,
        total_imported_kwh=round(sum(record.imported_kwh for record in records), 3),
        total_imported_cost_sek=(
            round(sum(record.imported_cost_sek or 0 for record in records), 2)
            if all(record.imported_cost_sek is not None for record in records)
            else None
        ),
        months=[
            HistoricalEnergyMonth(
                month=record.month,
                imported_kwh=record.imported_kwh,
                imported_cost_sek=record.imported_cost_sek,
            )
            for record in records
        ],
    )


@router.get("/sites", response_model=list[SiteResponse])
async def list_sites(
    repo: EnergyReadingRepository = Depends(get_reading_repository),
) -> list[SiteResponse]:
    sites = await repo.list_sites_with_latest()
    return [
        _site_response(site, site.latest_reading)
        for site in sites
    ]


@router.post("/sites", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site(
    payload: SiteCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SiteResponse:
    repo = SiteRepository(session)
    try:
        site = await repo.create_site(
            slug=payload.slug,
            name=payload.name,
            timezone=payload.timezone,
            external_system_id=payload.external_system_id,
            fallback_purchase_price_sek_kwh=payload.fallback_purchase_price_sek_kwh,
            export_compensation_sek_kwh=payload.export_compensation_sek_kwh,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    await session.commit()
    return SiteResponse(
        slug=site.slug,
        name=site.name,
        timezone=site.timezone,
        external_system_id=site.external_system_id,
        fallback_purchase_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
        export_compensation_sek_kwh=site.export_compensation_sek_kwh,
        latest_reading=None,
    )


@router.put("/sites/{slug}", response_model=SiteResponse)
async def update_site(
    slug: str,
    payload: SiteUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    reading_repo: EnergyReadingRepository = Depends(get_reading_repository),
) -> SiteResponse:
    repo = SiteRepository(session)
    updates = payload.model_dump(exclude_unset=True)
    try:
        site = await repo.update_site(slug, **updates)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found") from exc
    await session.commit()
    latest = await reading_repo.get_latest_for_site(site.id)
    return _site_response(site, latest)


@router.get("/sites/{slug}/energy-config", response_model=SiteEnergyConfigResponse)
async def get_site_energy_config(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
) -> SiteEnergyConfigResponse:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    config = await SiteEnergyConfigRepository(session).get_or_create(site.id)
    return SiteEnergyConfigResponse(
        site_slug=slug,
        load_includes_ev_charger=config.load_includes_ev_charger,
        inverter_display_name=config.inverter_display_name,
        physical_ev_charger_label=config.physical_ev_charger_label,
        ev_vehicle_label=config.ev_vehicle_label,
    )


@router.put("/sites/{slug}/energy-config", response_model=SiteEnergyConfigResponse)
async def update_site_energy_config(
    slug: str,
    payload: SiteEnergyConfigUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SiteEnergyConfigResponse:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    config = await SiteEnergyConfigRepository(session).update(
        site.id,
        load_includes_ev_charger=payload.load_includes_ev_charger,
        clear_load_includes_ev_charger=payload.clear_load_includes_ev_charger,
        inverter_display_name=payload.inverter_display_name,
        physical_ev_charger_label=payload.physical_ev_charger_label,
        ev_vehicle_label=payload.ev_vehicle_label,
    )
    await session.commit()
    return SiteEnergyConfigResponse(
        site_slug=slug,
        load_includes_ev_charger=config.load_includes_ev_charger,
        inverter_display_name=config.inverter_display_name,
        physical_ev_charger_label=config.physical_ev_charger_label,
        ev_vehicle_label=config.ev_vehicle_label,
    )


@router.delete("/sites/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    repo = SiteRepository(session)
    try:
        await repo.delete_site(slug)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found") from exc
    await session.commit()
