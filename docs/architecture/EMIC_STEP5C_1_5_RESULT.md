# EMIC Step 5C.1.5 – Rollback, Revocation & Trust Cache Hardening Result

**Date:** 2026-09-07  
**Phase:** Step 5C.1.5 security hardening (post independent verification)  
**Prior verdict:** NO-GO FOR STEP 5C.2 (readiness 58/100)

---

## 1. Executive Summary

Step 5C.1.5 closes the independent verification blockers by adding **defense-in-depth rollback protection**:

- **Persistent python-tuf ngclient state** (`MARKETPLACE_TUF_STATE_PATH`) across syncs and restarts
- **Monotonic trust cache promotion gate** rejecting any role version regression
- **Revocation monotonic generation** with conservative merge and explicit `SUPERSEDE` semantics
- **Cache validation** → `MetadataHealth.INVALID` on corrupt payloads
- **Separate catalog/revocation freshness** timestamps
- **Process-local sync lock** with `SYNC_IN_PROGRESS` / HTTP 409
- **Stable error taxonomy** (`MetadataErrorCode`)
- **Automated network negative tests** (HTTPS prod, redirect, oversize, timeout)
- **Non-skipped v2→v1 rollback tests** with signed v1/v2 fixtures

Full regression and production health checks **PASS**.

---

## 2. Finding Closure

| ID | Status | Resolution |
|----|--------|------------|
| **B1** | **CLOSED** | `apply_sync_result()` monotonic gate; rollback leaves cache unchanged |
| **H1** | **CLOSED** | `test_rollback_snapshot_rejected` runs v2→v1 with real fixtures (not skipped) |
| **H2** | **CLOSED** | Persistent TUF state dir; ephemeral tmp dir removed |
| **H3** | **CLOSED** | `revocation_policy.py` — generation monotonicity, merge, SUPERSEDE |
| **H4** | **CLOSED** | Root rollback via integration + unit cache tests |
| **H5** | **CLOSED** | Targets rollback tests (TUF + cache) |
| **H6** | **CLOSED** | `test_marketplace_network_security.py` |
| **M1** | **CLOSED** | `_validate_cache_row()` → `INVALID` |
| **M2** | **CLOSED** | `catalog_updated_at` / `revocation_updated_at` |
| **M3** | **CLOSED** | `asyncio.Lock` in `sync_service.py` |
| **M4** | **CLOSED** | `marketplace.revocation_updated` audit on change |
| **M5** | **CLOSED** | `TrustMetadataUpdatedEvent` emitted post-commit |
| **M6** | **CLOSED** | `MetadataErrorCode` enum |

---

## 3. Baseline Regression

Via `.\test-windows.ps1` (2026-09-07):

| Suite | Collected | Passed | Failed | Skipped | Duration |
|-------|-----------|--------|--------|---------|----------|
| **Python** | 1522 | 1516 | 0 | 6 | ~480 s |
| **Frontend** | 726 | 726 | 0 | 0 | ~29 s |
| **Architecture** (Step 5C guards) | 3 | 3 | 0 | 0 | <1 s |
| **Step 5C.1 marketplace security** | 40 | 40 | 0 | **0** | ~9 s |

The 6 Python skips are pre-existing non-marketplace tests. **Zero security-critical Step 5C.1 skips.**

**Production health:** `scripts/verify-prod-health.ps1` — PASS  
**Production runtime consistency:** `scripts/verify-prod-runtime-consistency.ps1` — PASS

---

## 4. STEP 5C.1.5 ACCEPTANCE

| Item | Result |
|------|--------|
| Real python-tuf retained | **PASS** |
| Persistent cross-sync trust | **PASS** |
| Root v1→v2 | **PASS** |
| Root v2→v1 rejected | **PASS** |
| Timestamp rollback rejected | **PASS** |
| Snapshot v2→v1 rejected | **PASS** |
| Targets v2→v1 rejected | **PASS** |
| Cache monotonic version gate | **PASS** |
| Rollback leaves cache unchanged | **PASS** |
| Rollback does not increment generation | **PASS** |
| Revocation monotonic generation | **PASS** |
| Revocation rollback rejected | **PASS** |
| Revocation wipe prevented | **PASS** |
| Explicit supersession semantics | **PASS** |
| Cache corruption → INVALID | **PASS** |
| Invalid cache offline safe | **PASS** |
| Invalid cache online recovery | **PASS** (valid sync replaces invalid row) |
| Catalog freshness independent | **PASS** |
| Revocation freshness independent | **PASS** |
| Concurrent sync safe | **PASS** |
| Stable error taxonomy | **PASS** |
| revocation_updated audit | **PASS** |
| TrustMetadataUpdated emitted | **PASS** |
| HTTP prod rejected | **PASS** |
| Redirect rejected | **PASS** |
| Oversize rejected | **PASS** |
| Timeout safe | **PASS** |
| No artifact download | **PASS** |
| No remote install | **PASS** |
| No public Store | **PASS** |
| No third-party runtime | **PASS** |
| No runtime revocation side effects | **PASS** |
| Security critical skipped tests = 0 | **PASS** |
| Architecture guards | **PASS** |
| Step 5B regression | **PASS** |
| Multi-site E2E | **PASS** |
| Full regression | **PASS** |
| Performance | **PASS** (dormant mode unchanged) |
| Prod health | **PASS** |
| Prod runtime consistency | **PASS** |

---

## 5. Key Implementation Changes

| Area | Change |
|------|--------|
| `trust_cache.py` | Monotonic gate, revocation merge, cache validation, separate freshness |
| `tuf_client.py` | Persistent state dir, stable errors, redirect/oversize handling |
| `revocation_policy.py` | New — bundle schema, generation, SUPERSEDE merge |
| `sync_service.py` | Sync lock, rollback→REJECTED mapping, event emission |
| `types.py` | `MetadataErrorCode`, `MetadataHealth.DISABLED`, `ApplySyncResult` |
| Migration `066` | `catalog_updated_at`, `revocation_updated_at`, `revocation_generation`, `revocation_content_hash` |
| Fixtures | v1 + v2 signed metadata; `rollback_v1/` archive for adversarial tests |

---

## 6. Out of Scope (unchanged)

Step 5C.1.5 does **not** implement Step 5C.2 (Publisher Governance), remote artifact download, public Store, or third-party runtime.

---

## 7. Next Step

Independent re-verification of Step 5C.1 with adversarial audit (Step 5C.1 verification rerun).

READY FOR STEP 5C.1 RE-VERIFICATION
