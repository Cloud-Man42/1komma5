# EMIC UI/UX Analysis

---

## 1. Dashboard Inventory

| View | Route | Primary purpose |
|------|-------|-----------------|
| Intelligence Overview | `/sites/[slug]` | At-a-glance live + today + solar/price panels |
| Energy | `/sites/[slug]/energy` | Flow diagram, history, peaks, quality |
| Solar | `/sites/[slug]/solar` | Forecast, weather, performance, accuracy |
| Solar Intelligence | `/sites/[slug]/solar/intelligence` | ML model admin |
| EV / Laddbox | `/sites/[slug]/ev` | Chargers, smart charging, sessions |
| Economy | `/sites/[slug]/costs` | Costs, savings, budget, prices |
| Vehicle | `/sites/[slug]/vehicle` | Mercedes live + sessions |
| SPA | `/sites/[slug]/spa` | Spa status, plan, economics |
| Diagnostics | `/sites/[slug]/diagnostics` | Audit, energy control, virtual EVSE |
| Performance | `/sites/[slug]/system/performance` | Server metrics |
| Config | `/config` | Integrations, sites, devices |
| Pi Kiosk | `/display/[slug]` | Touch wall display |

**Nav definition:** `frontend/src/components/intelligence-dashboard/navItems.ts`

---

## 2. Three-Second Comprehension Test

Can user answer in 3 seconds?

| Question | Overview | Energy | Pi |
|----------|----------|--------|-----|
| How much producing? | ✅ Live gauge + today kWh | ✅ Flow diagram | ✅ Solar card |
| How much using? | ✅ Consumption gauge | ✅ Flow diagram | ✅ Energy card |
| Battery charging? | ⚠️ In gauges, not primary | ✅ Battery node | ✅ Battery section |
| Buying electricity? | ⚠️ Grid gauge small | ✅ Grid flow | ✅ Grid section |
| Selling electricity? | ⚠️ Same | ✅ Export arrow | ✅ Grid section |
| Price good? | ⚠️ Sidebar card (300s refresh) | ❌ Not on energy page | ⚠️ Economy section |
| System optimal? | ⚠️ Strategy card (120s) | ❌ | ❌ Insights partial |

**Verdict:** Overview and Pi are **close** for core energy questions. Price and optimization status are **secondary/hidden**.

---

## 3. Information Overload Issues

| Issue | Location | Detail |
|-------|----------|--------|
| Duplicate live metrics | Overview + Energy + Sidebar | Same kW values in multiple cards |
| Too many sub-sections | Energy (7 hash sections) | Deep navigation via hash |
| Diagnostics on main nav | Same level as Economy | Should be admin/advanced |
| Solar + Solar Intelligence | Two solar entries | Confusing for non-technical users |
| Confidence percentages | Fixed regression (was 5800%) | Fixed per health report; verify UI |
| Technical labels | EV reasoning, virtual EVSE | Jargon on diagnostics |
| Economy cost breakdown | Estimated 56/23/15/6 split | May mislead — not labeled as estimate prominently |

---

## 4. Duplicated Information

| Data | Appears in |
|------|------------|
| Live solar kW | Overview gauges, Energy flow, Solar overview, Pi solar |
| Today solar kWh | Overview, Energy history, Solar, Economy, Pi |
| Grid import/export | Overview, Energy, Pi grid |
| Battery SOC | Overview, Energy, Pi battery |
| EV status | Overview widget, EV dashboard, Pi charger |
| Electricity price | Sidebar, Economy, Energy strategy card, Pi economy |
| Smart charging status | EV dashboard, Config readiness, Pi charger |

**Mitigation exists:** `SiteDataProvider` reduces duplicate fetches but not duplicate display.

---

## 5. Missing Information

| Missing | User need | Data available? |
|---------|-----------|-----------------|
| Single "am I winning?" score | Quick status | Could derive from net cost + strategy |
| Battery reserve / backup status | Outage preparedness | SOC only |
| Next cheap charging window | EV planning | Price engine today — not on EV overview prominently |
| Forecast confidence on main view | Trust | Accuracy API exists — buried in solar |
| Integration health summary | "Is something broken?" | Readiness endpoints exist — scattered |
| Comparison to yesterday | Context | History API — requires navigation |
| CO₂ / environmental | Motivation | Could estimate from solar kWh |

---

## 6. Desktop vs Raspberry Pi

### Desktop (`/sites/[slug]/*`)
- Full nav sidebar with all sections
- Hash sub-navigation within dashboards
- Recharts heavy charts (dynamic import)
- Mouse/keyboard oriented
- Multiple simultaneous polls

### Pi Kiosk (`/display/[slug]/*`)
- Touch-first; no sidebar
- Home cards → detail sections (`piSections.ts`)
- Home button 56px top-left
- 4s polling (aggressive)
- Simpler layout, fewer numbers
- Phase 2 gaps: forecast curve, battery today, price min/max show `--`

**Pi strengths:** Focused, large touch targets, single API call  
**Pi weaknesses:** Offline LKG not implemented; missing Phase 2 data fields

---

## 7. Widget Hierarchy Recommendations

**Tier 1 (always visible):** Production kW, Consumption kW, Grid direction, Battery SOC+state, Price tier  
**Tier 2 (one tap):** Today kWh totals, EV status, Net cost today  
**Tier 3 (sub-pages):** History charts, sessions, diagnostics, ML metrics

Current EMIC puts Tier 2 and Tier 3 at similar nav levels.

---

## 8. Label / Language Issues

- Mixed Swedish/English in code labels (API enums vs Swedish UI)
- "Intelligence Overview" vs Swedish "Översikt" — OK
- Smart charging modes mapped to Swedish in helpers
- Economy terms: "Nettokostnad", "Skattereduktion" — correct for SE market

---

## 9. Widgets of Questionable Value

| Widget | Issue |
|--------|-------|
| Forecast learning card (overview) | Mount-only, no refresh — stale |
| Multiple sparklines with same data | Redundant on overview |
| Energy scene calibrator | `/calibrate` — dev tool, not user feature |
| Heartbeat virtual bridge panel | Admin-level on config page — OK there |

---

## 10. UX Quick Wins

1. Add "Energy status strip" to overview: Produce | Use | Grid | Battery | Price in one row
2. Move Diagnostics out of primary nav
3. Enable economy auto-refresh
4. Show snapshot age / data freshness badge globally
5. Pi: implement Phase 2 display fields from existing backend data
6. Consolidate price display (sidebar + strategy → one source)
