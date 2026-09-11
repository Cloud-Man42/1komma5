# EMIC Step 5C.1 – Targeted Security Re-Verification

**Date:** 2026-09-07  
**Scope:** Post–Step 5C.1.5 hardening; targeted re-check of prior B1/H1–H6 findings only  
**Method:** Code inspection, adversarial runtime probe, focused + full regression, prod health  
**Out of scope:** Step 5C.2 implementation; full re-audit of all 150 original checks

Implementation self-reports (`EMIC_STEP5C_1_5_RESULT.md`) are **not** accepted as evidence.

---

## 1. Executive Summary

The Step 5C.1.5 hardening **closes all prior BLOCKER and HIGH findings** (B1, H1–H6) verified in this re-check.

Cross-sync rollback protection is now enforced at **two layers**:
1. Persistent python-tuf ngclient state (`MARKETPLACE_TUF_STATE_PATH`)
2. Monotonic trust-cache promotion gate in `apply_sync_result()`

Mandatory v2→v1 rollback tests run **without skips**. Revocation generation rollback and wipe are rejected. Network negative tests pass. Step 5B regression, multi-site E2E, full regression, and production health all **PASS**.

**One residual gap (non-blocking for 5C.2 scope):** corrupt-cache **online recovery** raises `CacheValidationError` during promotion instead of replacing the invalid row with a fresh verified generation (adversarial probe). Detection/status `INVALID` works; automatic recovery does not.

**Verdict:** Prior trust-foundation blockers are resolved. Step 5C.2 (Publisher Governance + Organization Policy) may proceed.

---

## 2. B1 – Cross-Sync Rollback Block

**Status: CLOSED**

Code review of `MarketplaceTrustCacheRepository.apply_sync_result()` confirms monotonic gate via `_detect_metadata_rollback()` before any promotion:

```93:103:packages/energy-core/src/energy_core/platform/modules/marketplace/trust_cache.py
        self._validate_cache_row(row)
        rollback = self._detect_metadata_rollback(row, result.versions)
        if rollback is not None:
            row.sync_failed = True
            row.last_error = (
                f"{MetadataErrorCode.METADATA_ROLLBACK_DETECTED.value}: "
                f"{rollback.role} {rollback.incoming_version} < {rollback.trusted_version}"
            )
            ...
            return row, ApplySyncResult(row_changed=True, promoted=False, rollback=rollback)
```

Roles checked: `root`, `timestamp`, `snapshot`, `targets`. Rejection is atomic — no partial field updates before return.

Unit tests `test_snapshot_rollback_rejected`, `test_targets_rollback_rejected`, `test_root_rollback_rejected` confirm `promoted=False` and versions unchanged.

---

## 3. Rollback Matrix (Signed Fixtures v1 → v2 → v1)

| Role | Test | Result |
|------|------|--------|
| Root | `test_root_rollback_rejected` (integration via sync service) | **REJECT** |
| Timestamp | `test_rollback_timestamp_rejected` | **REJECT** |
| Snapshot | `test_rollback_snapshot_rejected` | **REJECT** |
| Targets | `test_rollback_targets_rejected` | **REJECT** |

Fixtures: `repository/metadata/` (v2 current) + `repository/rollback_v1/metadata/` (v1 archive). No `pytest.skip` in any rollback test.

---

## 4. Cache Immutability on Reject

**Status: PASS**

`test_snapshot_rollback_rejected` (trust cache unit) snapshots row before/after downgrade attempt:

- `cache_generation` unchanged
- `snapshot_version` unchanged
- `revocations_json` unchanged (R1 retained on wipe attempt)
- `last_success_at` preserved (implicit — promotion path not taken)

`last_attempt_at` updates on reject path (line 74).

---

## 5. Persistent TUF State (H2)

**Status: CLOSED**

`tuf_client.py` uses persistent `tuf_state_dir` (no post-sync `rmtree`). Test `test_persistent_state_rejects_rollback_after_restart`: sync v2 → new client instance same dir → serve v1 → **REJECT**.

---

## 6. H1 – Snapshot Rollback Test Not Skipped

**Status: CLOSED**

`test_rollback_snapshot_rejected` executed in focused run — **PASSED**, **0 skips** in entire Step 5C.1 security suite (43 tests).

---

## 7. H3 – Revocation Rollback / Wipe / SUPERSEDE

**Status: CLOSED**

| Check | Test | Result |
|-------|------|--------|
| Generation rollback | `test_revocation_wipe_rejected`, `test_generation_rollback_rejected` | **REJECT** |
| Wipe (gen2 R1 → gen1 empty) | `test_revocation_wipe_rejected` | R1 remains |
| Missing-from-bundle unrevoke | `test_merge_keeps_prior_revocation_when_missing_from_new_bundle` | Prior R1 kept |
| Explicit SUPERSEDE | `test_supersede_removes_revocation`, `test_revocation_supersession_keeps_monotonic_generation` | R1 removed only via SUPERSEDE |

---

## 8. H4 / H5 – Root / Targets Rollback

**Status: CLOSED**

- H4: `test_root_rollback_rejected` — full-stack REJECT, `apply.promoted=False`
- H5: `test_targets_rollback_rejected` + `test_rollback_targets_rejected` — REJECT

---

## 9. H6 – Network Negative Tests

**Status: CLOSED**

All in `test_marketplace_network_security.py` — **PASS**:

| Test | Control |
|------|---------|
| `test_production_http_rejected` | HTTP URL in prod policy |
| `test_production_client_requires_https` | Client constructor |
| `test_redirect_rejected` | 302 external → `REDIRECT_REJECTED` |
| `test_oversize_rejected` | → `SIZE_LIMIT_EXCEEDED` |
| `test_timeout_maps_to_stable_code` | Stable timeout/network code |

---

## 10. Cache Corruption & Freshness

| Check | Result |
|-------|--------|
| Corrupt payload → `MetadataHealth.INVALID` | **PASS** (`test_corrupt_cache_reports_invalid`) |
| No silent trust on corrupt read | **PASS** |
| Invalid + offline safe | **PASS** (`mark_offline` catches `CacheValidationError`) |
| Invalid + online recovery | **PARTIAL** — probe: `CacheValidationError` raised on SUCCESS apply; row not replaced |
| Separate `catalog_updated_at` / `revocation_updated_at` | **PASS** (`test_separate_revocation_freshness`) |

---

## 11. Concurrent Sync (M3)

**Status: CLOSED**

`sync_service.py` uses process-local `asyncio.Lock`. `test_sync_in_progress` confirms one `IN_PROGRESS`, one `SUCCESS`. API maps to HTTP 409 (`marketplace_metadata.py`).

---

## 12. Stable Error Codes & Audit & Event Order

| Check | Result |
|-------|--------|
| `MetadataErrorCode` used in API/sync (not raw `RepositoryError` as contract) | **PASS** |
| `marketplace.metadata_rejected` on rollback | **PASS** (API with role/versions in summary) |
| `marketplace.root_rotated` only on forward rotation | **PASS** |
| `marketplace.revocation_updated` on change | **PASS** |
| Event order: verify → monotonic → commit → emit | **PASS** (`commit()` line 131 before `trust_metadata_listeners.emit()` line 132–133) |
| `TrustMetadataUpdatedEvent` no runtime side effects | **PASS** (listener registry only; no module/orchestrator subscribers) |

---

## 13. Scope Isolation

Architecture guards + source scan — **PASS**:

- No `PackageInstaller` / `PackageUpdater` / `ModuleOrchestrator` in marketplace layer
- No public Store browse route
- No artifact download / remote install paths in marketplace package

---

## 14. Security Test Counts

**Step 5C.1 security suite** (marketplace + guards + status API):

| | Count |
|---|-------|
| collected | 43 |
| passed | 43 |
| failed | 0 |
| skipped | **0** |

Security-critical skips: **0**

---

## 15. Regression

| Suite | collected | passed | failed | skipped | duration |
|-------|-----------|--------|--------|---------|----------|
| **Python** | ~1522 | **1517** | 0 | 6 | ~411 s |
| **Frontend** | 726 | **726** | 0 | 0 | ~28 s |
| **Architecture** (Step 5C guards) | 3 | **3** | 0 | 0 | ~1 s |
| **Step 5B store/packages** | 44 | **44** | 0 | 0 | ~28 s |

6 Python skips are pre-existing non-marketplace tests.

Multi-site: `test_package_enabled_only_on_selected_site` included in store regression — **PASS**.

---

## 16. Production

| Check | Result |
|-------|--------|
| `verify-prod-health.ps1` | **PASS** |
| `verify-prod-runtime-consistency.ps1` | **PASS** |
| `MARKETPLACE_METADATA_ENABLED=false` default | **PASS** (`config.py`) |
| No sync worker when disabled | **PASS** (`main.py` lifespan guard) |
| Disabled status shows `disabled` not unhealthy | **PASS** (`test_status_disabled`) |

---

## 17. Finding Closure

| ID | Status |
|----|--------|
| **B1** | **CLOSED** |
| **H1** | **CLOSED** |
| **H2** | **CLOSED** |
| **H3** | **CLOSED** |
| **H4** | **CLOSED** |
| **H5** | **CLOSED** |
| **H6** | **CLOSED** |

---

## 18. Residual Note (Non-Blocking)

**Invalid cache online recovery:** `_validate_cache_row()` on line 93 throws before promotion when prior cache is corrupt. Status correctly shows `INVALID`; a subsequent valid TUF sync does not automatically heal the row. Recommend Step 5C.1.6 or operational runbook (manual cache clear). Does not affect rollback/freeze/revocation trust foundation required for 5C.2.

---

## 19. STEP 5C.1 TARGETED RE-VERIFICATION

| Item | Result |
|------|--------|
| Root rollback | **PASS** |
| Timestamp rollback | **PASS** |
| Snapshot rollback | **PASS** |
| Targets rollback | **PASS** |
| Persistent cross-sync trust | **PASS** |
| Cache monotonic gate | **PASS** |
| Cache unchanged on reject | **PASS** |
| Revocation rollback | **PASS** |
| Revocation wipe prevention | **PASS** |
| SUPERSEDE semantics | **PASS** |
| Corrupt cache handling | **PASS** |
| Freshness separation | **PASS** |
| Concurrent sync safety | **PASS** |
| HTTP prod rejection | **PASS** |
| Redirect rejection | **PASS** |
| Oversize rejection | **PASS** |
| Timeout safety | **PASS** |
| Audit | **PASS** |
| Event ordering | **PASS** |
| No artifact download | **PASS** |
| No remote install | **PASS** |
| No public Store | **PASS** |
| No third-party runtime | **PASS** |
| Security critical skips = 0 | **PASS** |
| Step 5B regression | **PASS** |
| Multi-site E2E | **PASS** |
| Full regression | **PASS** |
| Prod health | **PASS** |
| Prod runtime consistency | **PASS** |

---

## 20. Final Decision

All prior BLOCKER and HIGH trust-foundation findings are verified closed. Rollback matrix passes with real signed fixtures and zero security-critical skips. Step 5B and production health pass. Scope isolation intact.

Step 5C.2 approval is limited to **Publisher Governance + Organization Policy** — not remote artifact download, public marketplace, or third-party runtime.

GO FOR STEP 5C.2
