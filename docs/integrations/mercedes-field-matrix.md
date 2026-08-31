# Mercedes field matrix (EQE)

This document tracks which Mercedes-me attributes EMIC has **observed** for the connected EQE,
and how each desired `VehicleState` field should be classified.

Run the masked inspector after the collector has been connected for a while:

- API: `GET /api/sites/{slug}/vehicles/integration/raw-attributes`
- Admin: `/admin/integrations/mercedes` (Raw Data Inspector panel)

## Classification legend

| Status | Meaning |
|--------|---------|
| **AVAILABLE** | Mercedes sends the value; EMIC maps it today or will map after verification |
| **DERIVED** | Computed from one or more Mercedes fields (e.g. plug state from `chargingstatus`) |
| **ESTIMATED** | Computed from indirect signals (SoC delta × battery capacity) |
| **NOT_AVAILABLE** | Not observed from Mercedes for this vehicle |

## Target VehicleState fields

| Field | Mercedes attribute(s) | Status | Notes |
|-------|----------------------|--------|-------|
| `state_of_charge_percent` | `soc` | AVAILABLE | Mapped in `vehicle_mapper.py` |
| `target_soc_percent` | `max_soc` | AVAILABLE | Mapped |
| `electric_range_km` | `rangeElectricKm` | AVAILABLE | Mapped |
| `is_charging` | `chargingactive`, `chargingstatus` | DERIVED | Derived from status enums |
| `is_plugged_in` | `chargingstatus` | DERIVED | Excludes unplugged/disconnected states |
| `charging_power_kw` | `chargingpowerkw` | AVAILABLE | W→kW normalization when >100 |
| `charging_power_limit_kw` | TBD | NOT_AVAILABLE | Inspect raw attributes |
| `estimated_charge_complete_at` | TBD | NOT_AVAILABLE | Inspect raw attributes |
| `departure_time` | TBD | NOT_AVAILABLE | Capability may exist; attribute name TBD |
| `latitude` | `positionLat`, `positionlat` | **VERIFY** | Decoder passes all VEP keys; mapper must add |
| `longitude` | `positionLong`, `positionlong` | **VERIFY** | Same as latitude |
| `location_timestamp` | position-related timestamp | **VERIFY** | Inspect observations |
| `odometer` | `odo`, `odometer` | **VERIFY** | Inspect observations |
| `ignition_state` | TBD | NOT_AVAILABLE | Inspect observations |
| `vehicle_state` | TBD | NOT_AVAILABLE | Parked/driving if available |
| `charging_energy_kwh` | session energy fields | **VERIFY** | May not exist on EQE |
| `charging_current_a` | TBD | **VERIFY** | |
| `charging_voltage_v` | TBD | **VERIFY** | |

## Geofence gate (Fas 2)

Charging Session Intelligence geofence matching requires **confirmed GPS** from the field matrix.
If `positionLat` / `positionLong` are NOT_AVAILABLE after sufficient observation time, Fas 2
location resolution falls back to:

1. Charge Amps / charger correlation (home)
2. Manual user corrections
3. `UNKNOWN` location (no false positives)

Update this table when new attributes appear in `raw-attributes` observations.
