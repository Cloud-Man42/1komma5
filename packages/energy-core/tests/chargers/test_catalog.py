"""Catalog integrity tests for EV charger integration framework."""

from energy_core.chargers.framework.catalog import (
    CHARGE_AMPS_CLOUD,
    get_manufacturer,
    get_model,
    list_all_integration_methods,
    list_manufacturers,
    validate_catalog,
)


def test_manufacturer_ids_unique():
    ids = [manufacturer.id for manufacturer in list_manufacturers()]
    assert len(ids) == len(set(ids))


def test_model_ids_unique_within_manufacturer():
    for manufacturer in list_manufacturers():
        model_ids = [model.id for model in manufacturer.models]
        assert len(model_ids) == len(set(model_ids)), manufacturer.id


def test_charge_amps_halo_is_full():
    model = get_model("charge-amps", "halo")
    assert model is not None
    assert model.status == "FULL"
    assert CHARGE_AMPS_CLOUD in model.integration_methods


def test_catalog_validation_passes():
    errors = validate_catalog()
    assert errors == []


def test_all_manufacturers_listed():
    assert get_manufacturer("zaptec") is not None
    assert get_manufacturer("go-e") is not None
    assert get_manufacturer("keba") is not None


def test_list_all_integration_methods_covers_vendors():
    methods = list_all_integration_methods()
    ids = {method.id for method in methods}
    assert "CHARGE_AMPS_CLOUD" in ids
    assert "ZAPTEC_REST" in ids
    assert "EASEE_CLOUD" in ids
    assert len(methods) >= 20
