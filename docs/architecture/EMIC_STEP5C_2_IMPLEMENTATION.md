# Step 5C.2 Implementation — Publisher Governance & Organization Policy

**Date:** 2026-09-08  
**Status:** Implemented (evaluate-only policy integration)

---

## Delivered components

### Core (`energy_core/platform/modules/governance/`)

| Module | Role |
|--------|------|
| `types.py` | Tiers, status, `PolicyDecision`, reason codes, snapshots |
| `policy_engine.py` | Deterministic `ModuleInstallPolicyEngine.evaluate()` |
| `policy_repository.py` | Installation policy CRUD + optimistic versioning |
| `publisher_repository.py` | Publisher lifecycle state machine |
| `ownership_repository.py` | Canonical module ownership |
| `transfer_repository.py` | Transfer workflow (PENDING→APPROVED→COMPLETED) |
| `verification_repository.py` | Manual verification records |
| `revocation_reader.py` | Read-only adapter over 5C.1 trust cache |
| `risk_classifier.py` | Control-capable detection |
| `break_glass.py` | Process-local break-glass sessions |
| `evaluation_service.py` | Orchestrates engine + repositories |

### Database

- Migration `067_module_governance.py`
- Tables: `module_publishers`, `module_publisher_verifications`, `module_ownership`, `module_ownership_transfers`, `module_installation_policy`, `module_policy_history`
- Extended `module_publisher_keys` with validity/revocation columns
- Seed: default installation policy, `emic` OFFICIAL publisher, backfill from existing keys

### Backend API

- `backend/app/api/module_governance.py` — admin routes under `/api/modules/governance`
- Registered in `backend/app/main.py`
- Extended `ValidationResult` + `PackageValidator` (evaluate-only; `install_allowed` unchanged)
- Extended `ValidationResponse` in `module_packages.py`

### Frontend

- Nav entries for Governance (Publishers, Policy, Diagnostics)
- `governance/GovernancePublishersPanel.tsx`
- `governance/OrganizationPolicyPanel.tsx`
- `governance/PolicyDiagnosticsPanel.tsx`
- API client functions in `frontend/src/lib/api.ts`

### Tests

- `packages/energy-core/tests/platform/governance/*` (engine, repos, security)
- `backend/tests/test_governance_api.py`
- Extended `test_step5c_guards.py` for governance boundaries
- Frontend Vitest for policy editor + diagnostics

### Documentation

- [EMIC_PUBLISHER_GOVERNANCE.md](../security/EMIC_PUBLISHER_GOVERNANCE.md)
- [EMIC_ORGANIZATION_MODULE_POLICY.md](../security/EMIC_ORGANIZATION_MODULE_POLICY.md)
- Updated [EMIC_MODULE_TRUST_MODEL.md](../security/EMIC_MODULE_TRUST_MODEL.md) §3.3–3.4

---

## Explicit non-goals (5C.2)

- Remote artifact download / remote install
- Public marketplace / publisher signup portal
- Policy enforcement on `install_allowed` (evaluate-only)
- Runtime quarantine side effects
- Invalid trust-cache online auto-recovery (documented debt from 5C.1)

---

## Policy integration note

`PackageValidator` calls `GovernanceEvaluationService` when an `AsyncSession` is provided. Policy fields are attached to `ValidationResult` for preview/UI; **`install_allowed` remains on crypto/trust-store path**.
