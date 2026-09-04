# Security — Design & P0 Finding

**Status:** DESIGN ONLY for hardening; P0 finding documented  
**Reference:** [`docs/emic-analysis/18_SECURITY.md`](../18_SECURITY.md)

---

## Deployment assumption

EMIC is deployed on a **trusted LAN** (home network). Most `/api/*` routes have **no authentication**. Documented in `docs/EMIC_HEALTH_REPORT.md`.

Widget (`/api/v1/widget/*`) and display (`/api/v1/display/*`) routes use device bearer tokens with scoped permissions.

---

## P0 finding: Apple device admin routes unauthenticated

**Route prefix:** `/api/apple-devices`  
**File:** [`backend/app/api/apple_devices.py`](../../../backend/app/api/apple_devices.py)

| Endpoint | Risk |
|----------|------|
| `POST /apple-devices` | Creates device + returns **plaintext token** |
| `GET /apple-devices` | Lists all enrolled devices |
| `PATCH /apple-devices/{id}` | Rename device |
| `POST /apple-devices/{id}/revoke` | Revoke token |
| `GET /apple-devices/metrics` | Widget metrics |

**No auth dependency** on any handler — any client on the network can enroll devices or revoke tokens.

**Impact:** HIGH on any network beyond single-user LAN (guest WiFi, exposed port forward, compromised client).

**Phase 1 action:** Document only. **Phase 2:** Require admin secret or session auth on these routes.

---

## Other unauthenticated surfaces (unchanged)

| Surface | Notes |
|---------|-------|
| Dashboard, config, vehicles, spa control | Full read/write |
| SEMP `/semp/*` | Device protocol |
| Energy control apply | Strategy sync endpoints |

---

## Proposed auth plan (Phase 2 — design)

1. **`EMIC_ADMIN_TOKEN`** env var — Bearer required on `/apple-devices`, site config mutations, vehicle commands.
2. **Optional OAuth** for multi-user (out of scope).
3. **Rate limiting** on token creation.
4. **Audit log** for admin actions.

Caddy can add basic auth layer for `/api/apple-devices` as interim mitigation without code change.

---

## Secrets

No secrets in Phase 1 docs. Credential storage unchanged (Fernet in DB, env for provider keys). See parent security doc for inventory.

---

## Tests

No new auth tests in Phase 1 (behaviour unchanged). Security tests planned with auth enforcement in Phase 2.
