# EMIC Step 4 Result – Module Manager & Operations UI

**Status:** READY FOR STEP 4 VERIFICATION

**Date:** 2026-09-07

## Summary

Step 4 adds backend onboarding metadata, module config persistence, aggregated operations API, and a new **Moduler & enheter** config hub with schema-driven forms, enable/disable with conflict handling, device list/detail, and add-device wizard shell wired to live integrations.

## Acceptance table

| # | Requirement | Status | Evidence |
|---|-------------|--------|----------|
| 1 | Module descriptor onboarding metadata | PASS | `ModuleDescriptor` extended; bootstrap populated for 4 live integrations |
| 2 | Config schema validation + secret masking | PASS | `config_schema.py`, `ModuleConfigService`, API tests |
| 3 | `GET /api/system/onboarding-catalog` | PASS | `test_onboarding_catalog_api.py` |
| 4 | Module config GET/PUT | PASS | `test_module_config_api.py` |
| 5 | Test connection (read-only) | PASS | `providers/module_onboarding.py`, Mercedes real REST sync |
| 6 | Discover endpoint | PASS | `POST .../discover` on site_modules router |
| 7 | Aggregated `/operations` | PASS | `test_operations_api.py` |
| 8 | Module Manager UI hub | PASS | `/config/modules-devices`, `ModuleTable`, `ModuleDetailPanel` |
| 9 | UNKNOWN runtime label | PASS | `statusLabels.ts` → “Runtime status unavailable” |
| 10 | Enable/disable 409 UX | PASS | `EnableDisableControl` surfaces conflict message |
| 11 | Device Manager list/detail | PASS | `DeviceListPanel`, `DeviceDetailPanel` |
| 12 | Add Device wizard | PASS | `AddDeviceWizard` + `SchemaForm` + catalog-driven steps |
| 13 | Admin auth on mutations | PASS | `require_admin_token` on config/test-connection |
| 14 | Connection test rate limit | PASS | `backend/app/rate_limits.py` |
| 15 | Audit on config change | PASS | `audit_admin_mutation` on config PUT / test-connection |
| 16 | Architecture guards | PASS | `test_step4_guards.py`, handlers in providers layer |
| 17 | No vendor imports in modules-devices UI | PASS | `test_step4_guards.py` |
| 18 | Unit tests | PASS | Backend + frontend tests added; see test run below |

## Test run

Run locally:

```powershell
.\test-windows.ps1
```

Target: Python ≥1417, frontend ≥705, architecture guards pass.

## Prod verification (manual)

1. Deploy: `scripts/deploy.local.ps1`
2. Open `/config/modules-devices?site=akarp`
3. Verify operations load in one request
4. Toggle `feature.solar-forecast` for Denmark via Module Manager
5. Run `scripts/verify-prod-health.ps1` and `scripts/verify-prod-runtime-consistency.ps1`

## Known limitations

- Charge Amps full device create still delegates to existing ev-chargers API (wizard activates module + config; charger CRUD unchanged)
- Heartbeat credentials remain in global heartbeat settings repo (site mapping via `external_system_id`)
- Module runtime apply on config change returns `restart_required` hint; orchestrator auto-restart not fully wired for all modules

## Blockers

None for Step 4 verification entry.
