# EMIC Step 5C.1 – Implementation Notes

**Date:** 2026-09-07  
**Phase:** Trusted Metadata, TUF Catalog & Revocation Client  
**Status:** Step 5C.1.5 hardening complete — see [`EMIC_STEP5C_1_5_RESULT.md`](./EMIC_STEP5C_1_5_RESULT.md)

---

## 1. Objective

Establish a **metadata-only**, **TUF-verified** trust channel between a future public Marketplace and local EMIC — without remote package download, install, or third-party runtime.

---

## 2. Dependencies

- `tuf>=4.0` (resolved: 7.0.1) in `packages/energy-core/pyproject.toml`
- `securesystemslib` (TUF signing)

---

## 3. Core modules

| Module | Responsibility |
|--------|----------------|
| `marketplace/tuf_client.py` | `MarketplaceMetadataClient` — python-tuf `Updater`, pinned bootstrap, persistent TUF state dir, `HttpxFetcher` (HTTPS, no redirects, size limits, stable error codes) |
| `marketplace/trust_cache.py` | DB-backed cache, monotonic promotion gate, staleness, cache validation (`INVALID`), status view |
| `marketplace/revocation_policy.py` | Revocation bundle parsing, monotonic generation, conservative merge / supersession |
| `marketplace/sync_service.py` | Async orchestration, process-local sync lock, feature-flag gating, `TrustMetadataUpdatedEvent` emission |
| `marketplace/types.py` | Health enums, stable `MetadataErrorCode`, allowed targets, event hook |

---

## 4. Database

- Model: `MarketplaceTrustCacheModel`
- Migration: `065_marketplace_trust_cache.py`, `066_marketplace_trust_cache_hardening.py`
- Single authoritative row (`cache_key=default`) with `cache_generation` for atomic promotion

---

## 5. Configuration (`energy_core.config.Settings`)

| Setting | Default | Notes |
|---------|---------|-------|
| `MARKETPLACE_METADATA_ENABLED` | `false` | Dormant deploy |
| `MARKETPLACE_METADATA_URL` | `""` | HTTPS required in production |
| `MARKETPLACE_TARGETS_URL` | `""` | Targets base URL |
| `MARKETPLACE_TRUSTED_ROOT_PATH` | fixture fallback in dev | Pinned root JSON |
| `MARKETPLACE_TUF_STATE_PATH` | `.emic-marketplace-tuf` in dev/test | Persistent ngclient metadata dir |
| `MARKETPLACE_SYNC_INTERVAL_SECONDS` | `3600` | Background loop |
| Timeouts / max bytes | configured | DoS guards |

---

## 6. Backend API

| Method | Path | Auth |
|--------|------|------|
| GET | `/api/modules/marketplace/status` | Admin |
| POST | `/api/modules/marketplace/sync` | Admin |

Background: `backend/app/marketplace_sync.py` — backoff + jitter on failure.

---

## 7. Security controls

- Real TUF roles (root/targets/snapshot/timestamp)
- Pinned offline root; monotonic root rotation
- Persistent TUF client state + cache monotonic promotion (cross-sync rollback protection)
- Revocation monotonic generation with explicit SUPERSEDE semantics
- Stable error taxonomy (`MetadataErrorCode`)
- No redirects; metadata size limits; fail-closed on TLS/verify errors
- Unverified or rollback metadata never committed to cache
- Process-local sync lock (`SYNC_IN_PROGRESS` / HTTP 409)
- Architecture guards: no `PackageInstaller` / orchestrator imports in marketplace layer

---

## 8. Frontend (minimal)

Internal Store overview shows read-only Marketplace metadata health (`ModuleStoreOverview`).

**No** public catalog browse or remote install UI.

---

## 9. Tests

| File | Coverage |
|------|----------|
| `test_marketplace_tuf_security.py` | Freeze, bad sig, unknown root, rotation, mix-and-match |
| `test_marketplace_trust_cache.py` | Cache, staleness, offline |
| `test_marketplace_status_api.py` | Admin auth, sync |
| `test_step5c_guards.py` | Architecture guards |

Fixtures: `packages/energy-core/tests/fixtures/marketplace_tuf/` (TEST ONLY).

---

## 10. Documentation

- [`EMIC_TUF_METADATA_MODEL.md`](../security/EMIC_TUF_METADATA_MODEL.md)
- [`EMIC_MARKETPLACE_ROOT_KEY_IR.md`](../security/EMIC_MARKETPLACE_ROOT_KEY_IR.md)
- Updated Step 5C design docs: TUF implementation replaces “TUF-inspired” for metadata layer

---

## 11. Explicit non-goals (5C.1)

Remote artifact download, public Store, publisher signup, marketplace DB on EMIC (beyond trust cache), runtime quarantine, third-party execution path.
