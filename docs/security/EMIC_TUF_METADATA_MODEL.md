# EMIC Marketplace TUF Metadata Model (Step 5C.1)

**Status:** Implemented in Step 5C.1  
**Library:** [python-tuf](https://github.com/theupdateframework/python-tuf) (`tuf>=4`, ngclient `Updater`)  
**Scope:** Metadata-only trust channel — **no package artifact download**

---

## 1. Why TUF

Step 5C design verification finding **H-03** rejected a custom “TUF-inspired” single-blob JSON model because it lacks:

- Role separation (root / targets / snapshot / timestamp)
- Freeze-attack protection via timestamp expiry
- Mix-and-match protection via snapshot binding
- Monotonic version semantics and root rollback protection

EMIC Step 5C.1 implements **real TUF metadata** using python-tuf. HTTPS is transport-only; trust comes from **pinned root + verified metadata chain**.

---

## 2. Roles

| Role | Purpose in EMIC |
|------|-----------------|
| **root** | Defines trusted keys and thresholds for all roles; offline-pinned bootstrap |
| **targets** | Lists allowed metadata targets (`emic/catalog.json`, `emic/revocations.json`) with hashes |
| **snapshot** | Binds metadata file versions/hashes — prevents mix-and-match |
| **timestamp** | Freshness guard; references snapshot hash; short expiry |

Delegations are **not** used in 5C.1 but the layout does not preclude them later.

---

## 3. Root trust

- EMIC ships with **pinned root metadata** (`MARKETPLACE_TRUSTED_ROOT_PATH`, default: test fixture path in dev).
- Initial root is provisioned via software distribution / trusted provisioning / air-gapped import — **never** from an unauthenticated Marketplace “trust me” response.
- Only **public** root metadata is stored locally; private root keys are never on EMIC.

---

## 4. Targets

Allowed target paths (metadata JSON only):

```
emic/catalog.json      — marketplace catalog snapshot references
emic/revocations.json  — signed revocation bundle
```

**Not allowed in 5C.1:** `.emicpkg`, artifact URLs, or any binary package target.

---

## 5. Snapshot

Snapshot metadata binds `targets.json` version and hash. EMIC rejects updates where timestamp references a snapshot hash that does not match downloaded snapshot bytes.

---

## 6. Timestamp

Timestamp metadata:

- Is signed by the timestamp role key from root
- Has short expiry (configured on Marketplace repository)
- References snapshot version + hash

Expired timestamp → metadata rejected; **existing trust cache retained**.

---

## 7. Revocation representation

Revocations are a **dedicated targets entry**: `emic/revocations.json`.

The JSON bundle includes stable revocation identity fields (scope, publisher/module/version/hash, reason, severity, effective_at, metadata_version). Verification uses the same TUF chain as catalog metadata.

---

## 8. Metadata expiration

All roles carry `expires`. EMIC uses UTC and the minimum expiry across root/timestamp/snapshot/targets for cache policy. Clock skew: obviously invalid system time should surface trust diagnostics; expired metadata is never silently promoted.

---

## 9. Root rotation

Supported via standard TUF semantics:

1. Client bootstraps pinned root **N**
2. Repository serves signed root **N+1** (signed with root N keys, monotonic version)
3. After verification, trusted root version advances in cache

Invalid rotation (skipped version, bad threshold) → reject; cache unchanged.

---

## 10. Offline cache

Trust cache (`marketplace_trust_cache` DB table) stores:

- Trusted role versions, catalog/revocation JSON, expiry, sync timestamps, cache generation
- On sync failure: **keep last trusted cache**, set `sync_failed` and diagnostics
- Marketplace outage does **not** clear valid cache

---

## 11. Freeze protection

Serving expired timestamp metadata → **reject**. Automated test: `test_expired_timestamp_rejected`.

---

## 12. Rollback protection (Step 5C.1.5)

Defense in depth across **two layers**:

1. **Persistent python-tuf ngclient state** (`MARKETPLACE_TUF_STATE_PATH`) — metadata directory survives syncs and restarts; `Updater.refresh()` enforces TUF monotonic semantics within the client.
2. **Trust cache monotonic promotion gate** — before any `SUCCESS` is committed, `MarketplaceTrustCacheRepository.apply_sync_result()` rejects the entire candidate generation if any of `root_version`, `timestamp_version`, `snapshot_version`, or `targets_version` regresses versus the last trusted cache. Error code: `METADATA_ROLLBACK_DETECTED`. Audit: `marketplace.metadata_rejected` with `reason=rollback`.

Revocation bundles use monotonic `bundle.generation` with conservative merge: prior `REVOKE` entries remain active unless explicitly `SUPERSEDE`d in a newer signed generation. Generation rollback or wipe → reject.

Older root/timestamp/snapshot/targets/revocation generations than currently trusted → **reject**. Trusted cache row unchanged (generation not incremented; `last_success_at` preserved).

---

## 13. Mix-and-match protection

Snapshot hash in timestamp must match downloaded snapshot. Corrupted or substituted snapshot → **reject**. Test: `test_mix_and_match_snapshot_rejected`.

---

## 14. Recovery

| Scenario | Response |
|----------|----------|
| Root key compromise | See [`EMIC_MARKETPLACE_ROOT_KEY_IR.md`](./EMIC_MARKETPLACE_ROOT_KEY_IR.md) |
| Corrupt local cache | Status `invalid` / `unavailable`; no blind trust |
| Break-glass root reset | Local admin + offline trusted root artifact via software update |

---

## 15. Test fixtures

Location: `packages/energy-core/tests/fixtures/marketplace_tuf/`

- `pinned_root.json` — offline bootstrap (TEST ONLY)
- `repository/metadata/{root,timestamp,snapshot,targets}.json` + versioned copies
- `repository/targets/emic/{catalog,revocations}.json` + hashed paths for `consistent_snapshot`
- Generator: `generate_fixtures.py` (TEST ONLY keys — never production)

---

## 16. Non-goals (Step 5C.1)

- Remote `.emicpkg` download or install
- Public Store catalog UI
- Sigstore / in-toto (future optional)
- Runtime quarantine policy application
- Third-party module execution

---

## Implementation references

| Component | Path |
|-----------|------|
| TUF client | `energy_core/platform/modules/marketplace/tuf_client.py` |
| Trust cache | `energy_core/platform/modules/marketplace/trust_cache.py` |
| Sync service | `energy_core/platform/modules/marketplace/sync_service.py` |
| Admin API | `backend/app/api/marketplace_metadata.py` |
