from energy_core.integrations.arctic_spa.operational_state import (
    filter_cycle_active,
    heater_drawing_power,
    pump_power_w,
)


def test_filter_not_active_without_measurable_load():
    assert (
        filter_cycle_active(
            filter_status="Filtering",
            current_power_w=0.0,
            breakdown={"pump1": 0.0},
        )
        is False
    )


def test_filter_active_with_pump_load():
    assert (
        filter_cycle_active(
            filter_status="Filtering",
            current_power_w=20.0,
            breakdown={"pump1": 180.0},
        )
        is True
    )


def test_heater_not_active_without_power():
    assert (
        heater_drawing_power(
            heater_active_reported=True,
            current_power_w=0.0,
            breakdown={},
        )
        is False
    )


def test_heater_active_from_breakdown():
    assert (
        heater_drawing_power(
            heater_active_reported=False,
            current_power_w=0.0,
            breakdown={"heater": 1800.0},
        )
        is True
    )


def test_pump_power_sums_pump_keys():
    assert pump_power_w({"pump1": 100.0, "pump2": 50.0, "heater": 2000.0}) == 150.0
