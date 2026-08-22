"""EV charger catalog and integration metadata API."""

from __future__ import annotations

from dataclasses import asdict

from app.schemas import (
    ChargerCatalogModelResponse,
    ChargerIntegrationMethodResponse,
    ChargerManufacturerResponse,
    ChargerModelDetailResponse,
)
from energy_core.chargers.framework.catalog import (
    feature_matrix_rows,
    get_manufacturer,
    get_model,
    list_all_integration_methods,
    list_integration_methods,
    list_manufacturers,
    list_models,
)
from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/chargers", tags=["charger-catalog"])


def _method_response(method) -> ChargerIntegrationMethodResponse:
    return ChargerIntegrationMethodResponse(
        id=method.id,
        label=method.label,
        protocol=method.protocol,
        connection_type=method.connection_type,
        recommended=method.recommended,
        priority=method.priority,
        implementation_status=method.implementation_status,
        cloud_dependent=method.cloud_dependent,
        documentation_url=method.documentation_url,
        credential_fields=[asdict(field) for field in method.credential_fields],
        connection_fields=[asdict(field) for field in method.connection_fields],
    )


def _model_response(model) -> ChargerCatalogModelResponse:
    caps = model.capabilities
    return ChargerCatalogModelResponse(
        id=model.id,
        manufacturer_id=model.manufacturer_id,
        name=model.name,
        status=model.status,
        supported_protocols=list(model.supported_protocols),
        integration_methods=list(model.integration_methods),
        documentation_url=model.documentation_url,
        capabilities={
            "can_read_status": caps.can_read_status,
            "can_start_charging": caps.can_start_charging,
            "can_stop_charging": caps.can_stop_charging,
            "can_read_power": caps.can_read_power,
            "can_read_energy": caps.can_read_energy,
            "can_read_session": caps.can_read_session,
            "can_set_max_current": caps.can_set_max_current,
            "supports_smart_charging": caps.supports_smart_charging,
        },
    )


@router.get("/manufacturers", response_model=list[ChargerManufacturerResponse])
async def list_charger_manufacturers() -> list[ChargerManufacturerResponse]:
    return [
        ChargerManufacturerResponse(
            id=manufacturer.id,
            name=manufacturer.name,
            model_count=len(manufacturer.models),
        )
        for manufacturer in list_manufacturers()
    ]


@router.get("/manufacturers/{manufacturer_id}", response_model=ChargerManufacturerResponse)
async def get_charger_manufacturer(manufacturer_id: str) -> ChargerManufacturerResponse:
    manufacturer = get_manufacturer(manufacturer_id)
    if manufacturer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manufacturer not found")
    return ChargerManufacturerResponse(
        id=manufacturer.id,
        name=manufacturer.name,
        model_count=len(manufacturer.models),
    )


@router.get("/manufacturers/{manufacturer_id}/models", response_model=list[ChargerCatalogModelResponse])
async def list_charger_models(manufacturer_id: str) -> list[ChargerCatalogModelResponse]:
    if get_manufacturer(manufacturer_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manufacturer not found")
    return [_model_response(model) for model in list_models(manufacturer_id)]


@router.get(
    "/manufacturers/{manufacturer_id}/models/{model_id}",
    response_model=ChargerModelDetailResponse,
)
async def get_charger_model_detail(manufacturer_id: str, model_id: str) -> ChargerModelDetailResponse:
    model = get_model(manufacturer_id, model_id)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    methods = [_method_response(method) for method in list_integration_methods(manufacturer_id, model_id)]
    return ChargerModelDetailResponse(
        model=_model_response(model),
        integration_methods=methods,
    )


@router.get("/feature-matrix")
async def get_feature_matrix() -> list[dict[str, str | bool]]:
    return feature_matrix_rows()


@router.get("/integration-methods", response_model=list[ChargerIntegrationMethodResponse])
async def list_charger_integration_methods() -> list[ChargerIntegrationMethodResponse]:
    return [_method_response(method) for method in list_all_integration_methods()]
