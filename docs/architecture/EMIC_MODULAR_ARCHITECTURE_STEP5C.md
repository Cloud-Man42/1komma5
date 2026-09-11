# EMIC Step 5C – Public Module Ecosystem Security Architecture & Marketplace Design

**Date:** 2026-09-07  
**Status:** Design only — no implementation  
**Foundation:** [EMIC_MODULAR_ARCHITECTURE_STEP5B.md](./EMIC_MODULAR_ARCHITECTURE_STEP5B.md) (production Internal Store)  
**Verification baseline:** [EMIC_STEP5B_VERIFICATION.md](./EMIC_STEP5B_VERIFICATION.md) — 82/100, GO for Step 5C design

---

## §1 Executive Summary

Step 5C defines how EMIC evolves from an **admin-only Internal Module Store** (Step 5B) to a **governed public module ecosystem** with third-party publishers, signed catalog/revocation metadata, org install policy, and tiered runtime isolation — without implementing marketplace routes, remote download, or public UI in this phase.

**Primary question (§4):** How can EMIC safely distribute, install, update, and revoke third-party modules at scale without a compromised publisher, Store, CDN, or module compromising the platform or physical devices?

**Answer:** Reuse the proven Step 5B install pipeline (`PackageValidator` → `PackageInstaller` → `loader` → orchestrator), add **real TUF** signed catalog/revocation metadata feeds (Step 5C.1), two-party release approval, tiered publisher trust, install policy engine, and subprocess isolation for Verified control modules.

---

## §2 Step 5B Foundation Inventory

| Layer | Existing (Step 5B) | Gap for public ecosystem |
|-------|-------------------|--------------------------|
| Package crypto | Ed25519, canonical hash, `trust_store.py` | No central revocation feed, catalog signing, release approval |
| Install engine | validate → impact → install/update/rollback | No remote artifact fetch |
| Runtime | In-process `importlib` via `loader.py` | No process isolation; permissions install-time only |
| Trust UI | `trust_read_model.py`, admin Store | No public catalog, org policy engine |
| Namespace | `paths.py` — protected `core.*`, built-ins | No publisher namespace registry |
| Runtime truth | Redis `module_version`, `package_checksum` | No attestation chain to Marketplace |

All future remote installs **must** flow through existing package pipeline — no parallel install path.

---

## §3 Goals and Non-Goals

### Goals

- Threat model and trust architecture for public distribution
- Signed catalog + revocation metadata design
- Two-party release model (publisher + Marketplace approval)
- Install policy engine specification
- Runtime isolation strategy for third-party control modules
- Marketplace data model and API contracts
- Migration path from Step 5B without breaking local upload
- Implementation phase plan with GO criteria

### Non-Goals (absolute — no implementation in Step 5C)

- Remote package download implementation
- Public marketplace routes or UI
- Publisher self-signup production flow
- Community ratings/reviews
- Auto-update implementation (policy design only)
- Payment/licensing/billing
- DB migrations
- PoC unless required to validate crypto assumption

---

## §4 Primary Security Question

See §1. Full analysis: [EMIC_MODULE_ECOSYSTEM_THREAT_MODEL.md](../security/EMIC_MODULE_ECOSYSTEM_THREAT_MODEL.md).

---

## §5 Threat Model Summary

32 enumerated threats (T01–T32) across publisher, Marketplace, CDN, identity, runtime, and offline scenarios. Top attack trees: compromised publisher key, CDN swap, Marketplace backend compromise, dependency confusion, control-module lateral movement.

**Residual risks:** Official in-process modules (R01), revocation staleness offline (R02), install-only permission enforcement until 5C.5 (R04).

---

## §6 Trust Boundaries

Twelve trust domains defined in [EMIC_MODULE_TRUST_MODEL.md](../security/EMIC_MODULE_TRUST_MODEL.md): EMIC Core, Official/Verified/Community Publisher, Marketplace Backend, Catalog, CDN, Installation Client, Module Runtime, Device/Site, Secrets, Admin.

**Principle:** Each domain may assert only what it owns; verification is always downstream.

---

## §7 Publisher Trust Tiers

| Tier | Prod install | Control modules | Runtime |
|------|--------------|-----------------|---------|
| OFFICIAL | Allowed | Allowed | In-process |
| VERIFIED | Org policy | Subprocess (5C.5) | Tiered |
| ORG_APPROVED | Allowlist | Policy-dependent | Tiered |
| COMMUNITY | **Blocked** | N/A | Dev/lab |
| REVOKED | Quarantine | N/A | Stopped |

---

## §8 Trust Field Separation

Extend Step 5B `ValidationResult`:

- Existing: `signed`, `signature_valid`, `publisher_identity_valid`, `publisher_trusted`, `install_allowed`
- New: `release_approved`, `revocation_status`, `policy_allowed`, `risk_class`, `catalog_trusted`, `artifact_pinned`

Never collapse into single "trusted" boolean.

---

## §9 Publisher Identity & Onboarding

- Publisher **owns private signing key**; EMIC/Marketplace store **public key only**
- `publisher_id` + `key_id` bind signatures in package and release metadata
- Onboarding tiers:
  - **COMMUNITY:** Self-register (dev portal only; no prod)
  - **VERIFIED:** Legal entity, domain verification, security questionnaire, manual review
  - **OFFICIAL:** EMIC internal only

---

## §10 Publisher Portal (Design)

Future authenticated portal for Verified publishers:

- Submit release metadata + upload artifact to staging CDN
- View verification status, advisories, revocation notices
- Rotate keys (overlapping validity window)
- No private key upload to EMIC

---

## §11 Key Ceremony

- Publishers generate Ed25519 keypairs locally (documented in Module SDK)
- Public key registered via Marketplace verification workflow
- EMIC installations sync trusted keys from Marketplace snapshot + local org overrides
- Step 5B admin "Add publisher key" remains for ORG_APPROVED local allowlist

---

## §12 Key Rotation

- Overlap period: old + new key both valid (`valid_from` / `valid_until`)
- New releases signed with new key; old releases remain verifiable until key expiry
- Marketplace publishes key rotation in catalog root metadata
- EMIC trust cache merges rotations on sync

---

## §13 Key Compromise Incident Flow

1. Publisher reports compromise → Marketplace revokes key (signed revocation feed)
2. EMIC sync → quarantine packages signed with revoked key
3. CRITICAL control modules → auto-stop per policy
4. Publisher publishes new key + re-signed releases
5. Audit trail retained; advisory optional

---

## §14 Revocation Model

Polymorphic revocation scopes: `PUBLISHER`, `KEY`, `MODULE`, `VERSION`, `HASH`, `CHANNEL`.

Signed revocation bundle (see data model doc). EMIC merges into local trust cache on sync.

---

## §15 Revocation SLA

| Risk class | Degraded after | Offline grace |
|------------|----------------|---------------|
| CRITICAL | 1h | 24h (commands restricted) |
| HIGH | 6h | 72h |
| NORMAL/LOW | 24h | 7d |

---

## §16 Offline Revocation Behavior

- Cached revocation bundle valid within grace
- Beyond SLA: degraded banner; block new remote installs; restrict CRITICAL control
- Air-gapped import bundle: signed offline snapshot (TUF root transfer pattern)

---

## §17 Emergency Quarantine

Scoped revocation — never whole-installation shutdown. Module-level quarantine reuses Step 5B `quarantine.py` + loader startup policy.

---

## §18 Catalog & Release Signing

**Real TUF** signed catalog/revocation metadata (python-tuf, Step 5C.1) listing module targets with hash, URL, release sequence, publisher, approval key reference. Package bytes verified separately at download time (5C.3).

---

## §19 Release Metadata Schema

See [EMIC_MODULE_MARKETPLACE_DATA_MODEL.md](./EMIC_MODULE_MARKETPLACE_DATA_MODEL.md) — `ModuleRelease`, `ReleaseApproval`, canonical JSON signing.

---

## §20 URL Allowlist & Pinning

- Artifact URL must appear in signed release metadata
- CDN domain allowlist in EMIC config (e.g. `cdn.emic.example`, publisher-specific subdomains after verification)
- No user-supplied arbitrary URLs

---

## §21 Catalog Freshness

- Snapshot `expires_at` — EMIC rejects expired snapshots for new installs
- Version counter monotonic — detect rollback of catalog itself

---

## §22 Channel Model

Channels: `stable`, `beta`, `internal`. Org policy selects allowed channels. Auto-update policy design-only (`MANUAL`, `NOTIFY`, `AUTO`).

---

## §24 Two-Party Release Model

1. **Publisher** signs `.emicpkg` (existing Ed25519 — unchanged)
2. **Marketplace** signs **release approval record** binding: module_id, version, content_sha256, release_sequence, publisher_key_id

Marketplace **does not** re-sign package as publisher. Two signatures, two roles.

---

## §25 Release Approval Workflow

1. Publisher uploads artifact + metadata
2. Automated checks: signature, manifest schema, permission diff, SBOM presence (Verified+)
3. Human or policy auto-approve for Official tier
4. Marketplace release key signs approval record
5. Entry appears in next catalog snapshot

---

## §29 Replay & Downgrade Protection

- `release_sequence` monotonic per module
- `published_at` in signed metadata
- Revoked-version list in revocation feed
- Step 5B `VERSION_DOWNGRADE_NOT_ALLOWED` retained
- Minimum version policy (org optional)

---

## §30 Dependency Security

- Explicit `module_dependencies` in manifest — no transitive auto-resolve
- Dependency must be Official, same publisher, or org-allowlisted
- Permission/capability diff on update triggers review

---

## §31 Namespace Registry

- Canonical `module_id` ownership by verified publisher
- Protected: `core.*`, `platform.*`, built-in integration IDs (`paths.py`)
- Squatting rejected at listing creation

---

## §32 Module ID Squatting Prevention

First verified owner wins for namespace prefix. Official modules reserved. Typosquat review for Verified listings.

---

## §33 Provenance Strategy

- Package signature = primary provenance (Step 5B)
- Release approval = governance provenance (Step 5C)
- Optional Sigstore attestation for Verified CI builds (future)

---

## §34 SBOM Strategy

CycloneDX JSON referenced in release metadata. Scanner ingests SBOM; vulnerability status from scanner only — not self-reported by publisher.

---

## §35 Vulnerability Status

Advisory feed (`GET /v1/advisories`) linked to module versions. Install policy may block installs with open CRITICAL CVEs (org configurable).

---

## §36–§37 Supply-Chain Metadata

Release record includes: `content_sha256`, `manifest_digest`, `sbom_ref`, `permissions`, `capabilities`, `dependencies`, `risk_class`. Deterministic inputs for risk scoring.

---

## §38–§41 Supply-Chain Monitoring

Risk score inputs (design):

- Publisher tier
- Permission/capability class changes on update
- Open advisories
- Revocation history
- SBOM scan results

Outputs: Store badge, policy gate, manual review queue — no automatic prod block without policy rule.

---

## §42 Install Policy Engine

**Inputs:** trust fields, `risk_class`, org tier policy, allowlist, advisory status, revocation staleness, channel.

**Outputs:** `policy_allowed`, install block reason, runtime mode requirement.

Runs after `PackageValidator`, before `PackageInstaller`.

---

## §43 Org Allowlist

`OrganizationPolicy` entity — allowed tiers, explicit publisher allowlist, control-module policy, break-glass for non-CRITICAL.

---

## §44 Control-Module Elevated Requirements

`device.control` and energy control capabilities require OFFICIAL or VERIFIED tier + release approval + (future) subprocess isolation.

---

## §47–§48 Runtime Isolation

Full analysis: [EMIC_MODULE_RUNTIME_ISOLATION.md](./EMIC_MODULE_RUNTIME_ISOLATION.md).

Tiered: Official in-process; Verified read-only in-process with brokers; Verified control → subprocess + Module RPC.

---

## §50 Module RPC

Minimal IPC contract: start/stop/health/capabilities/read/command/config over JSON-RPC or gRPC on Unix socket / named pipe.

---

## §51–§55 Brokers (Design)

| Broker | Purpose |
|--------|---------|
| Secret | Module requests own secret by key only |
| Network | Enforce `network.external` / `network.local` at OS level when isolated |
| Filesystem | Scoped paths per module |
| Device control | Capability + permission + site policy gate for high-risk commands |

---

## §56–§59 Kill Switch & Physical Safety

- Scoped signed revocation — not global EMIC kill
- CRITICAL modules → safe-state on quarantine (charger stop, vehicle command halt, SPA idle)
- Audit all emergency actions
- Org admin cannot override CRITICAL revocation

---

## §60–§61 Marketplace Backend Components

| Component | Responsibility |
|-----------|----------------|
| Catalog service | Signed snapshots, module listings |
| Revocation service | Signed revocation bundles |
| Publisher governance | Verification, tier management |
| Artifact CDN | Opaque bytes; integrity via hash+sig |
| Advisory service | CVE linkage |
| Release approval | Two-party signing workflow |

---

## §63 EMIC Installation Client Flow

1. Fetch signed catalog snapshot → verify Marketplace catalog key
2. Fetch signed revocation snapshot → verify + merge trust cache
3. Select release → verify publisher + approval signatures on metadata
4. Download artifact from pinned URL → verify hash + package signature via `PackageValidator`
5. Run existing install/update path (`PackageInstaller`)

See [EMIC_MODULE_MARKETPLACE_API_DESIGN.md](./EMIC_MODULE_MARKETPLACE_API_DESIGN.md).

---

## §64–§65 Caching & Offline

- Local cache: catalog snapshot, revocation bundle, trust keys
- TTL per risk class (trust model §5.1)
- Air-gapped: import signed bundle via admin UI (future)

---

## §67–§69 Privacy, Telemetry, Audit

- **Install identity:** opaque install ID for aggregate telemetry — no device credentials to Marketplace
- **Audit:** all install/update/revoke/quarantine events local + optional anonymized telemetry
- **Privacy:** site data never uploaded; only module install events and versions

---

## §75–§79 Store UX (Prose Wireframes)

**Public Store (future 5C.6):**

- Browse by category, publisher tier badge (Official/Verified)
- Module detail: capabilities, permissions, dependencies, advisories, release notes
- Install button → policy check → download → existing review panel pattern from Step 5B
- Needs-attention: quarantined, stale revocation, version mismatch

**Enterprise admin:**

- Org policy page: allowed tiers, allowlist, break-glass
- Private Store mirror option (§114)

Local upload path unchanged — admin Store tab remains.

---

## §81 Audit Requirements

Log: catalog sync, revocation merge, remote install attempt, policy denial, quarantine, break-glass override, key rotation.

---

## §86–§88 Fail-Safe Matrix

See [EMIC_MODULE_TRUST_MODEL.md](../security/EMIC_MODULE_TRUST_MODEL.md) §5. Default: fail-closed for install; degraded (not brick) for stale revocation.

---

## §92–§95 TUF / Sigstore Analysis

### TUF

**Use for:** Catalog snapshots, revocation bundles, root key hierarchy.

**Not for:** `.emicpkg` format — existing Ed25519 direct signing is sufficient and production-proven.

**Rationale:** TUF provides snapshot semantics, expiry, and offline root transfer without inventing custom update crypto.

### Sigstore

**Optional** for Verified publisher CI attestation (cosign + Rekor). Links build identity to published artifact hash.

**Not required for v1.** Ed25519 publisher signing + Marketplace approval sufficient for launch.

### Custom Protocol Rejection

Explicitly reject:

- Marketplace re-signing packages as if it were the publisher
- Custom kill-switch crypto outside signed revocation feed
- Unsigned catalog "trust on first use" for control modules

---

## §96–§98 Auth Separation

| Actor | Auth mechanism |
|-------|----------------|
| Publisher portal | OAuth + MFA; publisher-scoped API tokens |
| Marketplace admin | Separate admin IAM; no publisher token overlap |
| EMIC installation | No device credentials to Marketplace; opaque install ID for telemetry |
| EMIC admin | Existing admin token for local policy + local upload |

---

## §99–§100 Rate Limiting & Abuse

- Catalog/revocation: CDN cached; rate limit by install ID + IP
- Publisher upload: size limits, scan queue, tier-based quotas
- Community tier: staging only; no prod CDN path

---

## §114–§116 Enterprise / Private Store

- Org-hosted catalog mirror (signed snapshots replicated)
- Stricter policy: OFFICIAL-only or explicit allowlist
- Air-gapped import bundle signed by org or EMIC enterprise key

---

## §117–§118 Air-Gapped Install

1. Admin exports signed catalog + revocation + artifact bundle on connected machine
2. Import via admin UI on air-gapped EMIC
3. Verify all signatures locally
4. Install via existing pipeline

---

## §124–§125 Migration from Step 5B

| Step 5B artifact | Step 5C evolution |
|------------------|-------------------|
| Local upload | Unchanged |
| `module_publisher_keys` | Add `valid_from`, `valid_until`, tier; sync from Marketplace |
| Internal catalog JSON | Coexists with remote catalog client |
| Store UI | Extended in 5C.6; local path unchanged |
| `PackageValidator` | Extended inputs from policy engine — core crypto unchanged |
| Loader/orchestrator | Isolation wrapper in 5C.5 |

**Pre-5C debt:** Close M6 frontend Store tests + package multi-site E2E before 5C.3 public download.

---

## §126 Pipeline Reuse (Mandatory)

```text
Remote fetch (5C.3) → PackageValidator → PackageInstaller → loader → orchestrator
```

No bypass. Admin local upload continues: `upload → validate → install`.

---

## §130 Document Index

| # | Topic | Location |
|---|-------|----------|
| Threat model | Full STRIDE + attack trees | [EMIC_MODULE_ECOSYSTEM_THREAT_MODEL.md](../security/EMIC_MODULE_ECOSYSTEM_THREAT_MODEL.md) |
| Trust model | Domains, tiers, fail-safe | [EMIC_MODULE_TRUST_MODEL.md](../security/EMIC_MODULE_TRUST_MODEL.md) |
| Data model | ER, JSON schemas | [EMIC_MODULE_MARKETPLACE_DATA_MODEL.md](./EMIC_MODULE_MARKETPLACE_DATA_MODEL.md) |
| API design | Endpoints, client flow | [EMIC_MODULE_MARKETPLACE_API_DESIGN.md](./EMIC_MODULE_MARKETPLACE_API_DESIGN.md) |
| Runtime isolation | Matrix, RPC, brokers | [EMIC_MODULE_RUNTIME_ISOLATION.md](./EMIC_MODULE_RUNTIME_ISOLATION.md) |
| Design result | Acceptance, GO criteria | [EMIC_STEP5C_DESIGN_RESULT.md](./EMIC_STEP5C_DESIGN_RESULT.md) |

---

## §136 Security Stack Recommendation (Crypto Decision)

**Hybrid model — do not invent custom crypto protocol.**

| Layer | Standard | Rationale |
|-------|----------|-----------|
| Package artifact | **Ed25519 direct signing** (existing) | Production-proven in Step 5B; publisher identity bound to package |
| Catalog + revocation metadata | **Real TUF metadata** (python-tuf) | Role separation, freeze/rollback/mix-and-match protection; offline cache |
| Publisher CI attestation | **Sigstore/cosign optional** (future) | Verified tier provenance; not required v1 |
| Marketplace release approval | **Separate Ed25519 key** (EMIC release signing) | Two-party model: publisher signs package, Marketplace signs approval record |

**Explicit rejections:**

- Marketplace re-signing packages as publisher
- Custom kill-switch protocol outside signed revocation feed
- Replacing Ed25519 package signing with TUF targets for artifacts

---

## §137 Implementation Phases

| Phase | Scope | Depends on |
|-------|-------|------------|
| **Pre-5C** | M6 frontend tests + multi-site E2E | Step 5B.5 |
| **5C.1** | Signed catalog/revocation client; trust cache extension | Pre-5C |
| **5C.2** | Publisher governance; Verified onboarding; org policy engine | 5C.1 |
| **5C.3** | Remote artifact download via pinned URL → existing installer; air-gapped bundle | 5C.1 |
| **5C.4** | Supply-chain monitoring, SBOM ingest, advisories | 5C.2 |
| **5C.5** | Subprocess isolation + Module RPC for Verified control | 5C.3 |
| **5C.6** | Public Store UI + Enterprise policy admin | 5C.2–5C.4 |

Each phase requires independent security verification before next.

---

## §140–§143 Acceptance & GO

Full §140 table and §141 decisions in [EMIC_STEP5C_DESIGN_RESULT.md](./EMIC_STEP5C_DESIGN_RESULT.md).

**§143 Implementation GO criteria (summary):**

- Step 5C design verification PASS
- Pre-5C debt closed (M6, multi-site E2E)
- Red team checklist exercised for 5C.1+
- No public routes until 5C.6 verification

---

## §141 Critical Decisions (Summary)

See trust model §6 for full Recommendation / Alternatives / Reasoning on all eleven questions.

---

## §142 Risks & Open Questions

| Risk | Mitigation |
|------|------------|
| In-process Official modules | Accept with supply-chain controls; monitor |
| Permission enforcement lag | 5C.5 broker roadmap |
| Marketplace root compromise | Offline root + rotation IR |
| Verified bad actor | Revocation + monitoring + tier review |

**Open for implementation verification:** Subprocess IPC performance on edge hardware; Windows named pipe vs Unix socket parity.

---

## Out of Scope (Repeated)

No remote download, public routes, publisher signup prod, community catalog, auto-update impl, payment, DB migrations, or PoC enabling public distribution.

---

## References

- [EMIC_MODULAR_ARCHITECTURE_STEP5B.md](./EMIC_MODULAR_ARCHITECTURE_STEP5B.md)
- [EMIC_STEP5B_VERIFICATION.md](./EMIC_STEP5B_VERIFICATION.md)
- [docs/module-sdk/security.md](../module-sdk/security.md)
- `packages/energy-core/src/energy_core/platform/modules/packages/`
