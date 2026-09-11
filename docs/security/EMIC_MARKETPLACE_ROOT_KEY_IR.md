# EMIC Marketplace Root Key Compromise — Incident Response (M-05)

**Status:** Step 5C.1 IR playbook (documentation)  
**Applies to:** Marketplace **root** signing key compromise (not publisher package keys)

---

## 1. Detection

| Signal | Owner |
|--------|-------|
| Unexpected root version in EMIC status (`root_version` jump without planned rotation) | EMIC admin / ops |
| Marketplace security advisory in signed metadata (future) | EMIC sync diagnostics |
| External report of root key leak | Security / Marketplace ops |
| Failed metadata sync spike + signature failures across fleet | Monitoring |
| Audit events: `marketplace.metadata_rejected`, abnormal `marketplace.root_rotated` | EMIC audit log |

**Immediate checks:**

1. `GET /api/modules/marketplace/status` on affected installations (admin)
2. Compare trusted root version vs planned rotation bulletin
3. Verify metadata chain with offline pinned root artifact from secure release channel

---

## 2. Containment

1. **Disable remote metadata sync** if attacker-controlled metadata is suspected: `MARKETPLACE_METADATA_ENABLED=false` (feature flag — dormant safe mode).
2. **Do not** accept arbitrary “new root” over HTTPS without verified rotation chain from **known-good** pinned root.
3. Preserve audit logs and last known-good trust cache generation for forensics.
4. Internal Store / locally installed packages continue under existing local trust policy until revocation cache expires (see grace policy).

---

## 3. Root rotation (legitimate emergency rotation)

When Marketplace operators rotate root using proper TUF semantics:

1. Publish root **N+1** signed with root **N** keys (monotonic)
2. Ship updated **pinned root bootstrap** in EMIC patch release for fresh installs
3. Online installations with root N bootstrap auto-fetch N+1 after verification
4. EMIC records `marketplace.root_rotated` audit event

---

## 4. Out-of-band trust reset

If online rotation chain is untrusted (compromise suspected):

1. Stop metadata sync
2. Distribute new pinned root via **software update** or **air-gapped import** (signed EMIC release artifact)
3. Local admin executes break-glass root reset procedure (requires admin auth + offline artifact)
4. Clear or invalidate corrupt trust cache row; re-sync from known-good repository

---

## 5. Software update path

- EMIC patch includes new `MARKETPLACE_TRUSTED_ROOT_PATH` default or migration hook
- Release notes document root key ID change and minimum EMIC version
- Staging validation: bootstrap → sync → HEALTHY before prod rollout

---

## 6. Air-gapped recovery

1. Import pinned root JSON from trusted removable media
2. Configure metadata URL to internal mirror (HTTPS)
3. Manual admin sync: `POST /api/modules/marketplace/sync`
4. Verify status HEALTHY and root version matches bulletin

---

## 7. Grace policy

| Cache state | EMIC behavior (5C.1) |
|-------------|----------------------|
| Valid cache, sync disabled | Continue with cached catalog/revocation; report OFFLINE/STALE |
| Expired revocation cache | Status `TRUST_DATA_STALE` / `expired`; diagnostics only — **no auto module stop in 5C.1** |
| Invalid/untrusted cache | Status UNAVAILABLE; no metadata promotion |

Runtime quarantine based on stale revocation is **Step 5C.5+**.

---

## 8. Audit

Required audit actions (implemented):

- `marketplace.sync_started` / `sync_succeeded` / `sync_failed`
- `marketplace.root_rotated`
- `marketplace.metadata_rejected`
- `marketplace.revocation_updated` (future hook when revocation generation changes)

No package credentials or device secrets in audit payloads.

---

## 9. Customer / admin communication

Template points:

1. Summary: root key incident / planned rotation
2. Impact: metadata sync only; local Internal Store unaffected for installed packages
3. Action: update EMIC or import pinned root; run manual sync
4. Timeline: rotation version, expiry, support contact
5. Verification: expected root key IDs and version (no private material)

---

## 10. Post-incident

- Root cause analysis (HSM access, CI signing pipeline, insider)
- Key ceremony review
- Fleet report: installations stuck on old root vs successful rotation
- Update threat model and staging acceptance tests
