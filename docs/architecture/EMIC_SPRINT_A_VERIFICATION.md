# EMIC Sprint A – Targeted Verification Report

**Date:** 2026-09-08  
**Scope:** Step 5C.1 (accepted baseline) + Step 5C.2 (Publisher Governance & Organization Policy)  
**Method:** Code inspection, adversarial runtime probes, focused + full regression, production HTTP probes, health scripts  
**Out of scope:** Step 5C.3/5C.4 implementation; remote artifact download

Implementation self-reports (`EMIC_STEP5C_2_RESULT.md`) are **not** accepted as evidence.

---

## 1. Executive Summary

Step 5C.2 **code, tests, and local adversarial checks** are substantially sound: deterministic deny-first policy engine, separate tier/status model, evaluate-only integration (`install_allowed` unchanged), admin-gated API, ownership transfer guards, and architecture isolation all **PASS** in repository verification.

**Production gate FAILS:** Step 5C.2 is **not deployed** to the production host. `GET http://192.168.50.54/api/modules/governance/publishers` returns **404 Not Found**. Migration 067 cannot be confirmed on prod. Mandatory prod dry-runs (OFFICIAL/COMMUNITY/REVOKED/control gate) were **not executed on production**.

Step 5C.1 marketplace security regression **PASS** (36/36, 0 skips). Full regression **PASS** (1545 Python, 730 frontend). Prod health and runtime consistency scripts **PASS** on existing deployment (pre-governance stack).

**Verdict:** Sprint A governance implementation is locally verified but **production deployment is incomplete**. Per Sprint B gate criteria (§93), this is a **BLOCKER**.

---

## 2. Test Baseline

### Governance-focused suite

| Metric | Count |
|--------|------:|
| Collected (platform/governance) | 20 |
| Collected (backend/test_governance_api.py) | 5 |
| Collected (architecture guards incl. governance) | 6 |
| **Governance run total** | **31** |
| Passed | 31 |
| Failed | 0 |
| Skipped | 0 |

### Marketplace security suite (Step 5C.1 regression)

| Metric | Count |
|--------|------:|
| Collected | 36 |
| Passed | 36 |
| Failed | 0 |
| Skipped | 0 |

Note: Plan referenced 43 marketplace tests; repository currently collects **36** marketplace tests, all passing with **0 skips**.

### Full regression (`test-windows.ps1`)

| Suite | Passed | Failed | Skipped |
|-------|-------:|-------:|--------:|
| Python (pytest) | 1545 | 0 | 6 |
| Frontend (vitest) | 730 | 0 | 0 |

EvOverview flaky test: **not reproduced** in this full run (730/730 pass). Prior isolated failure recorded as INFO only.

### Additional targeted runs

| Suite | Result |
|-------|--------|
| Step 5B packages (`tests/platform/packages/`) | 28 passed |
| Multi-site runtime isolation | 1 passed |
| Adversarial policy matrix probe (runtime) | All core matrix checks passed |

---

## 3. Migration 067 Verification (Repository)

**Alembic head:** `067_module_governance`

**Tables created (migration source verified):**

| Table | Purpose |
|-------|---------|
| `module_publishers` | Publisher entity (tier + lifecycle status) |
| `module_publisher_verifications` | Manual verification records |
| `module_ownership` | Canonical `module_id → publisher_id` |
| `module_ownership_transfers` | Transfer workflow + tier snapshots |
| `module_installation_policy` | Single-row org installation policy |
| `module_policy_history` | Append-only policy revision snapshots |

**Extended (not duplicated):** `module_publisher_keys` — adds `valid_from`, `valid_until`, `revoked_at`, `revocation_reason`

**Seed/backfill:** default installation policy, `emic` OFFICIAL publisher, backfill distinct `publisher_id` from existing keys as ORG_APPROVED/ACTIVE.

**Prod status:** **NOT VERIFIED** — prod backend returns 404 for governance routes; migration application on prod DB not confirmed.

---

## 4. No Duplicate Trust Model

**PASS**

- Step 5B `module_publisher_keys` + `PublisherTrustStore` retained for crypto trust
- Step 5C.2 adds `module_publishers` governance entity (tier/lifecycle) — complementary, not a parallel signing trust DB
- Keys API remains `backend/app/api/module_governance.py` delegates keys to existing `module_publishers.py` routes

---

## 5. Publisher Tier Model

**PASS** — `PublisherTier` enum in `governance/types.py`:

| Tier | Semantics (verified in engine) |
|------|--------------------------------|
| `OFFICIAL` | Allowed by default prod policy |
| `VERIFIED` | Allowed by default prod policy |
| `ORG_APPROVED` | Allowed by default prod policy |
| `COMMUNITY` | Denied in production unless break-glass |
| `REVOKED` | Always denied (terminal tier) |

---

## 6. Status vs Tier Separation

**PASS**

- `ModulePublisherModel` stores independent `tier` and `status` columns
- Engine checks both: e.g. `SUSPENDED` status denies before tier allow rules; `REVOKED` tier denies regardless of allowlists
- `VERIFIED` tier + `SUSPENDED` status is structurally possible and denies via status check (line 101–108 `policy_engine.py`)

---

## 7–10. Mandatory Default Deny Checks

| Check | Result | Evidence |
|-------|--------|----------|
| COMMUNITY in prod → DENY | **PASS** | `test_community_denied_in_production`, adversarial probe |
| REVOKED → DENY | **PASS** | Before allowlists; break-glass cannot override (`test_break_glass_cannot_override_revoked_publisher`) |
| SUSPENDED → DENY | **PASS** | Status check precedes allow paths; adversarial probe |
| Default unknown → DENY | **PASS** | `DEFAULT_DENY` reason at engine terminus |

---

## 11. Decision Enum

**PASS** — `PolicyDecision`: `ALLOW`, `DENY`, `REQUIRE_ADMIN_APPROVAL`, `REQUIRE_SECURITY_REVIEW` in `governance/types.py`. API returns enum `.value` strings; no uncontrolled string sprawl in engine outputs.

---

## 12–15. Determinism, Default Deny, Precedence

**PASS**

- Same input → identical `PolicyEvaluationResult` (adversarial probe + unit tests)
- Deny checks ordered **before** allow paths in `policy_engine.py` (lines 71–120 before 168–178)
- Core matrix verified:

| Scenario | Result |
|----------|--------|
| publisher allow + publisher deny | DENY |
| publisher allow + module deny | DENY |
| module allow + publisher revoked | DENY |
| module allow + blocked permission | DENY |
| publisher allowlist + COMMUNITY (prod) | DENY |
| break-glass + CRITICAL revocation | DENY |

---

## 16. Reason Codes

**PASS** — Stable `PolicyReasonCode` enum includes: `PUBLISHER_REVOKED`, `PUBLISHER_SUSPENDED`, `TIER_NOT_ALLOWED`, `PUBLISHER_DENIED`, `MODULE_DENIED`, `PERMISSION_BLOCKED`, `CONTROL_MODULE_ISOLATION_REQUIRED`, `COMMUNITY_NOT_ALLOWED`, `REVOCATION_ACTIVE`, `REVOCATION_STALE`, `DEFAULT_DENY`, `BREAK_GLASS_ACTIVE`, etc.

---

## 17–19. Control Module Gate & Classification

**PASS**

- `is_control_capable()` in `risk_classifier.py` — backend-only from permissions + provided_capabilities
- `RUN`/`ENABLE` on control-capable modules → `DENY` while `CONTROL_ISOLATION_GATE_OPEN = False` (Step 5C.5)
- Read-only/non-control modules can ALLOW per tier/org rules (`test_official_publisher_allowed`)
- Verified publisher + control + RUN → DENY (adversarial probe)

---

## 20–21. Permission Policy

**PASS** — blocked permission → DENY even when otherwise allowed.

**INFO** — Combined high-risk permission pairs (e.g. `secrets.read_own` + `network.external`) not evaluated as combinations; single-permission blocking only. Documented as later policy extension; not a Sprint A blocker per design scope.

---

## 22–24. Revocation Integration

| State | Behavior (code-verified) |
|-------|--------------------------|
| Active revocation match | DENY (`REVOCATION_ACTIVE`) when `break_glass_active=False` OR severity `CRITICAL` |
| CRITICAL + break-glass | DENY (always) |
| Non-CRITICAL + break-glass active | **ALLOW may proceed** — matches docs limiting non-override to CRITICAL only |
| Freshness `expired` | Adds `REVOCATION_STALE` to reasons; **does not DENY** — evaluation continues |
| Metadata health `INVALID` | `RevocationReader.find_active_revocation` returns None — revocations not treated as trusted |

**MEDIUM (M2):** Stale revocation (`freshness=expired`) warns but does not deny. Document exact behavior for operators.

**MEDIUM (M3):** Non-CRITICAL active revocation bypassable with break-glass — consistent with written policy docs but stricter reading of verification checklist item 22 would expect all active revocations to deny.

---

## 25–28. Publisher Lifecycle

**PASS**

- Transitions enforced in `PublisherRepository.ALLOWED_TRANSITIONS`
- `REVOKED → ACTIVE` blocked (`test_invalid_transition_revoked_to_active`)
- No self-service tier escalation path — governance API is admin-token gated; publishers cannot PATCH own tier without admin auth
- Admin tier change via PATCH audited (`publisher.updated`)

---

## 29–30. Key Governance & Private Key Exclusion

**PASS**

- Ed25519 hex validation in `module_publishers.py` (32 bytes)
- Duplicate key_id handling tested via existing publisher key API tests
- No `private_key`, `signing_key`, or `seed` in governance request schemas (grep verified)

---

## 31–38. Ownership Integrity

| Check | Result |
|-------|--------|
| Canonical `module_id → publisher_id` | **PASS** — `module_ownership` PK on `module_id` |
| Package install hijack | **PASS** — no ownership writes in `packages/installer.py` |
| Transfer happy path + audit | **PASS** — repository tests + API audit hooks |
| Revoked target publisher | **PASS** — blocked |
| Protected module transfer | **PASS** — `is_protected_module_id` guard |
| Duplicate pending transfer | **PASS** — second pending rejected |
| No trust escalation on transfer | **PASS** — `from_tier`/`to_tier` snapshots; target tier used for future policy |
| Historical signatures | **PASS** — crypto verification unchanged; governance does not rewrite signature history |

**MEDIUM (M1):** `OWNERSHIP_MISMATCH` reason code defined but **not enforced** in `ModuleInstallPolicyEngine` — manifest publisher vs canonical ownership not checked during evaluate (plan §4 partial gap).

---

## 39–46. Organization Policy

**PASS** — persistence, default prod-safe tiers, optimistic concurrency (`409 POLICY_CONFLICT`), allow/deny list tests, denylist precedence.

**LOW (L1):** Policy history **GET API endpoint not implemented** — history rows written on update, but no list/history route in `module_governance.py` (plan listed GET history).

---

## 47–50. Break-Glass

| Requirement | Result |
|-------------|--------|
| Admin required | **PASS** |
| Reason required | **PASS** |
| Expiry required | **PASS** |
| Audit on activate | **PASS** |
| Expired session ignored | **PASS** — `BreakGlassStore.current()` clears expired |
| CRITICAL revocation non-override | **PASS** |
| REVOKED publisher non-override | **PASS** |
| Process-local store | **PASS** — `break_glass.py` module-level store; docs state process-local |

---

## 51–53. Evaluate-Only Integration

**PASS**

- `POST /api/modules/governance/evaluate` — dry-run, no mutation (except optional `policy.denied` audit on DENY)
- `install_allowed` computed **before** policy evaluation and **not modified** by governance result (`validator.py` lines 189–246)
- Policy fields attached separately: `policy_decision`, `policy_reason_codes`, etc.

---

## 54–58. Auth & Audit

**PASS (code)** — all governance routes use `require_admin_token`; anonymous → 401 when token configured.

**Prod note:** When `EMIC_ADMIN_TOKEN` is empty, `require_admin_token` is a no-op (dev design). Prod must set token.

**Audit events verified in code:** `publisher.created`, `publisher.verified`, `publisher.suspended`, `publisher.revoked`, `organization_policy.updated`, `module.transfer_*`, `break_glass.activated`, `policy.denied` (evaluate DENY only).

Key audit via existing `publisher.key_added` / `publisher.key_revoked` in `module_publishers.py`.

---

## 59–62. UI

**PASS** — internal admin UI only under `/config/modules-devices/governance/*`. Frontend governance components display API results; architecture guard forbids embedding `ModuleInstallPolicyEngine` / policy computation tokens.

---

## 63. Invalid Cache Recovery Debt

**INFO (carry-forward)** — Not fixed. Corrupt cache online recovery still raises `CacheValidationError` instead of auto-heal. Non-blocking; governance `RevocationReader` does not treat INVALID metadata as trusted.

---

## 64–69. Regression & Architecture Isolation

| Gate | Result |
|------|--------|
| Step 5C.1 marketplace security | **PASS** (36/36, 0 skips) |
| Step 5B packages | **PASS** (28/28) |
| Multi-site isolation | **PASS** (1/1) |
| Architecture guards | **PASS** |
| No remote download in governance | **PASS** (grep) |
| No public marketplace UI | **PASS** |
| No third-party runtime | **PASS** |

---

## 70–83. Production Deployment Gate

| Check | Result | Detail |
|-------|--------|--------|
| Migration 067 on prod | **FAIL** | Not confirmed; governance routes absent |
| Backend+frontend deploy | **FAIL** | `GET /api/modules/governance/publishers` → **404** |
| Prod governance auth | **FAIL** | Route not registered (404, not 401) |
| Prod OFFICIAL dry-run | **FAIL** | Not executed |
| Prod COMMUNITY deny | **FAIL** | Not executed |
| Prod REVOKED deny | **FAIL** | Not executed |
| Prod control gate dry-run | **FAIL** | Not executed |
| Prod policy mutation | **FAIL** | Not executed |
| MARKETPLACE_METADATA_ENABLED unchanged | **INFO** | Cannot verify flag; marketplace status also 404 on prod |
| Prod health script | **PASS** | `verify-prod-health.ps1` all checks OK |
| Prod runtime consistency | **PASS** | `verify-prod-runtime-consistency.ps1` all checks OK |

**Deploy attempt:** `EMIC_DEPLOY_SERVER=192.168.50.54`, `EMIC_DEPLOY_USER=hm` present; **no deploy key/password available** in environment — safe prod deploy not completed during verification.

**Reference prod probes:**

```
GET /api/modules/governance/publishers     → 404 Not Found
GET /api/modules/marketplace/status        → 404 Not Found
GET /api/modules/publishers                → 401 Unauthorized (5B route exists)
```

---

## 84. Log Review

Not performed on prod host (no SSH/deploy credentials). No local traceback in test runs.

---

## 87. Findings Summary

| ID | Severity | Finding |
|----|----------|---------|
| **B1** | **BLOCKER** | Step 5C.2 **not deployed to production** — governance API 404 |
| **B2** | **BLOCKER** | Migration **067 not applied/verified on production** |
| M1 | MEDIUM | `OWNERSHIP_MISMATCH` not enforced during policy evaluate |
| M2 | MEDIUM | Stale revocation (`freshness=expired`) warns only; does not DENY |
| M3 | MEDIUM | Non-CRITICAL revocation bypassable with break-glass (docs-aligned) |
| L1 | LOW | Policy history GET API not exposed |
| I1 | INFO | Invalid cache online recovery still deferred (5C.1) |
| I2 | INFO | Break-glass store is process-local (documented) |
| I3 | INFO | EvOverview flaky test not reproduced in this run |

**No BLOCKER found in local policy precedence, COMMUNITY/REVOKED/SUSPENDED deny logic, control RUN gate, or install_allowed separation.**

---

## 90. Targeted Score

| Area | Score |
|------|-------|
| Publisher Governance | PASS |
| Publisher Lifecycle | PASS |
| Key Governance | PASS |
| Private-key exclusion | PASS |
| Ownership Integrity | PASS |
| Ownership Transfer | PASS |
| No transfer trust escalation | PASS |
| Protected ownership | PASS |
| Organization Policy | PASS |
| Policy decision enum | PASS |
| Default deny | PASS |
| Deny precedence | PASS |
| COMMUNITY prod denied | PASS |
| REVOKED denied | PASS |
| SUSPENDED denied | PASS |
| Control RUN gate pre-5C.5 | PASS |
| Permission policy | PASS |
| Revocation integration | PASS (with M2/M3 caveats) |
| Break-glass | PASS |
| Critical non-override | PASS |
| Governance API admin auth | PASS (code) |
| Audit | PASS |
| UI backend-source-of-truth | PASS |
| Step 5C.1 regression | PASS |
| Step 5B regression | PASS |
| Multi-site regression | PASS |
| Architecture guards | PASS |
| No remote download | PASS |
| No public marketplace | PASS |
| No third-party runtime | PASS |
| Migration 067 prod | **FAIL** |
| Step 5C.2 deployed prod | **FAIL** |
| Prod governance auth | **FAIL** |
| Prod OFFICIAL dry-run | **FAIL** |
| Prod COMMUNITY deny | **FAIL** |
| Prod REVOKED deny | **FAIL** |
| Prod control gate | **FAIL** |
| Full regression | PASS |
| Prod health | PASS |
| Prod runtime consistency | PASS |

---

## 92. SPRINT A VERIFICATION Summary

```
SPRINT A VERIFICATION

Publisher governance                 PASS
Publisher lifecycle                  PASS
Key governance                       PASS
Private-key exclusion                PASS

Ownership integrity                  PASS
Ownership transfer                   PASS
No transfer trust escalation         PASS
Protected ownership                  PASS

Organization policy                  PASS
Policy decision enum                 PASS
Default deny                         PASS
Deny precedence                      PASS

COMMUNITY prod denied                PASS
REVOKED denied                       PASS
SUSPENDED denied                     PASS
Control RUN gate pre-5C.5            PASS

Permission policy                    PASS
Revocation integration               PASS

Break-glass                          PASS
Critical non-override                PASS

Governance API admin auth            PASS
Audit                                PASS
UI backend-source-of-truth           PASS

Step 5C.1 regression                 PASS
Step 5B regression                   PASS
Multi-site regression                PASS
Architecture guards                  PASS

No remote download                   PASS
No public marketplace                PASS
No third-party runtime               PASS

Migration 067 prod                   FAIL
Step 5C.2 deployed prod              FAIL
Prod governance auth                 FAIL
Prod OFFICIAL dry-run                FAIL
Prod COMMUNITY deny                  FAIL
Prod REVOKED deny                    FAIL
Prod control gate                    FAIL

Full regression                      PASS
Prod health                          PASS
Prod runtime consistency             PASS
```

---

## 93. Sprint B Gate Decision

Sprint B gate requires **0 BLOCKER**, prod deployment PASS, prod health PASS, prod runtime consistency PASS.

- **BLOCKERS:** B1 (prod deploy), B2 (migration 067 prod) — **2 blockers**
- Code-level governance/policy/ownership/control safety: **no unresolved HIGH blockers**
- Step 5C.1 + 5B regression: **PASS**
- Prod health + runtime consistency: **PASS** (existing stack)

**Required before Sprint B:**

1. Deploy backend+frontend with Step 5C.2 to production (`scripts/deploy-linux.ps1`)
2. Apply migration `067_module_governance` on prod DB
3. Execute prod governance auth matrix (401/403 anonymous, 200 admin)
4. Execute prod dry-runs: OFFICIAL→ALLOW, COMMUNITY→DENY, REVOKED→DENY, control RUN→DENY
5. Re-run this verification prod section

---

## 94. Sprint B Scope Reminder (if GO later)

Allowed next work: **Step 5C.3** (remote signed distribution foundation) + **Step 5C.4** (SBOM/advisories). VERIFIED/ORG_APPROVED control-capable third-party code **must not RUN** before Step 5C.5 isolation gate.

---

NO-GO FOR SPRINT B
