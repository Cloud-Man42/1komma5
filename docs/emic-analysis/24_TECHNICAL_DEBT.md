# TOP 30 Technical Debt

Ranked by risk × impact. Severity: CRITICAL / HIGH / MEDIUM / LOW.

| # | Severity | Risk | Effort | Item | Recommended fix |
|---|----------|------|--------|------|-----------------|
| 1 | CRITICAL | Data breach on LAN exposure | M | Open admin API without auth | Optional API key / OAuth for writes |
| 2 | HIGH | Wrong economics at 15-min granularity | M | Dual price stores (hourly + 15-min) | Unify on price_periods |
| 3 | HIGH | Performance degradation | M | `list_financial_stats` Python integration | Pre-aggregate in collector |
| 4 | HIGH | Solar dashboard unusable under load | M | Solar forecast heavy GET | Snapshot in collector |
| 5 | HIGH | DB growth unbounded | M | No Timescale retention policy | Add retention + compression |
| 6 | HIGH | Cache ineffective multi-worker | M | Process-local L1 only | Redis shared cache |
| 7 | HIGH | Fragmented energy model | L | 5 parallel state representations | Unified EnergyStateBuilder |
| 8 | MEDIUM | 2× dashboard API calls | S | Overview 15s + layout 30s poll | Single refresh coordinator |
| 9 | MEDIUM | SSE DB load | M | 1s DB poll per SSE client | Redis pub/sub push |
| 10 | MEDIUM | Collector cycle stretch | M | 15 sequential steps per poll | Prioritized sub-loops |
| 11 | MEDIUM | Stale economy view | S | Economy hook no auto-refresh | Add setInterval |
| 12 | MEDIUM | Apple devices open registration | S | No auth on `/apple-devices` | Admin auth |
| 13 | MEDIUM | display ↔ dashboard coupling | M | Cross-import in display_service | Shared builder service |
| 14 | MEDIUM | `repositories.py` god class | L | Multiple domains in one file | Split repositories |
| 15 | MEDIUM | `api.ts` monolith | M | 78 fetch functions one file | Split by domain |
| 16 | MEDIUM | Legacy `market_prices` table | M | Parallel to price_periods | Deprecate after migration |
| 17 | MEDIUM | Modbus catalog references | S | Dead integration in charger catalog | Mark deprecated clearly |
| 18 | MEDIUM | No collector cycle metrics | S | Duration not measured | Add timing logs/metrics |
| 19 | MEDIUM | Forecast learning no feedback | M | Records but doesn't tune | Close the loop |
| 20 | MEDIUM | Pi no offline LKG | M | Client state lost on reload | localStorage persist |
| 21 | LOW | Energy dashboard 60s hardcoded | S | Ignores site config | Use shared refresh hook |
| 22 | LOW | `schemas.py` size | M | Entire API in one module | Split by router |
| 23 | LOW | Health report stale (migration 044 vs 057) | S | Docs out of date | Update health report |
| 24 | LOW | No CI ruff/lint job | S | ruff configured but not in CI | Add lint workflow |
| 25 | LOW | Apple tests not in CI | S | Swift tests orphaned | Add macOS CI or skip doc |
| 26 | LOW | SEMP endpoints unauthenticated | S | Open device protocol | Auth or network isolate |
| 27 | LOW | Economy cost breakdown estimates | S | 56/23/15/6 hardcoded | Label as estimate or compute |
| 28 | LOW | `trusted_hosts="*"` ProxyHeaders | S | Required for Caddy | Document as accepted |
| 29 | LOW | nobil tables possibly unused | S | ChargeFinder superseded | Audit and remove |
| 30 | LOW | No coverage enforcement in CI | M | Coverage unknown | Add threshold |

**Effort:** S = small (days), M = medium (1–2 weeks), L = large (sprint+)
