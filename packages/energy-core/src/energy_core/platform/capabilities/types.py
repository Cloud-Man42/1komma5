"""System capability identifiers (vendor-neutral)."""

from __future__ import annotations

from enum import StrEnum


class Capability(StrEnum):
    """Normalized capabilities EMIC features consume."""

    ENERGY_READ_GRID_POWER = "energy.read_grid_power"
    ENERGY_READ_SOLAR_POWER = "energy.read_solar_power"
    BATTERY_READ_SOC = "battery.read_soc"
    BATTERY_READ_POWER = "battery.read_power"
    EV_CHARGER_START = "ev_charger.start"
    EV_CHARGER_STOP = "ev_charger.stop"
    EV_CHARGER_SET_CURRENT = "ev_charger.set_current"
    EV_CHARGER_READ_POWER = "ev_charger.read_power"
    EV_CHARGER_READ_ENERGY = "ev_charger.read_energy"
    VEHICLE_READ_SOC = "vehicle.read_soc"
    VEHICLE_READ_RANGE = "vehicle.read_range"
    VEHICLE_READ_CHARGING_STATE = "vehicle.read_charging_state"
    SPA_READ_TEMPERATURE = "spa.read_temperature"
    SPA_SET_TEMPERATURE = "spa.set_temperature"
    HVAC_READ_TEMPERATURE = "hvac.read_temperature"
    HVAC_READ_HUMIDITY = "hvac.read_humidity"
    HVAC_READ_STATE = "hvac.read_state"
    HVAC_READ_TARGET_TEMPERATURE = "hvac.read_target_temperature"
    HVAC_READ_STATUS = "hvac.read_status"
    PRICE_READ_CURRENT = "price.read_current"
    PRICE_READ_FORECAST = "price.read_forecast"
    WEATHER_READ_CURRENT = "weather.read_current"
    WEATHER_READ_FORECAST = "weather.read_forecast"
    FORECAST_SOLAR = "forecast.solar"
    OPTIMIZATION_ENERGY = "optimization.energy"
    SMART_CHARGING = "smart_charging"
    READ_STATUS = "read_status"
    READ_POWER = "read_power"
