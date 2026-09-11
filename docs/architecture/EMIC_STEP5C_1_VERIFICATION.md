# EMIC Step 5C.1 – Independent Security & Implementation Verification

**Date:** 2026-09-07  
**Verifier:** Independent adversarial audit (code, tests, runtime probes, docs cross-check)  
**Scope:** Step 5C.1 only — metadata trust channel, trust cache, admin API, background sync  
**Out of scope:** Step 5C.2 implementation, remote artifact download, public marketplace

**Primary question:**

> Has EMIC Step 5C.1 established a cryptographically verifiable, rollback-/freeze-resistant and offline-tolerant metadata trust channel **without** introducing remote package installation or third-party execution?

**Answer:** **Partially.** Real TUF verification exists within a single sync operation, and scope isolation is clean. However, **cross-sync rollback protection at the trust-cache promotion layer is missing**, mandatory v2→v1 rollback tests were not executed, and revocation downgrade/wipe is possible if older signed metadata is accepted by TUF on a fresh ephemeral updater bootstrap.

**Implementation self-report (`EMIC_STEP5C_1_RESULT.md`) is not accepted as evidence.** Several claimed PASS items were disproven below.

---

## 1. Executive Summary

Step 5C.1 delivers a **dormant, metadata-only foundation** using **python-tuf 7.0.1** (`Updater.refresh()`), pinned offline root bootstrap, DB trust cache, admin status/sync API, and background sync with backoff. Architecture guards confirm **no coupling to PackageInstaller or ModuleOrchestrator**. Step 5B Internal Store regression passes.

**Critical gap:** `MarketplaceTrustCacheRepository.apply_sync_result()` promotes any `SyncOutcome.SUCCESS` without comparing new role versions to the last trusted cache. An independent audit probe demonstrated:

- Snapshot/targets/root versions can be **downgraded** in the DB cache (v2 → v1 accepted).
- Revocation data can be **wiped** (prior revocation entry replaced by empty bundle).

Because `MarketplaceMetadataClient` uses a **fresh ephemeral TUF working directory on every sync** (destroyed after each call), cross-sync rollback protection **must** be enforced at cache promotion. It is not.

**Verdict:** **NO-GO FOR STEP 5C.2** until Step 5C.1.5 hardening closes blockers below.

---

## 2. Scope

Verified:

- TUF metadata client, trust cache, sync service, admin API, background worker
- Security tests, architecture guards, Step 5B store/package regression
- Documentation (TUF model, root IR, threat/trust updates)
- Production dormant defaults

Not verified as sufficient (gaps listed in findings):

- Full staging acceptance flow (used local audit fixtures instead)
- Live production deployment inspection (config defaults verified in code only)

---

## 3. Baseline Regression

Full suite via `.\test-windows.ps1` (2026-09-07):

| Suite | Collected | Passed | Failed | Skipped | Duration |
|-------|-----------|--------|--------|---------|----------|
| **Python** (energy-core + backend + collector) | 1501 | 1494 | 0 | 7 | ~406–432 s |
| **Frontend** (Vitest) | 726 tests / 154 files | 726 | 0 | 0 | ~29 s |
| **Windows client** (dotnet) | (included in script) | PASS | 0 | — | included |
| **Architecture** (Step 5C guards) | 3 | 3 | 0 | 0 | <1 s |
| **Package** (platform/packages + module_packages API) | ~56 | 55+ | 0 | 0 | ~82 s |
| **Store** (module_store API + frontend store tests) | ~17 | 17 | 0 | 0 | included |
| **Security** (marketplace TUF + trust cache + guards) | 18 | 17 | 0 | **1** | ~4 s |
| **Step 5C.1** (marketplace + guards + status API) | 21 | 20 | 0 | **1** | ~4 s |

**Regression classification:** No functional regressions detected. **Security regression:** one security-critical test permanently skipped (see §35).

---

## 4. TUF Library Verification

| Check | Result |
|-------|--------|
| Dependency declared | `tuf>=4.0` in `packages/energy-core/pyproject.toml` |
| Installed version | **tuf 7.0.1** (verified via `importlib.metadata`) |
| Uses `Updater.refresh()` | **YES** — `tuf_client.py` |
| Custom crypto shortcuts | **NO** — verification delegated to ngclient |
| Ad hoc half-TUF protocol | **NO** |

**Assessment:** Real python-tuf is used for in-sync verification. **PASS** for library choice.

---

## 5. Root Bootstrap

| Check | Result |
|-------|--------|
| Initial root source | File path `MARKETPLACE_TRUSTED_ROOT_PATH` / dev fallback to test fixture |
| Downloaded root blindly trusted | **NO** — `bootstrap=pinned_root_bytes` passed to `Updater` |
| Private root keys in runtime | **NO** |
| Private root keys in repo | **NO** — only signed public metadata in fixtures; `TEST_ONLY.txt` marker present |
| Generator creates ephemeral keys | `generate_fixtures.py` uses `CryptoSigner.generate_ed25519()` at generation time; private keys **not committed** |

**Assessment:** **PASS** for pinned bootstrap model.

---

## 6. Root Rotation

| Test | Result |
|------|--------|
| N → N+1 with pinned v1 bootstrap | **PASS** — `test_root_rotation_accepted`, sync ends `root_version==2`, `2.root.json` in fixtures |
| N → N+2 skip | Not tested |
| Threshold >1 | **N/A** — threshold=1 in fixtures; documented |

---

## 7. Root Rollback

| Test | Result |
|------|--------|
| N+1 accepted then serve N | **NOT TESTED** in suite |
| Trust cache monotonic root gate | **MISSING** — audit: DB accepts `root_version` downgrade 2→1 on SUCCESS |

**Assessment:** **FAIL** — root rollback protection not demonstrated; cache layer vulnerable.

---

## 8. Timestamp / Freeze Protection

| Test | Result |
|------|--------|
| Expired timestamp rejected | **PASS** — `test_expired_timestamp_rejected` |
| Failed sync retains prior cache | **PASS** — trust cache + TUF client tests |
| Timestamp rollback after newer accepted | **NOT TESTED** |
| Freeze → stale/expired status | **PARTIAL** — expiry computed from cached `metadata_expires_at`; no live runtime quarantine (by design) |

---

## 9. Snapshot / Rollback

| Test | Result |
|------|--------|
| Corrupt snapshot bytes | **PASS** — `test_mix_and_match_snapshot_rejected` |
| **v2 accept → v1 serve (signed rollback)** | **FAIL** |
| Production test | **SKIPPED** — `test_rollback_snapshot_rejected` skips when fixture version==1 |
| Independent audit fixture (temp, not prod) | v2 accepted; v1 re-serve → **SUCCESS** (no reject) |

**Assessment:** **FAIL** — mandatory v2→v1 snapshot rollback not proven. Implementation report’s “partial PASS” **rejected**.

---

## 10. Targets / Rollback

| Test | Result |
|------|--------|
| v2 → v1 targets rollback | **NOT TESTED** |
| Trust cache targets downgrade | **FAIL** — audit accepts `targets_version` 2→1 |

---

## 11. Mix-and-Match

| Test | Result |
|------|--------|
| Timestamp/snapshot hash mismatch (corruption) | **PASS** — `test_mix_and_match_snapshot_rejected` |
| Cross-role valid sigs, incompatible refs (full adversarial) | **PARTIAL** — corruption-based, not fully re-signed adversarial fixture |

---

## 12. Catalog Verification

| Check | Result |
|-------|--------|
| Catalog only after `Updater.refresh()` + target download | **YES** |
| Allowed path allowlist | **YES** — `emic/catalog.json` only |
| `.emicpkg` download path | **NONE** |

**Assessment:** **PASS** within single sync.

---

## 13. Revocation Verification

| Check | Result |
|-------|--------|
| Revocation via TUF target `emic/revocations.json` | **YES** |
| Unsigned API revocation | **NONE** |
| Merge semantics | **NO** — full JSON replace on each successful sync |

---

## 14. Revocation Rollback / Unrevoke

| Test | Result |
|------|--------|
| Revocation generation N+1 → N | **NOT TESTED** |
| Empty revocation bundle replacing prior revocations | **FAIL** — audit: prior revocation entry removed when older SUCCESS applied |
| `marketplace.revocation_updated` audit | **NOT IMPLEMENTED** (documented as future) |

**Assessment:** **FAIL** — revocation rollback safety not demonstrated; wipe risk at cache layer.

---

## 15. Trust Cache

- Model: `marketplace_trust_cache` table, single `cache_key=default` row
- Stores role versions, catalog/revocation JSON, expiry, sync timestamps, `cache_generation`
- `MetadataHealth.INVALID` enum exists but **never assigned** in code

---

## 16. Atomic Promotion

| Check | Result |
|-------|--------|
| Verify before in-memory SUCCESS | **YES** — TUF client returns SUCCESS only after full chain + both targets |
| DB write | Single-row update in one transaction + `commit()` |
| Monotonic version gate before write | **NO** — **BLOCKER** |
| Partial catalog OK / revocation fail | **SAFE at client** — both targets required before SUCCESS |
| Crash mid-transaction | SQLAlchemy single commit; no multi-table split — **acceptable for one row** |

---

## 17. Cache Corruption

| Scenario | Result |
|----------|--------|
| Corrupt JSON in DB | **NOT HANDLED** — no integrity MAC/signature on cache row; `INVALID` never set |
| Parse on read | Only via `parse_catalog`/`parse_revocations` helpers — not used by status API |

**Assessment:** **PARTIAL / FAIL** for corrupt-cache semantics.

---

## 18. Offline Semantics

| Scenario | Result |
|----------|--------|
| Valid cache + network down | **PASS** — `mark_offline`, prior cache retained (unit test) |
| Stale cache | **PASS** — `_compute_states` age thresholds |
| Expired metadata | **PASS** — `EXPIRED` when `now >= metadata_expires_at` |
| First boot offline | **PASS** — `UNINITIALIZED`/`UNAVAILABLE` when no `last_success_at` |
| EMIC core startup blocked | **PASS** — sync in background task; disabled by default |

---

## 19. Staleness

| State | Implemented |
|-------|-------------|
| HEALTHY / STALE / EXPIRED / OFFLINE / UNINITIALIZED / UNAVAILABLE | **YES** |
| INVALID | **NO** (dead enum) |
| Separate revocation freshness | **PARTIAL** — separate enum but `revocation_age_seconds` mirrors `catalog_age_seconds`; revocation can be STALE while catalog STALE at same age only |

---

## 20. Clock Handling

- Uses `datetime.now(UTC)` in trust cache
- TUF expiry enforced by python-tuf during refresh
- **No clock-skew tolerance policy in code**
- Host clock manipulation can affect staleness/expiry reporting — **MEDIUM** operational risk

---

## 21. Network Security

| Control | Code | Automated test |
|---------|------|----------------|
| HTTPS required in production | **YES** — `AppEnvironment.PRODUCTION` | **NO** |
| No redirects | **YES** — `follow_redirects=False` | **NO** |
| Connect/read timeouts | **YES** — httpx + settings | **NO** |
| Max metadata bytes | **YES** — fetcher check | **NO** |
| Oversized payload | **NOT TESTED** |
| Redirect attack | **NOT TESTED** |

---

## 22. Size Limits

Implemented in `HttpxFetcher` (`max_bytes`). **No negative tests** in Step 5C.1 suite.

---

## 23. Status API

| Check | Result |
|-------|--------|
| Route | `GET /api/modules/marketplace/status` |
| Anonymous | **401** — tested |
| Admin | **200** — tested |
| Secret/path leakage | **PASS** — response fields are operational metadata only |
| Disabled vs unhealthy | **PARTIAL** — `enabled=false` from settings; cache health may still show `uninitialized` |

---

## 24. Sync API

| Check | Result |
|-------|--------|
| Route | `POST /api/modules/marketplace/sync` |
| Admin auth | **YES** — tested |
| Disabled → 503 | **YES** |
| Concurrent sync lock | **NO** — no mutex; parallel syncs possible |
| Raw stack traces | **PASS** — message string only |

---

## 25. Background Worker

- Starts only if `marketplace_metadata_enabled` (`main.py` lifespan)
- Backoff + jitter on failure (`marketplace_sync.py`)
- Runs in asyncio task — does not block startup when disabled
- Sync work in `asyncio.to_thread` — **PASS** for event-loop isolation

---

## 26. Audit

| Event | Implemented |
|-------|-------------|
| `marketplace.sync_started` | **YES** |
| `marketplace.sync_succeeded` | **YES** |
| `marketplace.sync_failed` | **YES** |
| `marketplace.root_rotated` | **YES** (on version increase) |
| `marketplace.metadata_rejected` | **YES** |
| `marketplace.revocation_updated` | **NO** |
| Audit failure blocks promotion | **NO** — promotion already committed in same request flow after sync |

---

## 27. Root Compromise IR

Document `EMIC_MARKETPLACE_ROOT_KEY_IR.md` covers detection, containment, rotation, OOB reset, air-gap, grace policy, audit, comms. **PASS** for Step 5C.1 documentation scope.

Break-glass root reset: requires local admin + offline artifact — **not remotely triggerable by Marketplace API** (code review **PASS**).

---

## 28. Architecture Guards

| Guard | Result |
|-------|--------|
| No PackageInstaller in marketplace layer | **PASS** — static test |
| No ModuleOrchestrator | **PASS** |
| No public store browse route | **PASS** |
| Dynamic import bypass scan | **NONE found** in marketplace package |

---

## 29. Scope Leak Scan

| Path | Result |
|------|--------|
| Remote `.emicpkg` download | **NONE** |
| `artifact_url` / `package_url` fetch in marketplace layer | **NONE** |
| Marketplace → PackageInstaller | **NONE** |
| Public Store UI routes | **NONE** |
| Third-party runtime enablement | **NONE** |
| Marketplace DB beyond trust cache | **NONE** |

---

## 30. Step 5B Regression

Internal Store upload/validate/install/update/rollback/remove, publisher trust, quarantine — **PASS** (module_store + module_packages tests; full regression green).

---

## 31. Multi-site E2E

`test_package_enabled_only_on_selected_site` — package global, Åkarp enabled, Denmark disabled — **PASS**.

---

## 32. Frontend Debt

| Test file | Result |
|-----------|--------|
| `PublishersPanel.test.tsx` | **PASS** (2 tests) |
| `PackageStoreDetailPanel.test.tsx` | **PASS** (3 tests) |
| `ModuleStoreOverview` marketplace status | **PASS** |

---

## 33. Performance

- Dormant mode (`MARKETPLACE_METADATA_ENABLED=false`): no sync task — **near-zero overhead**
- Sync in thread pool — collector/dashboard not blocked in code review
- No memory retention of TUF temp dirs (deleted each sync)

---

## 34. Production Deployment

| Check | Result |
|-------|--------|
| Default `MARKETPLACE_METADATA_ENABLED=false` | **YES** — `config.py` |
| Prod health scripts exist | `scripts/verify-prod-health.ps1`, `verify-prod-runtime-consistency.ps1` |
| Live prod run in this audit | **NOT EXECUTED** (environment not available) |

---

## 35. Security Test Quality

| Test | Would fail if control removed? |
|------|-------------------------------|
| `test_expired_timestamp_rejected` | **YES** |
| `test_bad_signature_rejected` | **YES** |
| `test_unknown_root_rejected` | **YES** |
| `test_mix_and_match_snapshot_rejected` | **YES** (corruption) |
| `test_rollback_snapshot_rejected` | **N/A — SKIPPED** |
| Trust cache failed sync retention | **YES** |
| Mock bypass of TUF | **NO** — real `Updater` used against HTTP fixture |

### All skips in Step 5C.1 security tests

| Test | Reason | Security impact | Required before 5C.2? |
|------|--------|-----------------|------------------------|
| `test_rollback_snapshot_rejected` | Fixture snapshot version==1 | **HIGH** — rollback protection unproven | **YES** |

---

## 36. Previous Finding Status (Design Verification)

| ID | Status | Notes |
|----|--------|-------|
| **H-03** (real TUF) | **PARTIAL** | python-tuf used; cache-layer rollback breaks TUF guarantees cross-sync |
| **H-01** (execution gate doc) | **CLOSED (doc)** | Trust model §3.2 execution gate added |
| **H-02** (subprocess isolation) | **OPEN** | Correctly not claimed solved |
| **M-01** advisory trust | **DOC ONLY** | Future signed-metadata requirement documented |
| **M-03** ownership transfer | **DOC STUB** | |
| **M-04** SSRF/redirect/DNS/freeze | **PARTIAL** | Threats T33–T36 added; redirect/size tests missing |
| **M-05** root IR | **CLOSED (doc)** | |
| **M-06** policy enum | **DOC STUB** | |
| **M-07** TLS policy | **PARTIAL** | Documented + prod HTTPS in code; not fully tested |

---

## 37. New Findings

### BLOCKER

| ID | Finding |
|----|---------|
| **B1** | **Trust cache promotes metadata rollback.** `apply_sync_result()` accepts SUCCESS without enforcing `new_version >= cached_version` for root/timestamp/snapshot/targets. Audit: v2 cache overwritten by v1 SUCCESS; revocations wiped. Violates GO criterion “Metadata rollback protection PASS”. |

### HIGH

| ID | Finding |
|----|---------|
| **H1** | Mandatory **snapshot v2→v1** test **skipped** in CI; independent audit shows downgrade accepted at client+cache when v1 re-served after v2. |
| **H2** | **Ephemeral TUF state** — `MarketplaceMetadataClient` deletes ngclient metadata dir after each sync; cross-sync rollback protection must live in trust cache but does not. |
| **H3** | **Revocation rollback / unrevoke** — full replace semantics; no monotonic bundle version merge; attacker serving older signed empty bundle can clear revocations if TUF accepts downgrade. |
| **H4** | **Root rollback N+1→N** not tested; cache accepts root version downgrade. |
| **H5** | **Targets v2→v1** not tested; cache accepts targets version downgrade. |
| **H6** | Network hardening (HTTPS prod, redirect, oversize) implemented but **not covered by automated negative tests**. |

### MEDIUM

| ID | Finding |
|----|---------|
| **M1** | `MetadataHealth.INVALID` never set; corrupt cache not detected authoritatively. |
| **M2** | `revocation_age_seconds` duplicates `catalog_age_seconds` — not independently sourced. |
| **M3** | No concurrent sync serialization. |
| **M4** | `marketplace.revocation_updated` audit event documented but not emitted. |
| **M5** | `TrustMetadataUpdatedEvent` defined, never emitted (hook only). |
| **M6** | Error taxonomy uses exception class names (`RepositoryError`, `DownloadHTTPError`) not stable policy codes. |

### LOW / INFO

| ID | Finding |
|----|---------|
| **L1** | `pinned_root_version` DB column unused. |
| **I1** | Fixture generator regenerates keys each run — committed signatures tied to generation run; operational doc OK with TEST_ONLY. |

---

## 38. Readiness Scores (0–100)

| Area | Score |
|------|-------|
| TUF Correctness (in-sync) | 82 |
| Root Bootstrap | 90 |
| Root Rotation | 75 |
| Root Rollback Protection | **25** |
| Timestamp / Freeze Protection | 70 |
| Snapshot Integrity | 55 |
| Targets Integrity | 55 |
| Mix-and-Match Protection | 65 |
| Catalog Verification | 85 |
| Revocation Verification | 60 |
| Revocation Rollback Safety | **20** |
| Trust Cache | 50 |
| Atomic Promotion | 55 |
| Offline Semantics | 80 |
| Staleness | 70 |
| Clock Handling | 55 |
| Network Hardening | 60 |
| Size Limits | 50 |
| API Security | 85 |
| Audit | 70 |
| Architecture Isolation | 95 |
| No Package Execution | 95 |
| Step 5B Compatibility | 90 |
| Multi-site Regression | 85 |
| Performance | 85 |
| Production Safety (dormant) | 85 |
| Security Test Quality | **45** |
| Documentation | 80 |
| Incident Recovery | 75 |

**STEP 5C.1 READINESS SCORE: 58 / 100**

---

## 39. Required Fixes (Step 5C.1.5 — do not implement in this audit)

| Priority | Fix | Retest |
|----------|-----|--------|
| **B1** | Monotonic version gate in `apply_sync_result()` (reject SUCCESS if any role version regresses vs cache; emit `metadata_rejected` / do not increment generation) | v2→v1 snapshot/targets/root; cache unchanged |
| **H3** | Revocation merge policy — monotonic bundle version; reject shrink/wipe unless explicit supersession rules | unrevoke scenario |
| **H1/H2** | Add v2 fixtures + **non-skipped** snapshot/targets rollback tests | security suite |
| **H4/H5** | Root rollback test N+1→N | security suite |
| **M1** | Corrupt cache → `INVALID` / safe parse | trust cache test |
| **H6** | Negative tests: oversize, redirect, HTTP in prod | security suite |

---

## 40. STEP 5C.1 INDEPENDENT VERIFICATION

| Item | Result |
|------|--------|
| Real python-tuf | **PASS** |
| Standard TUF verification path | **PASS** (in-sync) |
| Pinned root bootstrap | **PASS** |
| No private prod root key | **PASS** |
| Root rotation N→N+1 | **PASS** |
| Root rollback N+1→N rejected | **FAIL** |
| Invalid root rotation rejected | **PARTIAL** (not explicitly tested) |
| Timestamp verification | **PASS** |
| Freeze attack rejected | **PASS** |
| Timestamp rollback rejected | **FAIL** (not tested) |
| Snapshot verification | **PASS** (in-sync) |
| Snapshot v2→v1 rollback rejected | **FAIL** |
| Targets verification | **PASS** (in-sync) |
| Targets v2→v1 rollback rejected | **FAIL** |
| Mix-and-match rejected | **PARTIAL** |
| Catalog verification | **PASS** |
| Revocation verification | **PASS** (in-sync) |
| Revocation rollback safety | **FAIL** |
| Verify-before-cache | **PASS** (in-memory) |
| Atomic cache promotion | **PARTIAL** |
| Partial sync safety | **PASS** |
| Crash promotion safety | **PARTIAL** |
| Cache corruption safety | **FAIL** |
| Valid-cache offline | **PASS** |
| Stale-cache offline | **PASS** |
| Expired-cache offline | **PASS** |
| First-boot offline | **PASS** |
| Catalog/revocation freshness separate | **PARTIAL** |
| Clock handling | **PARTIAL** |
| Status API admin auth | **PASS** |
| Sync API admin auth | **PASS** |
| No secret/path leakage | **PASS** |
| Background sync | **PASS** |
| Disabled means no network | **PASS** |
| Backoff/jitter | **PASS** (code) |
| Timeouts | **PASS** (code) |
| Size limits | **PARTIAL** |
| Redirect policy | **PARTIAL** |
| HTTPS production policy | **PARTIAL** |
| Audit | **PARTIAL** |
| Root compromise IR | **PASS** |
| No PackageInstaller coupling | **PASS** |
| No artifact download | **PASS** |
| No remote package install | **PASS** |
| No public Store UI | **PASS** |
| No third-party runtime | **PASS** |
| No runtime revocation side effects | **PASS** |
| Step 5B regression | **PASS** |
| Package multi-site E2E | **PASS** |
| Frontend Store debt | **PASS** |
| Performance | **PASS** |
| Prod dormant config | **PASS** |
| Prod health | **NOT RUN** |
| Prod runtime consistency | **NOT RUN** |
| Security test quality | **FAIL** |
| No security-critical skipped tests | **FAIL** |

---

## 41. Final Decision

Step 5C.1 establishes a **credible in-sync TUF metadata verifier** and a **clean dormant foundation**, but **does not yet provide cross-sync rollback- or revocation-safe trust cache promotion**. The implementation’s own “rollback protection PASS (partial skip)” is **insufficient**.

**5C.2 (Publisher Governance + Organization Policy) must not start until Step 5C.1.5 closes B1 and HIGH rollback/revocation items.**

NO-GO FOR STEP 5C.2
