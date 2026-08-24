# Heartbeat EV-profil – tvåvägssynk

Feature-flaggad synk mellan EMIC och Heartbeat EV-profil (`PATCH /v1/systems/{system_id}/devices/evs/{id}`).

## Aktivering

1. **Global skrivning** – `/config` → *Synka laddinställningar till Heartbeat* (`heartbeat_write_enabled`).
2. **Per laddbox** – Konfiguration → anläggning → laddbox → *Heartbeat-synk (EV-profil)* (`heartbeat_sync_enabled`).
   - Kräver `heartbeat_ev_id` och site `external_system_id`.

Standard: **av** för båda flaggorna.

## Vad synkas

| EMIC | Heartbeat |
|------|-----------|
| `charging_mode` | `chargeSettings.chargingMode` |
| `target_soc_pct` | `chargeSettings.targetSoc` |
| `departure_time` | `chargeSettings.primaryScheduleDepartureTime` |

**Synkas inte:** ström/Halo-styrning, `PAUSED` (EMIC-lokalt), EMS override.

## Triggers

- UI-styrning och override → push efter DB-commit
- Mercedes `set-target-soc` (lyckat) → push mål-SoC till länkad laddbox
- Smart charging cycle → pull vid start; push högst en gång/cykel vid behov
- Collector fallback → pull var 60:e s om engine inte kört nyligen

## Konflikter

Om Heartbeat `updatedAt` är nyare än senaste EMIC-push + 60 s cooldown vinner Heartbeat (app-ändring). Annars pushar EMIC vid lokala ändringar.

## Produktionsverifiering

1. Aktivera `heartbeat_write_enabled` i config.
2. Sätt `heartbeat_sync_enabled` på Halo-laddbox med `heartbeat_ev_id`.
3. Ändra laddläge i EMIC → verifiera i 1Komma5-appen.
4. Ändra target SoC i Heartbeat-appen → verifiera att EMIC laddbox-vyn uppdateras inom ~60 s.
5. Kör Mercedes `--execute set-target-soc` → verifiera Heartbeat EV-profil.

## Felsökning

- Sync-status och senaste fel visas i laddbox-vyn när synk är aktiv.
- `heartbeat_sync_error` i API-svar och DB (max 512 tecken).
- Halo-styrning påverkas inte av sync-fel.
