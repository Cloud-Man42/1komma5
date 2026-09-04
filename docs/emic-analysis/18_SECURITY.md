# EMIC Security Analysis

**IMPORTANT:** No secrets reproduced in this document. All credential values masked as `[REDACTED]`.

---

## 1. Authentication Summary

| Surface | Auth | Risk level |
|---------|------|------------|
| Main `/api/*` (dashboard, config, admin) | **None** | **HIGH** — assumes trusted LAN |
| Widget `/api/v1/widget/*` | Bearer token, scope `widget.read`, 60/min rate limit | LOW |
| Display `/api/v1/display/*` | Bearer or cookie, scope `display.read`, ≥30/min | LOW |
| Apple devices admin | **None** | **HIGH** |
| SEMP endpoints `/semp/*` | **None** | MEDIUM — device protocol exposure |
| `/health` | None | LOW (expected) |

**Documented assumption:** LAN-trusted deployment (`docs/EMIC_HEALTH_REPORT.md` — "Säkerhetshårdning utan ny autentisering").

---

## 2. Authorization

- No role-based access control (RBAC)
- No user accounts in EMIC
- Site-level data not isolated by auth — any network client can access all sites
- Device tokens scoped to `widget.read` / `display.read` only
- Vehicle commands, spa control, energy control apply — **unauthenticated**

---

## 3. Secrets Management

| Secret | Storage | Exposure risk |
|--------|---------|---------------|
| `EMIC_SECRET_KEY` / Fernet key | File or Docker volume `emic_secrets` | LOW if volume secured |
| Heartbeat credentials | DB encrypted (Fernet) | LOW — API returns config without passwords |
| Mercedes tokens | DB encrypted | LOW |
| Charge Amps credentials | Env vars + per-charger DB | Config endpoint returns status only |
| Arctic Spa API key | Env + site config | Server-side only |
| Pi display token | `/etc/emic/kiosk.env` | LOW — local file, proxy injection |
| Open-Meteo API key | Env optional | LOW |
| Heartbeat API key (legacy env) | Env | Dev only typical |

**Verification needed:** Confirm `HeartbeatConfigResponse` and similar schemas exclude password fields — defined in `backend/app/schemas.py`.

---

## 4. Frontend Credential Exposure Audit

| Credential | Visible in frontend? | Evidence |
|------------|---------------------|----------|
| Heartbeat password | ❌ Should not be | Config page uses GET/PUT without displaying password |
| Mercedes tokens | ❌ | Admin shows diagnostics, not tokens |
| Charge Amps API key | ❌ | `chargeamps-config` returns connection status |
| Stripe | N/A — not integrated | — |
| Modbus | N/A — removed | — |
| Display token | ❌ on Pi | Caddy injects server-side |
| Widget token | ⚠️ Stored on Apple device keychain | Expected for widget |

**API keys in `NEXT_PUBLIC_*` env vars:** Only `NEXT_PUBLIC_API_BASE_URL` and optional `NEXT_PUBLIC_PERFORMANCE_DEBUG` — no secrets in public env.

---

## 5. Transport Security

| Path | TLS |
|------|-----|
| Production EMIC | Caddy TLS (`tls internal` or ACME) |
| Pi → EMIC | HTTPS to `emic.inacloud.se` |
| Pi local | HTTP localhost:8080 (acceptable — loopback) |
| Dev frontend | HTTP localhost:3000 |

**ProxyHeadersMiddleware:** Trusts `X-Forwarded-*` from Caddy (`trusted_hosts="*"`).

---

## 6. CORS

```python
allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"]
allow_credentials=True
allow_methods=["*"]
allow_headers=["*"]
```

**Production:** Same-origin via Caddy — CORS not needed for prod browser access. Dev-only restriction.

---

## 7. CSRF

- No CSRF tokens on API
- Cookie-based display auth (`emic_display_token`) — **CSRF risk if cookie used from browser on untrusted origin**
- Mitigated: display cookie likely same-site only on Pi proxy setup

---

## 8. XSS

- React/Next.js default escaping
- User-generated content minimal — site names, device labels
- `dangerouslySetInnerHTML` usage: UNKNOWN — should audit frontend grep

---

## 9. SQL Injection

- SQLAlchemy parameterized queries throughout
- Raw SQL in `repositories.py` CAGG path uses parameterized `text(sql)`
- **Risk: LOW** with standard ORM usage

---

## 10. Command Injection

- No shell invocation from API handlers identified
- Collector uses Python async HTTP clients only
- Deploy scripts (`scripts/deploy-linux.ps1`) — operator-run, not web-exposed

---

## 11. Rate Limiting

| Endpoint | Limit |
|----------|-------|
| Widget API | 60/min per device |
| Display API | ≥30/min per device |
| Main API | **None** |
| ChargeFinder test lookup | Circuit breaker only |

---

## 12. Security Observations (Priority)

| # | Observation | Severity |
|---|-------------|----------|
| 1 | Open admin API on LAN | HIGH |
| 2 | Apple device registration without auth | HIGH |
| 3 | Vehicle/spa/charging commands unauthenticated | HIGH |
| 4 | SEMP endpoints open | MEDIUM |
| 5 | No API rate limiting on main routes | MEDIUM |
| 6 | `trusted_hosts="*"` on ProxyHeaders | LOW — needed for Caddy |
| 7 | Fernet key auto-generated on first boot | LOW — ensure volume backup |
| 8 | ChargeFinder web scraping | LOW — ToS/legal consideration |

---

## 13. Recommendations

1. Add optional API key or OAuth for admin routes (even on LAN)
2. Protect apple-devices endpoints
3. Rate limit destructive commands (vehicle start/stop, spa control)
4. Audit frontend for `dangerouslySetInnerHTML`
5. Security headers via Caddy (HSTS, CSP)
6. Rotate display/widget tokens periodically
7. Document threat model for LAN vs internet-exposed deployments

---

## 14. UNKNOWN

- Whether EMIC is exposed beyond LAN in any deployment
- CSP configuration on Caddy
- Penetration test history
