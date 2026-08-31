# Ekonomisk beräkning i EMIC

Denna beskrivning gäller `EnergyReadingRepository.list_financial_stats` i
`packages/energy-core/src/energy_core/db/repositories.py`.

## Per tidsintervall

Mellan två mätpunkter (max 300 sekunder) beräknas:

| Mängd | Formel |
| --- | --- |
| Solel direkt till huset | `min(sol, max(0, förbrukning − urladdning − import))` |
| Batteri till huset | `min(urladdning, max(0, förbrukning − solel_direkt))` |
| Import / export | mätta `grid_import_w` / `grid_export_w` |

Ekonomi värderas med timpris från `market_prices.all_in_price_eur_kwh` (all-in)
eller reservpris från `sites.fallback_purchase_price_sek_kwh`.

**Såld el** värderas per intervall mot **feed-in-tariff** (`market_prices.feed_in_price_eur_kwh`)
eller spot beroende på `sites.sell_pricing_mode`, med site-konfiguration från
`energy_core/export_revenue/`:

Export räknas endast från `sites.sell_contract_start_date` (t.ex. Pulse-avtal).
Fysisk export före det datumet lagras som `uncontracted_exported_kwh` utan intäkt.

```
effectiveSellPrice = spotPrice + adjustment − deduction
energySaleRevenue  = exportKWh × effectiveSellPrice
gridBenefitRevenue = exportKWh × gridBenefitRate (konfigurerbar per site)
export_revenue_sek = energySaleRevenue + gridBenefitRevenue
```

Om spot saknas används `sites.export_compensation_sek_kwh` som fallback (märks ESTIMATED).

Historisk skattereduktion (≤2025, SE): `min(export, import, 30 000 kWh) × 0,60 kr/kWh`
beräknas per år och allokeras proportionellt till delperioder. **Från 2026-01-01 = 0.**

## Resultat

- **Besparing sol** = solel direkt till huset × inköpspris
- **Besparing batteri** = batteriurladdning till huset × inköpspris
- **Spotersättning** = export × effectiveSellPrice (tidsmatchat)
- **Nätnytta** = export × gridBenefitRate (separat post)
- **Intäkt såld el** = spotersättning + nätnytta (exkl. skattereduktion)
- **Skattereduktion** = historisk post, separat från såld el
- **Kostnad köpt el** = import × inköpspris
- **Nettokostnad** = kostnad köpt el − intäkt såld el (ingen skattereduktion)
- **Total ekonomisk nytta** = besparing sol + besparing batteri + intäkt såld el
- **Total ekonomiskt värde** = nytta + historisk skattereduktion

## Frontend (Ekonomi-vyn)

Visningslager i `frontend/src/components/economy-dashboard/economyDashboardHelpers.ts`:

- **Nettokostnad** = `grid_import_cost_sek − export_revenue_sek`
- **Total besparing** = sol + batteri + såld el (kategorier utan data döljs)
- **Avkastning YTD** = YTD ekonomisk nytta / investering × 100 (null om investering saknas)
- **Kostnadsfördelning** (nät/skatt/påslag) = uppskattade andelar av importkostnad (56/23/15/6 %)
- **Återbetalningstid** = kvarvarande investering / annualiserad nytta (senaste 12 mån)

## Tidigare fel: solel via batteri

Tidigare användes `min(sol, förbrukning)` för solel. Det ignorerade att sol samtidigt
kunde ladda batteriet. Exempel:

- Sol 2000 W, förbrukning 3000 W, batteriladdning 500 W, import 1500 W
- Felaktigt: 2000 W solel + 1500 W import = 3500 W mot 3000 W förbrukning
- Vid senare urladdning krediterades samma energi igen som batteribesparing

### Korrigerad attribuering

Solel som går till batteriet räknas inte som direkt solel. När batteriet urladdas
till huset räknas det som batteribesparing. Identiteten

`solar_self + battery_self + imported == consumption`

ska då hålla per dag/period.

## Nätladdat batteri

Laddning från nätet ökar `grid_import_cost_sek`. Urladdning till huset ökar
`battery_savings_sek`. Vid samma pris ger det netto noll – batterikortet visar
bruttovärdet av urladdningen, inte enbart arbitragevinst.
