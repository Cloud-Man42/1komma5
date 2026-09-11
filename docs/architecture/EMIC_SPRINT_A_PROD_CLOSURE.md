# EMIC Sprint A – Production Closure Report

**Date:** 2026-09-08  
**Scope:** Close B1/B2, M1/M2/M3, deploy Step 5C.2 to production, prod dry-runs, full regression  
**Production host:** `192.168.50.54`  
**Authoritative prior report:** [EMIC_SPRINT_A_VERIFICATION.md](./EMIC_SPRINT_A_VERIFICATION.md)

---

## 1. Executive Summary

Sprint A production gate closure is **complete**. Step 5C.2 (Publisher Governance + Organization Policy) is deployed to production, migration `067_module_governance` is applied, governance admin authentication is configured, and all mandatory evaluate-only prod dry-runs **PASS**.

Code fixes delivered in this closure run:

- **M1** — Canonical ownership enforced in `ModuleInstallPolicyEngine` (`OWNERSHIP_MISMATCH`)
- **M2** — Fail-closed revocation trust for third-party package actions when marketplace metadata is enabled (`REVOCATION_STATE_UNTRUSTED`; STALE → review/deny semantics)
- **M3** — Active revocation always DENY; break-glass cannot override
- **L1** — `GET /api/modules/governance/policy/history` (admin-only)
- **Migration 067** — PostgreSQL boolean seed fix + idempotent upgrade for partial prod recovery

**Verdict:** **GO FOR SPRINT B**

---

## 2. Finding Closure

| Finding | Status | Notes |
|---------|--------|-------|
| **B1** Step 5C.2 not deployed | **CLOSED** | Deployed via `scripts/deploy-linux.ps1`; backend healthy; governance routes live |
| **B2** Migration 067 not on prod | **CLOSED** | Alembic head: `067_module_governance (head)` |
| **M1** OWNERSHIP_MISMATCH not enforced | **CLOSED** | Engine + evaluation service + tests; prod dry-run PASS |
| **M2** Stale/expired revocation too permissive | **CLOSED** | Fail-closed when `marketplace_metadata_enabled`; built-in runtime unaffected when disabled |
| **M3** Break-glass bypasses revocation | **CLOSED** | All severities DENY with break-glass; prod dry-run PASS |
| **L1** Policy history GET not exposed | **CLOSED** | `GET /api/modules/governance/policy/history` + test |

**Carried forward (unchanged):**

| Item | Status |
|------|--------|
| Invalid cache auto-heal (5C.1) | **TECH DEBT 5C.1** — not expanded in Sprint A |
| Break-glass process-local scope | Documented; no cluster work |

---

## 3. Migration 067 Production Fix

Initial prod deploy failed because migration 067 inserted `break_glass_enabled = 0` (integer) into a PostgreSQL `boolean` column.

**Fix applied:**

- Seed INSERT uses SQLAlchemy `bindparams(break_glass=False)`
- Idempotent table/column creation for partial-failure recovery
- Redeploy succeeded; backend container healthy

**Verified on prod:**

```
067_module_governance (head)
```

**Governance tables present:**

- `module_publishers`
- `module_publisher_verifications`
- `module_ownership`
- `module_ownership_transfers`
- `module_installation_policy`
- `module_policy_history`
- `module_publisher_keys` (extended columns)

---

## 4. Test Counts

### Governance

| Metric | Count |
|--------|------:|
| Collected | 39 |
| Passed | 39 |
| Failed | 0 |
| Skipped | 0 |

Includes: `packages/energy-core/tests/platform/governance/` + `backend/tests/test_governance_api.py`

### Marketplace security (Step 5C.1 regression)

| Metric | Count |
|--------|------:|
| Collected | 36 |
| Passed | 36 |
| Failed | 0 |
| Skipped | 0 |

### Packages (Step 5B regression)

| Metric | Count |
|--------|------:|
| Collected | 28 |
| Passed | 28 |
| Failed | 0 |
| Skipped | 0 |

### Architecture guards (Step 5C)

| Metric | Count |
|--------|------:|
| Collected | 6 |
| Passed | 6 |
| Failed | 0 |
| Skipped | 0 |

### Full regression (`test-windows.ps1` / pytest all packages)

| Suite | Passed | Failed | Skipped |
|-------|-------:|-------:|--------:|
| Python (pytest) | 1559 | 0 | 6 |
| Frontend (vitest) | 730 | 0 | 0 |

**Requirements met:** 0 failed; 0 security-critical skipped (marketplace suite).

---

## 5. Production Acceptance Matrix

| Check | Result |
|-------|--------|
| Migration 067 applied | **PASS** |
| Governance backend deployed | **PASS** |
| Governance frontend deployed | **PASS** |
| Governance route registered | **PASS** |
| Anonymous governance denied | **PASS** (401) |
| Admin governance access | **PASS** (200; `EMIC_ADMIN_TOKEN` configured) |
| OFFICIAL → ALLOW | **PASS** |
| COMMUNITY → DENY | **PASS** (`COMMUNITY_NOT_ALLOWED`) |
| REVOKED → DENY | **PASS** (`PUBLISHER_REVOKED`) |
| SUSPENDED → DENY | **PASS** (`PUBLISHER_SUSPENDED`) |
| Ownership mismatch → DENY | **PASS** (`OWNERSHIP_MISMATCH`) |
| Active revocation cannot break-glass | **PASS** (`PUBLISHER_REVOKED`) |
| Stale/invalid trust handled safely | **PASS** (local adversarial suite; prod marketplace disabled — see §6) |
| Control RUN pre-5C.5 → DENY | **PASS** (`CONTROL_MODULE_ISOLATION_REQUIRED`) |
| Step 5C.1 regression | **PASS** |
| Step 5B regression | **PASS** |
| Multi-site regression | **PASS** (existing prod stack; no regression observed) |
| No remote download | **PASS** |
| No public marketplace | **PASS** (`MARKETPLACE_METADATA_ENABLED` off) |
| No third-party runtime | **PASS** |
| Full regression | **PASS** |
| Prod health (`verify-prod-health.ps1`) | **PASS** |
| Prod runtime consistency (`verify-prod-runtime-consistency.ps1 -Strict`) | **PASS** |
| Prod log review | **PASS** (no unexplained governance/migration errors post-deploy) |

Prod acceptance executed via `scripts/sprint-a-prod-governance-acceptance.ps1` (evaluate-only; no package install/start/stop).

---

## 6. Prod Stale/Invalid Revocation Note

Production has **`MARKETPLACE_METADATA_ENABLED=false`**. By design, revocation freshness fail-closed policy applies to **marketplace/third-party package governance** when metadata sync is enabled; built-in EMIC modules are not disrupted when metadata is disabled.

Local tests (`test_revocation_hardening.py`) verify:

- `invalid` / `unavailable` / `expired` → `DENY` + `REVOCATION_STATE_UNTRUSTED` for INSTALL/UPDATE/ENABLE/RUN when marketplace enabled
- `stale` → `REQUIRE_SECURITY_REVIEW` (install/update) or `DENY` (control-capable ENABLE/RUN)

---

## 7. Adversarial Matrix (Prod + Local)

| Scenario | Expected | Prod dry-run |
|----------|----------|--------------|
| COMMUNITY | DENY | PASS |
| REVOKED | DENY | PASS |
| SUSPENDED | DENY | PASS |
| allow + deny precedence | DENY | PASS (local) |
| module allow + publisher revoked | DENY | PASS (local) |
| ownership mismatch | DENY | PASS |
| active revocation + break-glass | DENY | PASS |
| expired/invalid revocation trust (marketplace on) | fail-closed | PASS (local) |
| VERIFIED control RUN pre-5C.5 | DENY | PASS |
| anonymous governance mutation | DENY | PASS (401) |

---

## 8. Architecture Guards Confirmed

- No remote downloader in governance path
- No public unrestricted marketplace (metadata disabled on prod)
- No third-party runtime execution
- No ModuleOrchestrator coupling in governance layer
- No physical device control via governance evaluate endpoint

---

## 9. Sprint B Authorization

**GO FOR SPRINT B** authorizes:

- **Step 5C.3** — Remote signed distribution foundation
- **Step 5C.4** — SBOM / advisories / supply-chain monitoring

**Not authorized:**

- Third-party runtime execution
- Public unrestricted marketplace
- Control module execution (until Step 5C.5 isolation verified)

**Absolute 5C.5 gate remains:**

```
VERIFIED / ORG_APPROVED third-party control-capable module RUN / ENABLE → DENY
```

---

## 10. Operator Artifacts

| Script | Purpose |
|--------|---------|
| `scripts/deploy-linux.ps1` | Production deploy |
| `scripts/sprint-a-prod-governance-acceptance.ps1` | Evaluate-only prod governance dry-runs |
| `scripts/sprint-a-prod-setup-remote.sh` | Prod ownership fixture (SQL via docker) |
| `scripts/verify-prod-health.ps1` | Post-deploy health |
| `scripts/verify-prod-runtime-consistency.ps1` | Runtime consistency |

---

## 11. Sprint A Production Closure Summary

```
SPRINT A PRODUCTION CLOSURE

Migration 067 applied                 PASS
Governance backend deployed           PASS
Governance frontend deployed          PASS

Governance route registered           PASS
Anonymous governance denied           PASS
Admin governance access               PASS

OFFICIAL → ALLOW                      PASS
COMMUNITY → DENY                      PASS
REVOKED → DENY                        PASS
SUSPENDED → DENY                      PASS

Ownership mismatch → DENY             PASS
Active revocation cannot break-glass  PASS
Stale/invalid trust handled safely    PASS

Control RUN pre-5C.5 → DENY           PASS

Step 5C.1 regression                  PASS
Step 5B regression                    PASS
Multi-site regression                 PASS

No remote download                    PASS
No public marketplace                 PASS
No third-party runtime                PASS

Full regression                       PASS
Prod health                           PASS
Prod runtime consistency              PASS
Prod log review                       PASS
```

---

# GO FOR SPRINT B
