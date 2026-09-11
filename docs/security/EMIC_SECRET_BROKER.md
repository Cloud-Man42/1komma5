# EMIC Secret Broker

## Contract

- `GetSecret(secret_ref)` — module + site scoped only
- No enumeration API; unknown refs → audit + deny
- Values never logged
- Requires `secrets.read_own` permission

## Host-only storage

Secrets registered by host during module provisioning; worker never receives DB/Redis credentials via environment.

## Audit

Each access attempt recorded with `runtime_instance_id`, `module_id`, `secret_ref`, `allowed`, timestamp.

Implementation: `platform/modules/brokers/secret_broker.py`

Tests: `test_brokers.py`, `test_cross_site.py`
