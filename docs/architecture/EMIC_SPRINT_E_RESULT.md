# EMIC Sprint E — Real External Module / SDK Validation

**Date:** 2026-09-09  
**Module:** `integration.sensibo` (Sensibo Climate, read-only)  
**Verdict:** **SPRINT E NOT VERIFIED** — see [EMIC_SPRINT_E_VERIFICATION.md](EMIC_SPRINT_E_VERIFICATION.md)

---

## Summary

Sprint E delivered the first real external `.emicpkg` module (`integration.sensibo`) with selective per-module runtime authorization, broker provisioning, generic climate contracts, Store catalog entry, broker-backed onboarding, and an extended install wizard. Global `THIRD_PARTY_RUNTIME_ENABLED` remains off; control gate remains closed.

---

## Root architecture delivered

| Component | Status |
|-----------|--------|
| Per-module runtime authorization (`runtime_pilot_authorizations`) | Done |
| Broker provisioning from manifest `network_hosts` + site config | Done |
| `emic_runtime_sdk` GetSecret / NetworkRequest / PublishReadings | Done |
| Generic climate contracts + API + UI | Done |
| Standalone `modules/sensibo/` package (GET-only client) | Done |
| Signed `.emicpkg` fixture + Store catalog entry | Done |
| Sensibo onboard handler (broker-backed probe/discovery) | Done |
| Install wizard credential/connectivity/discovery/device steps | Done |
| `scripts/sprint-e-sensibo-acceptance.ps1` | Done |

---

## Security answers (Section 171)

| Question | Answer |
|----------|--------|
| Vendor-specific Core changes? | **NO** (generic climate/broker infrastructure only) |
| Internal EMIC imports in module runtime code? | **NO** |
| Direct network from module? | **NO** (Network Broker) |
| Direct DB/Redis from module? | **NO** |
| Credential outside Secret Broker? | **NO** |
| Write/control Sensibo API invoked? | **NO** (GET-only client) |
| General third-party runtime enabled? | **NO** |
| Control gate opened? | **NO** |

---

## Acceptance table

| Area | Result |
|------|--------|
| Standalone Sensibo module | PASS |
| No Sensibo logic in Core | PASS |
| Generic SDK/brokers | PASS |
| `.emicpkg` build + sign | PASS |
| Store catalog + preflight | PASS |
| Runtime authorization API + UI | PASS |
| Climate API + UI | PASS |
| External config + onboard handler | PASS |
| Install wizard Sensibo flow | PASS |
| Architecture guards (`network_hosts`, module imports) | PASS |
| Full regression `.\test-windows.ps1` | PASS (1727 Python + 747 frontend) |
| Linux isolated runtime E2E (Sensibo worker) | Pending Linux CI / prod |
| Prod real Sensibo read E2E | Pending operator (`sprint-e-sensibo-acceptance.ps1`) |

---

## Operator prod sequence

1. Deploy platform changes (`deploy-linux.ps1`)
2. Install signed `integration.sensibo` via Module Store
3. Configure site credential + selected devices (wizard or external-config API)
4. Grant exact runtime authorization (module, version, sha256, publisher, site)
5. Enable module for site; verify isolated worker + climate API/UI
6. Run `.\scripts\sprint-e-sensibo-acceptance.ps1 -BaseUrl <prod> -SiteSlug <site>`
7. Log review: no credential leakage, no write API paths

---

**Status:** SPRINT E NOT VERIFIED
