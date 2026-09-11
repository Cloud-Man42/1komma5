# EMIC Publisher Governance

**Date:** 2026-09-08  
**Scope:** Step 5C.2 — publisher entity, lifecycle, keys, verification, ownership  
**Related:** [EMIC_ORGANIZATION_MODULE_POLICY.md](./EMIC_ORGANIZATION_MODULE_POLICY.md), [EMIC_MODULE_TRUST_MODEL.md](./EMIC_MODULE_TRUST_MODEL.md)

---

## 1. Publisher entity

Each publisher is stored in `module_publishers` with:

| Field | Purpose |
|-------|---------|
| `publisher_id` | Stable identifier (matches manifest `publisher`) |
| `display_name` | Human-readable label |
| `tier` | Trust tier (`OFFICIAL`, `VERIFIED`, `ORG_APPROVED`, `COMMUNITY`, `REVOKED`) |
| `status` | Lifecycle status (independent of tier) |
| `verified_at` / `suspended_at` / `revoked_at` | Audit timestamps |

Keys remain in `module_publisher_keys` (Step 5B) with optional validity/revocation metadata.

---

## 2. Lifecycle

```text
create → PENDING_VERIFICATION → ACTIVE
ACTIVE ↔ SUSPENDED
ACTIVE → REVOKED (terminal)
```

Invalid transitions (e.g. `REVOKED → ACTIVE`) are rejected by `PublisherRepository`.

Revoking a publisher sets `tier=REVOKED` and `status=REVOKED`.

---

## 3. Verification (5C.2)

Manual admin verification only (no DNS challenge in 5C.2):

- `POST /api/modules/governance/publishers/{id}/verify`
- Creates a `module_publisher_verifications` record
- Activates publisher; may promote `COMMUNITY → VERIFIED` on verify

Re-verification cadence may use `expires_at` on verification records (documented for future automation).

---

## 4. Key governance

- Ed25519 public keys only (`module_publishers` API + governance UI)
- Reject any payload containing `private_key`, `seed`, or similar
- Key status: `trusted`/`ACTIVE`, `revoked`, `disabled`

---

## 5. Module ownership

Canonical mapping: `module_ownership` (`module_id → publisher_id`).

Protected namespaces (`core.*`, `platform.*`, built-in IDs via `is_protected_module_id`) cannot be transferred or reassigned via external paths.

---

## 6. Ownership transfer (M-03)

Workflow: `PENDING → APPROVED → COMPLETED` (or `REJECTED`).

**No trust escalation:** On completion, ownership moves to target publisher; effective tier is taken from the **target** publisher, not the source. Transferred modules do not inherit source tier or signatures.

Official/protected modules are non-transferable.

---

## 7. Admin API

Base path: `/api/modules/governance` (admin token required).

| Area | Routes |
|------|--------|
| Publishers | CRUD, verify, suspend, reactivate, revoke |
| Policy | GET/PUT installation policy, impact summary |
| Ownership | List, transfer request/approve/reject/complete |
| Evaluate | POST dry-run (no mutation) |
| Break-glass | POST activate, GET status |

Stable error codes include `PUBLISHER_REVOKED`, `POLICY_DENIED`, `OWNERSHIP_TRANSFER_NOT_ALLOWED`, `POLICY_CONFLICT`.

---

## 8. Evaluate-only in 5C.2

`install_allowed` remains on the crypto/trust-store path. Policy decisions appear in validate preview, dry-run API, and governance UI diagnostics only.
