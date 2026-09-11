# EMIC Step 5C – Independent Security & Architecture Design Verification

**Date:** 2026-09-07  
**Verifier:** Independent audit (design docs, Step 5B code baseline, repository leak scan)  
**Scope:** Step 5C design only — readiness for **5C.1** (catalog/revocation metadata client + trust cache)  
**Not in scope:** Implementation, 5C.1 coding, remote download, public marketplace

**Source of truth:** Cross-verification of design documents and Step 5B architecture. [`EMIC_STEP5C_DESIGN_RESULT.md`](./EMIC_STEP5C_DESIGN_RESULT.md) self-assessment (49/49 PASS) is **not** treated as evidence.

---

## 1. Executive Summary

Step 5C design deliverables (7 documents) provide a coherent security architecture for a governed public module ecosystem built on the production-verified Step 5B Internal Store pipeline. The design correctly mandates pipeline reuse, trust field separation, two-party release signing, tiered publisher trust, and scoped revocation.

**Repository leak check:** **PASS** — no marketplace routes, remote downloader, migrations, or public Store UI from Step 5C design phase.

**Independent assessment:** Design is **adequate to begin 5C.1** (signed catalog/revocation client + trust cache). Three HIGH findings and seven MEDIUM findings must be resolved or gated before later phases (5C.3 remote download, 5C.5 isolation, 5C.6 public UI).

**STEP 5C DESIGN READINESS SCORE: 74 / 100**

Design result self-score (49/49) is **not accepted** — independent verification reflects documented gaps below.

---

## 2. Scope Verification

| Requirement | Verified | Evidence |
|-------------|----------|----------|
| Design verification only | **PASS** | No Step 5C implementation in codebase |
| No remote package download | **PASS** | Grep: no `remote/validate`, `remote/install` in `.py`/`.ts`/`.tsx` |
| No marketplace DB migrations | **PASS** | No `*marketplace*` alembic versions |
| No public marketplace routes | **PASS** | API design marked contract-only |
| No publisher signup prod | **PASS** | Publisher endpoints marked future/design-only |
| No public Store UI | **PASS** | Store UX is prose wireframes only |
| Step 5B pipeline unchanged | **PASS** | `PackageValidator` → `PackageInstaller` → `loader.py` intact |
| Design docs exist (7) | **PASS** | All listed in §2 deliverables table |

---

## 3. Cross-Document Consistency

### 3.1 Consistent (PASS)

| Topic | Documents aligned |
|-------|-------------------|
| Pipeline reuse | Master §126, API §8, design result §3 |
| Trust field separation | Trust model §4, master §8, module-sdk/security.md |
| Publisher tiers (5) | Trust model §3, master §7 — uses `ORG_APPROVED` not "TRUSTED" |
| COMMUNITY blocked in prod | Trust model §3, master §7, threat T01 |
| Two-party release | Master §24–25, data model §3.6, API §5 |
| No Marketplace re-sign as publisher | Master §136, threat model T07 |
| Pre-5C debt before 5C.3 | Master §124, design result §8, Step 5B verification M6 |
| Fail-safe matrix | Trust model §5, master §86–88 |
| Install ≠ enable | API §5 step 9, Step 5B pattern |

### 3.2 Inconsistencies / Gaps

See **§50 Findings**. Key cross-doc issues:

- **H-01:** Trust model §3.2 org opt-in for Verified control in-process until 5C.5 conflicts with G6 execution gate wording.
- **H-03:** Master §136 and data model §5.1 call model "TUF-inspired" but JSON schema is single signed blob without TUF role separation.
- **M-02:** Source precedence across local/org/public Store not algorithmically defined.

---

## 4. Threat Model

**Document:** [`EMIC_MODULE_ECOSYSTEM_THREAT_MODEL.md`](../security/EMIC_MODULE_ECOSYSTEM_THREAT_MODEL.md)

| Criterion | Status | Notes |
|-----------|--------|-------|
| 25+ enumerated threats | **PASS** | 32 threats T01–T32 |
| STRIDE coverage | **PARTIAL** | Subsystem matrix §7; per-threat lacks full asset/actor/entry-point/owner dossier |
| Mitigations mapped to 5B vs 5C | **PASS** | §8 mapping table |
| Residual risk register | **PASS** | §9 R01–R06 |
| Red team checklist | **PASS** | §10 — 10 scenarios |

**Required threat scenarios — coverage:**

| Scenario | Covered | ID / Gap |
|----------|---------|----------|
| Malicious publisher | Yes | T01 |
| Compromised publisher key | Yes | T02, attack tree §6.1 |
| Compromised Store backend | Yes | T07, attack tree §6.3 |
| Compromised catalog signing key | Partial | T31; freeze/mix-and-match not explicit |
| Compromised CDN | Yes | T13, attack tree §6.2 |
| MITM | Yes | T09 |
| Rollback/replay | Yes | T14, T15 |
| Dependency confusion | Yes | T19, attack tree §6.4 |
| Namespace squatting | Yes | T18, T20 |
| Publisher impersonation | Yes | T03 |
| Malicious update | Yes | T02, T05 |
| Revoked release/key | Yes | T02, T06 |
| Stale revocation | Yes | T28 |
| Offline host | Yes | T29 |
| Root key compromise | Yes | T31 |
| Malicious Store admin | Yes | T11 |
| Module sandbox escape | Partial | T27 "TBD at implementation" |
| Secret theft | Yes | T24 |
| Lateral movement | Yes | T23, attack tree §6.5 |
| Control abuse | Yes | T25 |
| Device damage | Implicit | Via control abuse + safe-state (isolation §7) |
| Kill-switch abuse | Yes | T32 |
| **SSRF** | **Missing** | Add before 5C.3 (M-04) |
| **Redirect hijack** | **Missing** | Add before 5C.3 (M-04) |
| **DNS rebinding** | **Missing** | Add before 5C.5 network policy (M-04) |
| **Freeze attack** | **Missing** | Related to H-03 TUF subset |
| **False revocation** | Partial | T11; recovery path underspecified |

**Verdict:** **PARTIAL PASS** — adequate for design phase; gaps gated to 5C.3+.

---

## 5. Attack Trees

**Document:** Threat model §6

| Required tree | Present | Mitigations linked |
|---------------|---------|-------------------|
| Compromised publisher key | Yes §6.1 | Yes |
| CDN artifact swap | Yes §6.2 | Yes |
| Marketplace backend compromise | Yes §6.3 | Yes |
| Dependency confusion | Yes §6.4 | Yes |
| Control-module lateral movement | Yes §6.5 | Yes |
| Malicious package reaches runtime | Partial | Via publisher key + lateral trees; no dedicated "unsigned path" tree |
| Module escapes isolation | **Missing** | Required before 5C.5 |
| Revocation fails | **Missing** | Stale revocation in T28; no dedicated tree |

**Verdict:** **PARTIAL PASS** — top 5 present with concrete mitigations; two recommended additions for 5C.5 verification.

---

## 6. Trust Boundaries

**Document:** [`EMIC_MODULE_TRUST_MODEL.md`](../security/EMIC_MODULE_TRUST_MODEL.md) §2

Twelve domains defined with may-assert / must-verify / never-assert columns:

EMIC Core, Official/Verified/Community Publisher, Marketplace Backend, Catalog Service, CDN, Installation Client, Module Runtime, Device/Site, Secrets Store, Admin.

**Organization policy** implied via Admin + InstallPolicyEngine; not a separate domain row — acceptable.

**Verdict:** **PASS**

---

## 7. Publisher Trust

| Tier | Identity | Prod install | Control modules | Runtime | Verified |
|------|----------|--------------|-----------------|---------|----------|
| OFFICIAL | EMIC-operated | Allowed | Allowed | In-process | Trust model §3 |
| VERIFIED | Org verification | Org policy | Subprocess (5C.5) | Tiered | Trust model §3 |
| ORG_APPROVED | Admin allowlist | Per-org | Policy-dependent | Tiered | Trust model §3 |
| COMMUNITY | Self-register | **Blocked** | N/A | Dev/lab | Trust model §3 |
| REVOKED | Any revoked | Quarantine | N/A | Stopped | Trust model §3 |

**Verdict:** **PASS**

---

## 8. Publisher Identity

Lifecycle stages in design:

| Stage | Documented | Gap |
|-------|------------|-----|
| Create | Yes — onboarding §9 | |
| Verify | Yes — PublisherVerification entity | Re-verification cadence not specified |
| Approve tier | Yes — master §25 | |
| Key register | Yes — data model §3.2 | |
| Rotate | Yes — master §12 | |
| Suspend | Partial — Publisher.status SUSPENDED | |
| Revoke | Yes — revocation polymorphic | |
| **Ownership transfer** | **No** | M-03 |
| Terminate | Partial — REVOKED tier | |

**Verdict:** **PARTIAL PASS**

---

## 9. Key Management

Separate key roles documented:

| Key role | Documented | Location |
|----------|------------|----------|
| Publisher signing key | Yes | Package signature, trust store |
| Marketplace release approval key | Yes | Master §24, data model §3.6 |
| Catalog signing key | Yes | Data model §5.1 `catalog_key_id` |
| Revocation signing key | Yes | Data model §5.2 |
| Offline root | Yes | Trust model Q8, master §136 |

**Private keys:** Marketplace never stores publisher private keys — **PASS** (trust model §9, threat T04).

**Verdict:** **PASS**

---

## 10. Key Rotation

- `valid_from` / `valid_until` on PublisherKey — data model §3.2
- Overlap period — master §12
- Old releases verifiable until key expiry — master §12
- Rotation published in catalog root metadata — master §12

**Verdict:** **PASS**

---

## 11. Revocation

- Polymorphic scopes: PUBLISHER, KEY, MODULE, VERSION, HASH, CHANNEL — master §14
- Signed revocation bundle — data model §5.2
- SLA by risk class — trust model §5.1 (1h / 6h / 24h)
- CRITICAL auto-quarantine — trust model Q5
- No admin override for CRITICAL — trust model Q9
- Scoped kill switch — master §56–59, threat T32

**Revoked key semantics:** Distinction via `reason_code` (KEY_COMPROMISE vs expiry via `valid_until` + EXPIRED status) — partially documented; recommend explicit enum doc.

**Verdict:** **PASS**

---

## 12. Root Trust

- Multi-key hierarchy: offline root → online catalog + revocation subkeys — trust model Q8
- EMIC ships root pins with update channel — trust model Q8
- N and N-1 key support during rotation — API §10

**Gap (M-05):** Offline **root** compromise incident response is high-level only — no step-by-step recovery (out-of-band root transfer, EMIC software update with new pins, grace period).

**Verdict:** **PARTIAL PASS**

---

## 13. TUF Evaluation

Design recommends TUF for catalog/revocation metadata only; Ed25519 direct signing for packages.

**Actual design artifact:** Single signed JSON snapshot (data model §5.1) with `snapshot.version`, `expires_at`, `targets`, one `signatures.catalog` — **not** full TUF role graph (root/targets/snapshot/timestamp delegations).

| TUF guarantee | Design coverage |
|---------------|-----------------|
| Snapshot freshness | Partial — `expires_at`, monotonic version |
| Freeze attack | **Weak** — no timestamp role or max-age enforcement chain |
| Rollback of metadata | Partial — monotonic version |
| Mix-and-match | **Weak** — no hash-linked role metadata |
| Delegation | Not present |

**Finding H-03:** Calling this "TUF" without adopting `python-tuf` or specifying equivalent guarantees risks custom update-framework vulnerabilities.

**Recommendation:** For 5C.1 implementation, either (a) use `python-tuf` with standard roles, or (b) rename to "signed snapshot" and publish a spec document with explicit freeze/rollback/mix-and-match mitigations.

**Verdict:** **PARTIAL PASS**

---

## 14. Sigstore Evaluation

Optional future phase for Verified publisher CI attestation — master §92–95, trust model Q4.

Not required for v1 or 5C.1. Correctly deferred.

**Verdict:** **PASS**

---

## 15. Artifact Signing

- Ed25519 direct signing on `.emicpkg` — unchanged from Step 5B
- Digest: `{content_sha256}\n{manifest_sha256}` — module-sdk/security.md
- Marketplace cannot replace publisher signature — master §136

**Verdict:** **PASS**

---

## 16. Catalog Signing

Signed catalog snapshot before trust — API §2.1, install flow step 1.

Browse endpoints (`/v1/catalog/modules`) explicitly unsigned — install requires signed snapshot target match. **PASS**.

**Verdict:** **PARTIAL PASS** (see §13 TUF gaps)

---

## 17. Replay / Rollback

- `release_sequence` monotonic per module — master §29
- `published_at` in signed metadata
- Revoked-version list in revocation feed
- Step 5B `VERSION_DOWNGRADE_NOT_ALLOWED` retained — master §29
- Catalog snapshot version monotonic — master §21

**Verdict:** **PASS**

---

## 18. Dependency Security

- Explicit `module_dependencies` in manifest — no auto-resolve
- Dependency must be Official, same publisher, or org-allowlisted — master §30
- Canonical `module_id` — master §31

**Verdict:** **PASS**

---

## 19. Namespace Ownership

- Publisher owns namespace via ModuleListing — data model §3.3
- Protected prefixes `core.*`, `platform.*` — paths.py (Step 5B), master §31
- Built-in IDs protected — paths.py `is_protected_module_id`
- First verified owner wins — master §32

**Verdict:** **PASS**

---

## 20. Provenance

Release metadata includes: module_id, version, publisher, publisher_key_id, content_sha256, manifest_digest, release_sequence, published_at, release_id — data model §3.4, §5.3.

Optional: sbom_ref, Sigstore (future).

**Verdict:** **PASS**

---

## 21. SBOM

CycloneDX JSON referenced in release metadata — master §34.

**Motivation:** CycloneDX is widely supported for component-level SBOM in supply-chain tooling; SPDX better for license-only. CycloneDX choice is reasonable for vulnerability scanner integration.

Transitive dependencies: implied via scanner ingest — not explicitly mandated in manifest dependency list (manifest deps are module-level only). Recommend clarifying SBOM covers Python/runtime transitive deps.

**Verdict:** **PARTIAL PASS**

---

## 22. Vulnerability Model

- Scanner ingests SBOM; status from scanner only — master §34–35
- Advisory feed — API §2.5, data model §3.9
- Install policy may block CRITICAL CVEs — master §35

**Gap (M-01):** Advisories not signed; no advisory trust chain.

**Verdict:** **PARTIAL PASS**

---

## 23. Supply-Chain Monitoring

Deterministic risk inputs — master §38–41: tier, permission/capability diff, advisories, revocation history, SBOM scan.

Outputs: badge, policy gate, review queue — no opaque auto-block without policy rule. **PASS** for §57 false-positive concern.

**Verdict:** **PASS**

---

## 24. Risk Classification

CRITICAL / HIGH / NORMAL / LOW — trust model §4, data model §3.4.

Derived from capabilities + publisher tier — master §36–37.

**Verdict:** **PASS**

---

## 25. Policy Engine

**Inputs:** trust fields, risk_class, org tier, allowlist, advisory status, revocation staleness, channel — master §42.

**Outputs:** `policy_allowed`, block reason, runtime mode requirement — master §42.

**Gap (M-06):** No explicit decision enum (`ALLOW`, `DENY`, `REQUIRE_ADMIN_APPROVAL`, `REQUIRE_SECURITY_REVIEW`).

**Verdict:** **PARTIAL PASS**

---

## 26. Organization Policy

OrganizationPolicy entity — data model §3.11: allowed_tiers, publisher_allowlist, control_module_policy, break_glass.

Supports official-only, official+verified, approved publishers, blocked permissions (via policy engine design).

**Verdict:** **PASS**

---

## 27. Runtime Isolation

**Document:** [`EMIC_MODULE_RUNTIME_ISOLATION.md`](./EMIC_MODULE_RUNTIME_ISOLATION.md)

Comparison matrix: in-process, subprocess, container, WASM, gRPC sidecar — scored and analyzed.

Tiered recommendation: Official in-process; Verified read-only in-process + brokers; Verified control subprocess + RPC.

**Finding H-02:** Subprocess scored 4/5 security but design lacks **mandatory OS-level controls** (seccomp/AppArmor, network namespace, read-only rootfs, no-new-privs, FD limits). A plain Python subprocess shares kernel with host and is **not** a sandbox.

**Verdict:** **PARTIAL PASS**

---

## 28. Module RPC

JSON-RPC 2.0 over Unix socket / named pipe — isolation §5.

Methods: start/stop/health/capabilities/read/command/config.

Error codes defined — isolation §5.5.

**Gaps for 5C.5:**
- RPC auth / module identity binding (§90–91) — mentioned implicitly, not fully specified
- Request size, timeout, rate, concurrency limits (§93) — not specified

**Verdict:** **PARTIAL PASS**

---

## 29. Secret Broker

Module requests own secret by declared key — isolation §6.1.

Scoped to manifest secrets list + `secrets.read_own`.

**Gap:** In-process modules have document-only enforcement until 5C.5 — acknowledged (R04).

**Verdict:** **PASS** (design intent; enforcement deferred)

---

## 30. Network Policy

`network.external` / `network.local` — isolation §6.2.

OS enforcement only for isolated subprocess; in-process document-only until Phase 1.

**Gaps:** DNS rebinding (M-04), `network.local` high-risk policy for energy systems — mentioned as HIGH risk class but no specific local-network egress rules.

**Verdict:** **PARTIAL PASS**

---

## 31. Filesystem Policy

Module write paths scoped — isolation §6.3.

**Gap:** Symlink/mount escape (§84) not explicitly in threat model or isolation doc.

**Verdict:** **PARTIAL PASS**

---

## 32. Control Broker

DeviceControlBroker chain: Module → RPC → Broker → CapabilityRegistry → SitePolicy → DeviceAdapter — isolation §6.4.

Six check steps including revocation freshness for CRITICAL.

**Verdict:** **PASS**

---

## 33. Emergency Quarantine

Flow: revocation → quarantine → loader block → orchestrator stop — master §17, Step 5B quarantine.py pattern.

Scoped — not global EMIC kill — master §56, threat T32.

**Verdict:** **PASS**

---

## 34. Physical Safety

Safe-state table — isolation §7:

| Class | Safe state |
|-------|------------|
| EV charger | Stop charging; safe current limit |
| Vehicle | Halt pending commands |
| SPA/HVAC | Idle mode |
| Battery inverter | Hold safe setpoint; alert |
| Read-only telemetry | No action |

Broker implements safe-state before subprocess teardown.

**Note:** Implementation owner and device-specific safe-state validation remain for 5C.5 — design intent is present.

**Verdict:** **PASS**

---

## 35. Marketplace Architecture

Component split — master §60–61: Catalog, Revocation, Publisher governance, Artifact CDN, Advisory, Release approval.

Not monolithic — **PASS**.

**Verdict:** **PASS**

---

## 36. Data Model

Entities: Publisher, PublisherKey, ModuleListing, ModuleRelease, ReleaseSignature, ReleaseApproval, PackageArtifact, Revocation, SecurityAdvisory, ReleaseChannel, OrganizationPolicy, PublisherVerification.

ER diagram — data model §2.

Mapping to existing EMIC tables — data model §4.

Immutability: releases should be immutable (design intent; soft-delete for audit — recommend explicit immutability rule in §100).

**Verdict:** **PASS**

---

## 37. API Design

Read endpoints: catalog snapshot, modules, releases, revocations, advisories — API §2.

Future publisher/admin endpoints marked design-only — API §3–4.

EMIC-side future endpoints for 5C.3 — API §8 (not implemented).

Structured error contract — API §9.

**Verdict:** **PASS**

---

## 38. Authentication

| Actor | Mechanism | Separation |
|-------|-----------|------------|
| Publisher | OAuth + MFA (future) | Yes |
| Marketplace admin | Separate IAM | Yes |
| EMIC installation | Opaque install ID; no device credentials | Yes — API §6 |
| EMIC admin | Existing admin token | Yes |

**Verdict:** **PASS**

---

## 39. Caching / Offline

Local cache: catalog snapshot, revocation bundle, trust keys — master §64–65.

TTL by risk class — trust model §5.1.

Cache on catalog unavailable — trust model fail-safe §5.

**Cache poisoning:** Cached metadata must pass signature verification on read — implied; recommend explicit "verify on read" rule (§112).

**Cache rollback:** Monotonic snapshot version mitigates — partial.

**Verdict:** **PASS**

---

## 40. Air-Gapped

Signed offline import bundle — master §117–118, trust model Q7.

TUF root transfer pattern referenced.

Revocation bundle in bundle — data model §5.2.

Compatible with Internal Store local upload — master §124.

**Verdict:** **PASS**

---

## 41. Privacy

No energy usage, vehicle location, device credentials, household data to Marketplace — master §67–69.

Install telemetry: opaque ID, module_id, version, result only — API §6.

**Verdict:** **PASS**

---

## 42. Audit

Local audit: catalog sync, revocation merge, install attempt, policy denial, quarantine, break-glass, key rotation — master §81.

Central Marketplace audit for admin actions — implied via admin API design.

Log tampering: not explicitly addressed — recommend append-only central audit for Marketplace admin (§120).

**Verdict:** **PASS**

---

## 43. Incident Response

Publisher key compromise flow — master §13.

Bad release — revocation + quarantine.

Marketplace DB compromise — two-party model limits forge without publisher key.

Catalog signing key compromise — subkey rotation; root offline.

Module breakout — isolation + quarantine.

**Gap (M-05):** Root/offline key compromise step-by-step recovery underspecified.

**Verdict:** **PARTIAL PASS**

---

## 44. Store UX

Prose wireframes — master §75–79.

Tier badges: Official, Verified — not "Safe".

Needs-attention: quarantined, stale revocation, version mismatch.

Install review pattern reuses Step 5B PackageReviewPanel concept.

**Verdict:** **PASS**

---

## 45. Enterprise / Private Store

Org-hosted catalog mirror — master §114–116.

Stricter policy: OFFICIAL-only or allowlist.

Air-gapped import.

**Gap (M-02):** Source collision resolution algorithm not defined (§48, §134).

**Verdict:** **PARTIAL PASS**

---

## 46. Migration from Step 5B

Local upload unchanged — master §124.

`module_publisher_keys` extended later — no destructive rewrite.

Internal catalog JSON coexists.

Pre-5C debt: M6 + multi-site E2E before 5C.3 — **PASS**.

**Verdict:** **PASS**

---

## 47. Security Tests

Red team checklist — threat model §10 (10 scenarios).

G3: signature tests, offline cache for 5C.1.

G5: CDN swap + replay for 5C.3.

G6: escape, broker bypass, secret isolation, network egress, safe-state for 5C.5.

Recommend adding: TUF freeze, mixed metadata, publisher key compromise to G5.

**Verdict:** **PASS**

---

## 48. Red Team

Checklist present and actionable — threat model §10.

Automation candidates: catalog signature invalid, hash mismatch, revoked key before sync, permission escalation update.

**Verdict:** **PASS**

---

## 49. Implementation Phasing

| Phase | Scope | Gate |
|-------|-------|------|
| Pre-5C | M6 + multi-site E2E | Before 5C.3 |
| 5C.1 | Catalog/revocation client + trust cache | **This verification** |
| 5C.2 | Publisher governance + org policy | After 5C.1 G3 |
| 5C.3 | Remote download → existing installer | Pre-5C + H-01 + M-04 |
| 5C.4 | SBOM + advisories | After 5C.2 |
| 5C.5 | Subprocess isolation + RPC | After 5C.3; G6 before control RUN |
| 5C.6 | Public Store UI | After 5C.2–5C.4 + G7 |

**Finding H-01:** Trust model §3.2 allows org opt-in for Verified control in-process until 5C.5 — conflicts with G6. Requires explicit **Third-Party Execution Gate** (see §52 Required Fixes).

**Phasing §141–§143:** 5C.3 before 5C.5 is acceptable **if** download/validate/install-to-disk is separated from **RUN/enable** for control-capable third-party modules.

**Verdict:** **PARTIAL PASS**

---

## 50. Findings

### BLOCKER

None.

### HIGH

| ID | Finding | Owner | Gate |
|----|---------|-------|------|
| **H-01** | Phasing ambiguity: Verified control modules may run in-process with org opt-in until 5C.5, undermining G6 | Platform | Before 5C.3 |
| **H-02** | Subprocess isolation lacks mandatory OS hardening spec; plain subprocess ≠ sandbox | Platform | Before 5C.5 |
| **H-03** | "TUF-inspired" signed JSON lacks TUF role separation and freeze-attack guarantees | Security | 5C.1 implementation spec |

### MEDIUM

| ID | Finding | Owner | Gate |
|----|---------|-------|------|
| **M-01** | Security advisories unsigned — policy inputs could be spoofed | Marketplace | Before 5C.4 |
| **M-02** | No deterministic source precedence for same module_id across local/org/public Store | Platform | Before 5C.3 |
| **M-03** | Publisher/module ownership transfer policy missing | Marketplace | Before 5C.2 |
| **M-04** | SSRF, HTTP redirect, DNS rebinding not in threat model | Security | Before 5C.3 |
| **M-05** | Offline root key compromise recovery IR underspecified | Security | Before 5C.1 prod keys |
| **M-06** | Policy engine outputs lack explicit decision enum | Platform | Before 5C.2 |
| **M-07** | TLS cert pinning not specified; domain allowlist only | Platform | Before 5C.3 |

### LOW

| ID | Finding |
|----|---------|
| **L-01** | Audit uses `revocation_valid`; design uses `revocation_status` — naming only |
| **L-02** | Two-party model collapses for Official auto-approve — acceptable with documented exception |

### INFO

- Design result 49/49 self-PASS not accepted; independent score 74/100.
- Step 5B ValidationResult lacks `publisher_identity_valid` in code; design and module-sdk docs reference it — extend in 5C.1 trust cache work.

---

## 51. Readiness Scores

| Area | Score / 100 |
|------|-------------|
| Threat Model | 72 |
| Trust Boundaries | 85 |
| Publisher Governance | 70 |
| Key Management | 75 |
| Revocation | 80 |
| Root Trust | 65 |
| Catalog Signing | 68 |
| Artifact Distribution | 78 |
| Replay Protection | 82 |
| Dependency Security | 80 |
| Provenance | 75 |
| SBOM | 70 |
| Supply-chain Monitoring | 72 |
| Policy Engine | 70 |
| Isolation Strategy | 62 |
| Secret Isolation | 65 |
| Network Isolation | 60 |
| Control Broker | 78 |
| Emergency Quarantine | 80 |
| Physical Safety | 75 |
| Marketplace Architecture | 82 |
| Data Model | 85 |
| API Design | 80 |
| Offline Model | 78 |
| Privacy | 85 |
| Audit | 75 |
| Incident Response | 68 |
| UX Trust Model | 80 |
| Enterprise Policy | 72 |
| Migration from Step 5B | 88 |
| Test Strategy | 75 |
| Red Team Plan | 75 |
| Crypto Framework Choice | 72 |
| Implementation Phasing | 70 |

**STEP 5C DESIGN READINESS SCORE: 74 / 100**

---

## 52. Required Fixes (Design Documentation Only)

These are **documentation amendments** — not implementation. Must be completed before indicated gates.

### Before 5C.1 implementation (recommended alongside coding)

1. **H-03:** Publish `EMIC_SIGNED_SNAPSHOT_SPEC.md` OR mandate `python-tuf` in 5C.1 implementation plan with role mapping (root/targets/snapshot/timestamp).
2. **M-05:** Add offline root key compromise IR playbook section to master Step 5C doc or security runbook outline.

### Before 5C.2

3. **M-03:** Document publisher/module ownership transfer rules (no trust escalation via transfer).
4. **M-06:** Add policy engine output enum: `ALLOW`, `DENY`, `REQUIRE_ADMIN_APPROVAL`, `REQUIRE_SECURITY_REVIEW`.

### Before 5C.3 (mandatory gates)

5. **H-01 — Third-Party Execution Gate:** Add to master §137 and trust model §3.2:

   > No Verified or ORG_APPROVED **control-capable** module may **RUN** (site enable + orchestrator load) in production until G6 (5C.5 isolation + broker + safe-state tests) passes. 5C.3 may download, validate, and install-to-disk Official packages and Verified **read-only** modules only.

6. **M-02:** Define source precedence algorithm, e.g.:
   - Local admin upload > org private mirror > org policy-selected public catalog > default public catalog
   - Same module_id from two sources: higher precedence wins; lower ignored unless admin override with audit

7. **M-04:** Add threat rows and mitigations for SSRF (pinned URL only, no user URL, block private IP ranges), HTTP redirect (no redirects or same-host only), freeze attack (monotonic snapshot version + expires_at).

8. **M-07:** Document TLS policy: HTTPS required; optional cert pinning for Marketplace CDN with rotation procedure.

### Before 5C.4

9. **M-01:** Sign advisories or include in signed catalog snapshot; document advisory trust chain.

### Before 5C.5 (mandatory gates)

10. **H-02:** Extend isolation doc with mandatory OS controls for Verified control subprocess:
    - Linux prod: seccomp/AppArmor profile, network namespace or egress proxy, read-only rootfs, UID separation, FD/CPU/RAM limits
    - Windows dev: document reduced enforcement; prod Linux is enforcement target

11. Add attack trees: isolation escape, revocation failure.

12. G6 test plan: escape tests, broker bypass, secret isolation, network egress, safe-state under crash.

---

## 53. GO / NO-GO for 5C.1

### 5C.1 scope (allowed)

- Signed catalog snapshot client
- Signed revocation snapshot client
- Trust cache extension (local DB/filesystem)
- Signature verification against pinned Marketplace root keys
- Offline cache semantics and staleness tracking
- Admin status endpoint (`/api/modules/marketplace/status` — future, per API §8)

### 5C.1 non-goals (forbidden even at GO)

- Remote package install or enable
- Remote artifact download
- Public publisher signup
- Public Store UI
- Third-party module runtime
- Marketplace DB migrations on EMIC

### Gate assessment (§167)

| Criterion | Result |
|-----------|--------|
| No BLOCKERS | **PASS** |
| No unresolved HIGH in trust | **PASS** — tiers and field separation sound |
| No unresolved HIGH in revocation | **PASS** — model adequate for 5C.1 cache |
| No unresolved HIGH in catalog signing | **CONDITIONAL** — H-03 addressed via 5C.1 spec requirement, not blocking metadata client start |
| No unresolved HIGH in root trust | **PASS** — adequate for initial pin deployment; M-05 doc fix recommended |
| No unresolved HIGH in dependency identity | **PASS** |
| No unresolved HIGH in phasing affecting 5C.1 | **PASS** — H-01 gates 5C.3 only |
| No implementation leakage | **PASS** |
| Same local installer retained | **PASS** |
| Pre-5C debt not required for 5C.1 | **PASS** — M6/E2E gated to 5C.3 |

### Decision

**GO FOR STEP 5C.1**

5C.1 authorization is **narrow**: metadata sync and trust cache only. It does **not** authorize remote package download, public publisher onboarding, public marketplace, or third-party installation/execution.

---

## STEP 5C DESIGN VERIFICATION — Acceptance Table

| Criterion | Result |
|-----------|--------|
| No implementation leakage | **PASS** |
| Threat model | **PARTIAL** |
| Attack trees | **PARTIAL** |
| Trust boundaries | **PASS** |
| Publisher identity | **PARTIAL** |
| Publisher tiers | **PASS** |
| Key management | **PASS** |
| Key rotation | **PASS** |
| Revocation | **PASS** |
| Root trust | **PARTIAL** |
| Catalog signing | **PARTIAL** |
| Release signing | **PASS** |
| Artifact integrity | **PASS** |
| Replay protection | **PASS** |
| Downgrade protection | **PASS** |
| Dependency confusion | **PASS** |
| Namespace ownership | **PASS** |
| Package provenance | **PASS** |
| SBOM | **PARTIAL** |
| Vulnerability handling | **PARTIAL** |
| Supply-chain monitoring | **PASS** |
| Risk classification | **PASS** |
| Install policy engine | **PARTIAL** |
| Organization policy | **PASS** |
| Runtime isolation | **PARTIAL** |
| Module RPC | **PARTIAL** |
| Secret broker | **PASS** |
| Network policy | **PARTIAL** |
| Filesystem policy | **PARTIAL** |
| Device control broker | **PASS** |
| Emergency quarantine | **PASS** |
| Kill switch | **PASS** |
| Physical control safety | **PASS** |
| Marketplace architecture | **PASS** |
| Data model | **PASS** |
| API design | **PASS** |
| Offline/cache | **PASS** |
| Air-gapped | **PASS** |
| Privacy | **PASS** |
| Audit | **PASS** |
| Incident response | **PARTIAL** |
| Store UX | **PASS** |
| Enterprise/private Store | **PARTIAL** |
| Migration from Step 5B | **PASS** |
| Same local installer retained | **PASS** |
| TUF decision | **PARTIAL** |
| Sigstore decision | **PASS** |
| No custom crypto | **PASS** |
| Security test strategy | **PASS** |
| Red-team plan | **PASS** |
| Implementation phases | **PARTIAL** |
| Implementation gates | **PASS** |

---

## References

- [EMIC_STEP5C_DESIGN_RESULT.md](./EMIC_STEP5C_DESIGN_RESULT.md) (not used as evidence)
- [EMIC_MODULAR_ARCHITECTURE_STEP5C.md](./EMIC_MODULAR_ARCHITECTURE_STEP5C.md)
- [EMIC_MODULE_ECOSYSTEM_THREAT_MODEL.md](../security/EMIC_MODULE_ECOSYSTEM_THREAT_MODEL.md)
- [EMIC_MODULE_TRUST_MODEL.md](../security/EMIC_MODULE_TRUST_MODEL.md)
- [EMIC_MODULE_MARKETPLACE_DATA_MODEL.md](./EMIC_MODULE_MARKETPLACE_DATA_MODEL.md)
- [EMIC_MODULE_MARKETPLACE_API_DESIGN.md](./EMIC_MODULE_MARKETPLACE_API_DESIGN.md)
- [EMIC_MODULE_RUNTIME_ISOLATION.md](./EMIC_MODULE_RUNTIME_ISOLATION.md)
- [EMIC_STEP5B_VERIFICATION.md](./EMIC_STEP5B_VERIFICATION.md)
- [EMIC_MODULAR_ARCHITECTURE_STEP5B.md](./EMIC_MODULAR_ARCHITECTURE_STEP5B.md)

---

GO FOR STEP 5C.1
