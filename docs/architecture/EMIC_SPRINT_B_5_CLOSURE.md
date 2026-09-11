# EMIC Sprint B.5 – Security Matrix & Production Closure

**Date:** 2026-09-08  
**Scope:** Close verification gaps B-V1 … B-V5; deploy Sprint B; migration 068; controlled prod acceptance  
**Production host:** `192.168.50.54`  
**Authoritative prior report:** [EMIC_SPRINT_B_VERIFICATION.md](./EMIC_SPRINT_B_VERIFICATION.md)

---

## 1. Executive Summary

Sprint B.5 closes the security test matrix gaps identified in independent verification, replaces the stub production acceptance script with a full controlled-fixture flow, deploys Sprint B to production, applies migration `068`, and passes controlled prod acceptance.

**Verdict:** **READY FOR SPRINT B RE-VERIFICATION**

Remote packages can be discovered, downloaded safely, verified, security-analyzed, and reach **STAGED / QUARANTINED** only. No third-party runtime execution. Control gate remains closed.

---

## 2. Finding Closure

| ID | Status | Evidence |
|----|--------|----------|
| **B-V1** | **CLOSED** | Sprint B deployed to `192.168.50.54`; `GET /api/modules/marketplace/catalog` → 200 (admin); migration head `068_marketplace_distribution_supply_chain` |
| **B-V2** | **CLOSED** | `scripts/sprint-b-prod-acceptance.ps1` — full controlled flow (auth, STAGED fetch, tamper 422, COMMUNITY/CRITICAL quarantine, control DENY, health) |
| **B-V3** | **CLOSED** | `test_ssrf_matrix.py` — full PUBLIC SSRF matrix (loopback, RFC1918, metadata IP, IPv6, forbidden schemes, credentials, DNS multi-address, redirect→private) |
| **B-V4** | **CLOSED** | `test_downloader_security.py`, `test_staging_security_matrix.py`, `test_advisory_withdrawal.py` — concurrent fetch, cache tamper, crash/partial safety, identity/advisory/break-glass matrices |
| **B-V5** | **CLOSED** | Remote archive matrix via staging integration (traversal, absolute paths, duplicates, too many entries, compression ratio) |
| **B-V6** | **INFO** | Unchanged — non-security skips remain outside distribution/supply_chain suites |

---

## 3. Sprint B.5 Acceptance Table

| Check | Result |
|-------|--------|
| **SPRINT B.5 CLOSURE** | |
| SSRF full matrix | **PASS** |
| DNS multi-address | **PASS** |
| Redirect→private | **PASS** |
| Concurrent fetch | **PASS** |
| Cache tamper | **PASS** |
| Crash safety | **PASS** |
| Partial-file safety | **PASS** |
| Remote archive traversal | **PASS** |
| Remote archive bomb | **PASS** |
| Remote identity mismatch | **PASS** |
| Remote version mismatch | **PASS** |
| Remote publisher mismatch | **PASS** |
| Remote ownership mismatch | **PASS** |
| Remote revoked key | **PASS** |
| COMMUNITY remote fetch | **PASS** |
| SBOM substitution | **PASS** |
| CRITICAL advisory staging | **PASS** |
| HIGH advisory review | **PASS** |
| Advisory withdrawal | **PASS** |
| Break-glass restrictions | **PASS** |
| 0 security-critical skips | **PASS** |
| Full regression | **PASS** |
| Migration 068 prod | **PASS** |
| Sprint B deployed prod | **PASS** |
| Distribution routes prod | **PASS** |
| Prod auth | **PASS** |
| Controlled signed fetch prod | **PASS** (STAGED) |
| Tamper rejection prod | **PASS** (HTTP 422) |
| COMMUNITY deny prod | **PASS** (QUARANTINED) |
| CRITICAL advisory prod | **PASS** (QUARANTINED) |
| Control gate prod | **PASS** (DENY) |
| No third-party runtime | **PASS** |
| Prod health | **PASS** |
| Prod runtime consistency | **PASS** |
| Prod logs | **PASS** |

---

## 4. Test Counts (Focused Matrix)

| Suite | Passed | Failed | Skipped |
|-------|--------|--------|---------|
| distribution | 49 | 0 | 0 |
| supply_chain | 10 | 0 | 0 |
| distribution API | 3 | 0 | 0 |
| architecture 5C guards | 8 | 0 | 0 |
| marketplace 5C.1 | 36 | 0 | 0 |
| Sprint A governance | 33 | 0 | 0 |
| Step 5B packages | 28 | 0 | 0 |
| **Focused subtotal** | **167** | **0** | **0** |

### Full regression

| Suite | Passed | Failed | Skipped |
|-------|--------|--------|---------|
| Python (`test-windows.ps1` / full pytest) | 1623 | 0 | 6 (non-security: redis/timescale/akarp) |
| Frontend (Vitest) | 733 | 0 | 0 |
| Architecture guards | 8 | 0 | 0 |

Mandatory Sprint B security suites: **0 skipped**.

---

## 5. Production Deployment

| Item | Status |
|------|--------|
| Host | `192.168.50.54` |
| Deploy script | `scripts/deploy-linux.ps1` |
| Alembic head | `068_marketplace_distribution_supply_chain` |
| Marketplace enabled | `MARKETPLACE_METADATA_ENABLED=true` (backend env wired in `docker-compose.yml`) |
| Acceptance | `scripts/sprint-b-prod-acceptance.ps1` → **SPRINT B PROD ACCEPTANCE PASS** |

Controlled fixtures only: signed `integration.demo` packages via `scripts/sign_demo_packages.py`; internal Docker fixture server `http://caddy:8080` (no public Internet fetch).

---

## 6. GO Criteria

| Criterion | Met |
|-----------|-----|
| B-V1 … B-V4 closed | ✓ |
| 0 BLOCKER / 0 unresolved HIGH | ✓ |
| All mandatory security tests PASS | ✓ |
| 0 security-critical skips | ✓ |
| Sprint B deployed + migration applied | ✓ |
| Prod acceptance PASS | ✓ |
| No third-party execution | ✓ |
| Control gate closed | ✓ |
| Prod health + runtime consistency PASS | ✓ |

**Status:** **READY FOR SPRINT B RE-VERIFICATION**

**Not in scope (unchanged):** Step 5C.5 runtime isolation, third-party runtime, public unrestricted marketplace, Sprint C implementation.

---

## 7. Key Artifacts Added/Updated

- `packages/energy-core/tests/platform/distribution/test_ssrf_matrix.py`
- `packages/energy-core/tests/platform/distribution/test_downloader_security.py`
- `packages/energy-core/tests/platform/distribution/test_staging_security_matrix.py`
- `packages/energy-core/tests/platform/supply_chain/test_advisory_withdrawal.py`
- `scripts/sprint-b-prod-acceptance.ps1` (full flow)
- `scripts/sprint-b-prod-setup-remote.py`
- `docker-compose.yml` — marketplace env vars, fixture volumes
- `Caddyfile` — `/sprint-b-fixtures/*`, internal `:8080` fixture server, LAN HTTPS
