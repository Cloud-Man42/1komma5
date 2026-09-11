# EMIC Step 5C – Design Result

**Date:** 2026-09-07  
**Scope:** Public Module Ecosystem Security Architecture & Marketplace Design  
**Status:** **READY FOR STEP 5C DESIGN VERIFICATION**  
**Not:** PUBLIC MARKETPLACE READY (no implementation in this phase)

---

## 1. Executive Summary

Step 5C design deliverables are complete. Seven documents define threat model, trust architecture, master architecture (49 sections), marketplace data model, API contracts, runtime isolation strategy, and crypto framework decision (TUF + Ed25519 hybrid).

All design work respects the absolute constraint: **zero marketplace implementation** — no remote downloader, DB migrations, publisher signup, or public Store UI.

**Foundation:** Step 5B Internal Store verified at 82/100 ([EMIC_STEP5B_VERIFICATION.md](./EMIC_STEP5B_VERIFICATION.md)); GO for Step 5C design confirmed.

---

## 2. Deliverables

| Document | Path | Status |
|----------|------|--------|
| Threat model | [EMIC_MODULE_ECOSYSTEM_THREAT_MODEL.md](../security/EMIC_MODULE_ECOSYSTEM_THREAT_MODEL.md) | Complete |
| Trust model | [EMIC_MODULE_TRUST_MODEL.md](../security/EMIC_MODULE_TRUST_MODEL.md) | Complete |
| Master architecture | [EMIC_MODULAR_ARCHITECTURE_STEP5C.md](./EMIC_MODULAR_ARCHITECTURE_STEP5C.md) | Complete |
| Data model | [EMIC_MODULE_MARKETPLACE_DATA_MODEL.md](./EMIC_MODULE_MARKETPLACE_DATA_MODEL.md) | Complete |
| API design | [EMIC_MODULE_MARKETPLACE_API_DESIGN.md](./EMIC_MODULE_MARKETPLACE_API_DESIGN.md) | Complete |
| Runtime isolation | [EMIC_MODULE_RUNTIME_ISOLATION.md](./EMIC_MODULE_RUNTIME_ISOLATION.md) | Complete |
| Design result | This document | Complete |

---

## 3. §140 Design Acceptance Table

| # | Acceptance criterion | Status | Evidence |
|---|---------------------|--------|----------|
| 1 | Primary security question answered | **PASS** | [STEP5C §4](./EMIC_MODULAR_ARCHITECTURE_STEP5C.md); threat model §1 |
| 2 | Design-only scope enforced (no impl) | **PASS** | No new routes/migrations in repo; all docs marked design-only |
| 3 | Step 5B pipeline reuse mandated | **PASS** | STEP5C §126; API design §8 |
| 4 | Trust field separation (no collapse) | **PASS** | Trust model §4; STEP5C §8 |
| 5 | STRIDE threat model (25+ threats) | **PASS** | Threat model §5 — 32 threats T01–T32 |
| 6 | Attack trees (top 5) | **PASS** | Threat model §6 |
| 7 | Trust domains defined | **PASS** | Trust model §2 |
| 8 | Publisher tiers (5 tiers) | **PASS** | Trust model §3; STEP5C §7 |
| 9 | Fail-safe matrix | **PASS** | Trust model §5 |
| 10 | Two-party release model | **PASS** | STEP5C §24–25; data model §3.6 |
| 11 | Revocation model + SLA | **PASS** | STEP5C §14–16; trust model §5.1 |
| 12 | Replay/downgrade protection | **PASS** | STEP5C §29 |
| 13 | Dependency/namespace security | **PASS** | STEP5C §30–32; threat T18–T21 |
| 14 | SBOM/provenance strategy | **PASS** | STEP5C §33–37 |
| 15 | Install policy engine spec | **PASS** | STEP5C §42–44 |
| 16 | Runtime isolation decision | **PASS** | [Runtime isolation doc](./EMIC_MODULE_RUNTIME_ISOLATION.md) |
| 17 | Module RPC contract | **PASS** | Isolation §5 |
| 18 | Broker design (secret/network/device) | **PASS** | Isolation §6; STEP5C §51–55 |
| 19 | Kill switch scoped + safe-state | **PASS** | STEP5C §56–59; isolation §7 |
| 20 | Marketplace data model (ER + JSON) | **PASS** | [Data model doc](./EMIC_MODULE_MARKETPLACE_DATA_MODEL.md) |
| 21 | Mapping to existing EMIC tables | **PASS** | Data model §4 |
| 22 | API endpoint contracts | **PASS** | [API design doc](./EMIC_MODULE_MARKETPLACE_API_DESIGN.md) |
| 23 | EMIC install client flow (5 steps) | **PASS** | API design §5 |
| 24 | Auth separation | **PASS** | STEP5C §96–98; API design §6 |
| 25 | Rate limiting / abuse model | **PASS** | STEP5C §99–100; API design §7 |
| 26 | TUF analysis | **PASS** | STEP5C §92–95 |
| 27 | Sigstore analysis | **PASS** | STEP5C §92–95; optional path documented |
| 28 | §136 crypto recommendation (hybrid) | **PASS** | STEP5C §136 |
| 29 | Reject Marketplace re-sign as publisher | **PASS** | STEP5C §136; trust model |
| 30 | Caching/offline/air-gapped | **PASS** | STEP5C §64–65, §117–118 |
| 31 | Enterprise/private Store design | **PASS** | STEP5C §114–116 |
| 32 | Store UX wireframes (prose) | **PASS** | STEP5C §75–79 |
| 33 | Privacy/telemetry/audit | **PASS** | STEP5C §67–69, §81 |
| 34 | Migration from Step 5B | **PASS** | STEP5C §124–125 |
| 35 | Local upload path unchanged | **PASS** | STEP5C §124; API design §8 |
| 36 | Implementation phases (§137) | **PASS** | STEP5C §137 |
| 37 | Pre-5C debt identified | **PASS** | M6 + multi-site E2E before 5C.3 |
| 38 | §141 decisions (all 11) | **PASS** | Trust model §6 |
| 39 | Residual risk register | **PASS** | Threat model §9 |
| 40 | Red team checklist | **PASS** | Threat model §10 |
| 41 | Out-of-scope repeated in docs | **PASS** | All 7 documents |
| 42 | Cross-references between docs | **PASS** | Reference sections in each doc |
| 43 | Mermaid diagrams present | **PASS** | Threat, trust, data model, API, isolation |
| 44 | No vague "TBD" on critical crypto | **PASS** | §136 explicit hybrid stack |
| 45 | Control module tier requirements | **PASS** | OFFICIAL or VERIFIED required |
| 46 | COMMUNITY blocked in prod | **PASS** | Trust model §3 |
| 47 | Org admin override policy | **PASS** | No CRITICAL override; audit for NORMAL |
| 48 | Supply-chain monitoring inputs | **PASS** | STEP5C §38–41 |
| 49 | GO criteria for implementation | **PASS** | §143 below |

**Overall §140:** **49/49 PASS**

---

## 4. §141 Critical Decisions

Full Recommendation / Alternatives / Reasoning in [EMIC_MODULE_TRUST_MODEL.md](../security/EMIC_MODULE_TRUST_MODEL.md) §6. Summary:

| # | Question | Decision |
|---|----------|----------|
| Q1 | Third-party in-process? | Tiered — Official yes; Verified control → subprocess |
| Q2 | Control modules require Official/Verified? | **Yes** |
| Q3 | Use TUF? | **Yes** for catalog/revocation metadata only |
| Q4 | Use Sigstore? | **Optional** future phase for Verified CI |
| Q5 | Central revocation auto-stop? | Risk-class dependent — CRITICAL auto-quarantine |
| Q6 | Revocation staleness TTL? | 1h / 6h / 24h by risk; 7d offline grace |
| Q7 | Offline installation? | Cached trust + air-gapped import bundle |
| Q8 | Marketplace root key compromise? | Offline root + online subkeys + rotation IR |
| Q9 | Org admin override revocation? | No for CRITICAL; yes with audit for NORMAL |
| Q10 | Dependency confusion? | Canonical module_id + ownership registry |
| Q11 | Permission enforcement? | Install-time now; broker enforcement 5C.5 |

---

## 5. §142 Critical Decisions (Architecture)

| Decision | Choice | Tradeoff |
|----------|--------|----------|
| Package signing | Keep Ed25519 direct (Step 5B) | No TUF wrapper on artifacts — simpler, proven |
| Catalog/revocation | TUF-inspired snapshots | Slight complexity vs custom JSON |
| Release approval | Separate Marketplace Ed25519 key | Two-party trust vs single gate |
| Isolation default | In-process Official; subprocess Verified control | Performance vs security for third party |
| Remote install path | Pinned URL → existing validator | No parallel install engine |
| Community tier | Dev/lab only | Limits ecosystem size vs safety |

---

## 6. §143 Implementation GO Criteria

Implementation of Step 5C **sub-phases** may begin only when:

| Gate | Requirement |
|------|-------------|
| **G1** | Step 5C design verification PASS (this document reviewed independently) |
| **G2** | Pre-5C debt closed: M6 frontend Store tests + package multi-site E2E |
| **G3** | 5C.1: Catalog/revocation client + trust cache — security review PASS |
| **G4** | 5C.2: Publisher governance — verification workflow tested |
| **G5** | 5C.3: Remote download — red team exercises CDN swap + replay |
| **G6** | 5C.5: Subprocess isolation — broker + safe-state tested before Verified control in prod |
| **G7** | 5C.6: Public UI — only after G3–G5 PASS |

**This design phase does NOT authorize G3–G7.** It authorizes **design verification** only.

---

## 7. Implementation Phase Plan

| Phase | Scope | Verification |
|-------|-------|--------------|
| Pre-5C | M6 tests + multi-site E2E | Test suite green |
| 5C.1 | Signed catalog/revocation client | Signature tests, offline cache |
| 5C.2 | Publisher governance + org policy | Tier enforcement tests |
| 5C.3 | Remote download → existing installer | Hash/signature MITM tests |
| 5C.4 | SBOM + advisories | Scanner integration tests |
| 5C.5 | Subprocess + Module RPC + brokers | Isolation escape tests |
| 5C.6 | Public Store UI | UX + policy E2E |

---

## 8. Step 5B Debt Carry-Forward

From [EMIC_STEP5B_VERIFICATION.md](./EMIC_STEP5B_VERIFICATION.md):

| Item | Status | Required before |
|------|--------|-----------------|
| M6 — thin frontend Store tests | PARTIAL | 5C.3 implementation |
| Multi-site package E2E | Recommended | 5C.3 implementation |
| Signed demo prod lifecycle | CLOSED | — |

---

## 9. Risks Accepted at Design Stage

| Risk | Severity | Owner | Notes |
|------|----------|-------|-------|
| Official in-process | Medium | Platform | Accepted with supply-chain controls |
| Permission install-only until 5C.5 | Medium | Platform | Roadmap documented |
| Revocation stale offline | Medium | Operations | Degraded mode, not brick |
| Subprocess perf on edge | Low | Platform | Verify in 5C.5 POC |

---

## 10. Verification Checklist (Independent Reviewer)

- [ ] Confirm no marketplace routes added to codebase
- [ ] Confirm no DB migrations for marketplace entities
- [ ] Validate threat model covers prompt §5 scenarios
- [ ] Validate trust tiers match org safety requirements
- [ ] Validate install client flow ends at PackageValidator
- [ ] Validate §136 rejects custom crypto and publisher re-sign
- [ ] Validate COMMUNITY tier blocked for prod
- [ ] Validate CRITICAL revocation cannot be admin-overridden
- [ ] Cross-doc link integrity

---

## 11. Final Status

```
┌─────────────────────────────────────────────────────────┐
│  STEP 5C DESIGN: READY FOR STEP 5C DESIGN VERIFICATION │
│  NOT: PUBLIC MARKETPLACE READY                          │
└─────────────────────────────────────────────────────────┘
```

**Design acceptance:** 49/49 PASS  
**Implementation:** Not started (by design)  
**Next step:** Independent Step 5C design verification review

---

## 12. References

- [EMIC_MODULAR_ARCHITECTURE_STEP5C.md](./EMIC_MODULAR_ARCHITECTURE_STEP5C.md)
- [EMIC_MODULAR_ARCHITECTURE_STEP5B.md](./EMIC_MODULAR_ARCHITECTURE_STEP5B.md)
- [EMIC_STEP5B_VERIFICATION.md](./EMIC_STEP5B_VERIFICATION.md)
- [EMIC_MODULE_ECOSYSTEM_THREAT_MODEL.md](../security/EMIC_MODULE_ECOSYSTEM_THREAT_MODEL.md)
- [EMIC_MODULE_TRUST_MODEL.md](../security/EMIC_MODULE_TRUST_MODEL.md)
