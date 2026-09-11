# EMIC Organization Module Policy

**Date:** 2026-09-08  
**Scope:** Step 5C.2 — installation policy engine, precedence, break-glass  
**Related:** [EMIC_PUBLISHER_GOVERNANCE.md](./EMIC_PUBLISHER_GOVERNANCE.md)

---

## 1. Policy row

Single installation policy (`policy_scope=installation`) in `module_installation_policy`:

| Field | Description |
|-------|-------------|
| `allowed_tiers` | Tiers permitted for install evaluation |
| `publisher_allowlist` / `publisher_denylist` | Publisher overrides |
| `module_allowlist` / `module_denylist` | Module overrides |
| `blocked_permissions` | Deny if manifest requests permission |
| `control_module_policy` | `OFFICIAL_ONLY` or `VERIFIED_OK` |
| `break_glass_enabled` | Allow scoped break-glass overrides |
| `policy_version` | Optimistic concurrency |

History snapshots append to `module_policy_history`.

---

## 2. Production-safe defaults

```json
{
  "allowed_tiers": ["OFFICIAL", "VERIFIED", "ORG_APPROVED"],
  "control_module_policy": "VERIFIED_OK",
  "break_glass_enabled": false
}
```

`COMMUNITY` is denied in production by default. `REVOKED` is always denied.

---

## 3. Deterministic precedence (deny > allow)

1. Active CRITICAL revocation → `DENY`
2. Module denylist → `DENY`
3. Publisher denylist → `DENY`
4. Suspended publisher → `DENY`
5. Blocked permission → `DENY`
6. Control-capable + action `RUN`/`ENABLE` before Step 5C.5 → `DENY`
7. Tier not in `allowed_tiers` / COMMUNITY in prod → `DENY` (unless break-glass)
8. Explicit module allowlist → `ALLOW`
9. Publisher allowlist + tier match → `ALLOW`
10. Tier in `allowed_tiers` → `ALLOW`
11. Default → `DENY`

---

## 4. Policy decision enum (M-06)

| Decision | Meaning |
|----------|---------|
| `ALLOW` | Policy would permit (evaluate-only in 5C.2) |
| `DENY` | Policy blocks |
| `REQUIRE_ADMIN_APPROVAL` | Reserved |
| `REQUIRE_SECURITY_REVIEW` | Reserved for control/security gates |

Reason codes include `PUBLISHER_REVOKED`, `TIER_NOT_ALLOWED`, `COMMUNITY_NOT_ALLOWED`, `REVOCATION_ACTIVE`, `CONTROL_MODULE_ISOLATION_REQUIRED`, `DEFAULT_DENY`, etc.

---

## 5. Break-glass

When `break_glass_enabled=true`, admin may activate a time-bounded session (`POST .../break-glass/activate`).

Break-glass may override non-critical tier/org restrictions only. It **never** overrides:

- Revocation (CRITICAL)
- Invalid signature
- `REVOKED` publisher status

---

## 6. Integration

- `ModuleInstallPolicyEngine.evaluate()` — pure, no HTTP
- `PackageValidator` attaches `policy_decision`, `policy_reason_codes`, `publisher_tier` to `ValidationResult` when DB session available
- `install_allowed` unchanged in 5C.2

---

## 7. PUT conflict

Policy updates require `expected_version`. Mismatch returns `409 POLICY_CONFLICT`.
