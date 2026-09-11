# EMIC Device Control Broker

## Flow

```
Isolated worker → RPC Command → DeviceControlBroker → typed command schema → SyntheticDeviceAdapter (tests)
```

## Permissions

Requires one of: `device.control`, `energy.control`, `charger.control`, `vehicle.control`, `hvac.control`, `spa.control`.

## Leases

Short-lived control leases keyed by `(runtime_instance_id, site_id, device_id)`. Revoked on runtime stop/crash via `revoke_runtime()`.

## Safe state

On lease release, `SyntheticDeviceAdapter.release_control()` restores `safe_default_power_w` (typically 0 W).

## Cross-site

`device_site_id` in params must match runtime `site_id`; otherwise `PermissionError`.

## Production gate

`CONTROL_ISOLATION_GATE_OPEN=false` — control-capable third-party modules remain `BLOCKED` at runtime start until hard verification completes.

Implementation: `platform/modules/brokers/device_control_broker.py`
