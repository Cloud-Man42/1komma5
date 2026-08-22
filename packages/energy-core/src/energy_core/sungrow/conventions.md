# Sungrow telemetry conventions (EMIC canonical model)

Phase 1 uses **Heartbeat live-overview as proxy** for Sungrow Hybrid Inverter SH10.
No direct Modbus. Display name is always:

```text
Sungrow Hybrid Inverter SH10
```

Do not substitute SH10RT/SH10RS unless verified from device telemetry.

## Sign conventions

All power values are **non-negative magnitudes** in watts:

| Signal | Field | Convention |
|--------|-------|------------|
| PV production | `pv_power_w` | `>= 0` |
| House load | `load_power_w` | `>= 0` |
| Grid import | `grid_import_w` | `>= 0` |
| Grid export | `grid_export_w` | `>= 0` |
| Battery charge | `battery_charge_w` | `>= 0` |
| Battery discharge | `battery_discharge_w` | `>= 0` |

Heartbeat may send signed grid/battery power; the mapper splits into import/export
and charge/discharge using the same rules as `parse_live_overview`.

## Missing data

Use `null` for unknown values. Never substitute `0` as a placeholder.

## Energy balance residual

After normalization:

```text
PV + GridImport + BatteryDischarge ≈ Load + BatteryCharge + GridExport
residual_w = lhs - rhs
```

## Freshness

`sungrow_telemetry_max_age_seconds` (default 60) determines `fresh` flag on snapshots.
