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

Ekonomi värderas med timpris från `market_prices.all_in_price_sek_kwh` eller
reservpris från `sites.fallback_purchase_price_sek_kwh`. Såld el värderas med
`sites.export_compensation_sek_kwh`.

## Resultat

- **Besparing sol** = solel direkt till huset × inköpspris
- **Besparing batteri** = batteriurladdning till huset × inköpspris
- **Intäkt såld el** = export × ersättning
- **Kostnad köpt el** = import × inköpspris
- **Ekonomiskt resultat** = sol + batteri + intäkt − kostnad köpt el

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
