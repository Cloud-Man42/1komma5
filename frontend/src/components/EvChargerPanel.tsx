"use client";



import Image from "next/image";
import { FormEvent, useCallback, useEffect, useState } from "react";

import {

  EvBridgeStatus,

  EvCharger,

  EvChargingSavings,

  EvSolarChargingPlan,

  OVERRIDE_HOURS,

  controlEvCharger,

  fetchEvBridgeStatus,

  fetchEvChargerSavings,

  fetchEvSolarChargingPlan,

  fetchEvChargers,

  formatWatts,

  setEvChargerOverride,

} from "@/lib/api";

import { EvChargingAnalytics } from "@/components/EvChargingAnalytics";
import { DeadlineInput } from "@/components/DeadlineInput";
import VirtualEvseDiagnosticsPanel from "@/components/VirtualEvseDiagnosticsPanel";
import EnergyReasoningPanel from "@/components/EnergyReasoningPanel";
import { HaloPowerIndicator } from "@/components/HaloPowerIndicator";

import { combineDeadlineLocal, formatDeadline } from "@/lib/deadlineInput";
import { formatSekAmount } from "@/lib/prices";

import { useDashboardRefreshSeconds } from "@/lib/useDashboardRefresh";



function isChargeAmpsHalo(charger: EvCharger): boolean {
  const label = `${charger.manufacturer} ${charger.model} ${charger.name}`.toLowerCase();
  return label.includes("halo") || label.includes("chargeamp") || label.includes("charge amps");
}

function ChargeAmpsHaloVisual({ charger }: { charger: EvCharger }) {
  if (!isChargeAmpsHalo(charger)) return null;

  return (
    <div className="charger-header-visual">
      <Image
        src="/images/charge-amps-halo.png"
        alt="Charge Amps Halo väggladdare"
        width={220}
        height={293}
        className="charger-halo-image"
        priority
      />
      <HaloPowerIndicator charger={charger} />
    </div>
  );
}

const MODE_LABELS: Record<string, string> = {

  SMART_CHARGE: "Smart laddning",

  PRICE_CHARGE: "Billigast pris",

  SOLAR_CHARGE: "Solel",

  QUICK_CHARGE: "Snabbladdning",

  PAUSED: "Pausad",

};

function isPriceOnlyMode(mode: string | null | undefined): boolean {
  return mode === "PRICE_CHARGE";
}

function HeartbeatSyncStatus({ charger }: { charger: EvCharger }) {
  if (!charger.heartbeat_sync_enabled) {
    return null;
  }

  const pushed = charger.heartbeat_last_pushed_at
    ? new Date(charger.heartbeat_last_pushed_at).toLocaleString("sv-SE")
    : null;
  const pulled = charger.heartbeat_last_pulled_at
    ? new Date(charger.heartbeat_last_pulled_at).toLocaleString("sv-SE")
    : null;

  return (
    <div className="charger-sync-status">
      <p className="muted">
        Heartbeat-synk aktiv
        {pushed ? <> · Senast skickat {pushed}</> : null}
        {pulled ? <> · Senast hämtat {pulled}</> : null}
      </p>
      {charger.heartbeat_sync_error ? (
        <p className="form-error">Synkfel: {charger.heartbeat_sync_error}</p>
      ) : null}
    </div>
  );
}

function ChargerControlForm({
  charger,
  onSubmit,
}: {
  charger: EvCharger;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const [selectedMode, setSelectedMode] = useState(charger.charging_mode ?? "SMART_CHARGE");
  const priceOnly = isPriceOnlyMode(selectedMode);

  useEffect(() => {
    setSelectedMode(charger.charging_mode ?? "SMART_CHARGE");
  }, [charger.charging_mode, charger.id]);

  return (
    <form onSubmit={onSubmit} className="form-grid">
      <label className="form-field">
        <span>Laddningsläge</span>
        <select
          name="charging_mode"
          value={selectedMode}
          onChange={(event) => setSelectedMode(event.target.value)}
        >
          {Object.keys(MODE_LABELS).map((mode) => (
            <option key={mode} value={mode}>
              {MODE_LABELS[mode] ?? mode}
            </option>
          ))}
        </select>
      </label>

      <label className="form-field">
        <span>Mål-SoC (%)</span>
        <input
          type="number"
          name="target_soc_pct"
          min={0}
          max={100}
          defaultValue={charger.target_soc_pct ?? 80}
        />
      </label>

      {!priceOnly && (
        <>
          <label className="form-field">
            <span>Avfärd (HH:MM)</span>
            <input
              type="text"
              name="departure_time"
              pattern="\d{2}:\d{2}"
              defaultValue={charger.departure_time ?? "07:00"}
            />
          </label>

          <label className="form-field form-field-wide">
            <span>Klar senast</span>
            <DeadlineInput value={charger.deadline_at} idPrefix={`deadline-${charger.id}`} />
          </label>
        </>
      )}

      <div className="form-field form-field-wide">
        <p className="muted">
          {priceOnly
            ? "Billigast pris laddar när elpriset är som lägst. Avfärd och klar senast används inte."
            : selectedMode === "SMART_CHARGE" && charger.departure_time == null
              ? "Smart laddning laddar vid normalt eller billigt elpris även utan avresa. Ange avresa eller klar senast för att styra när bilen ska vara klar."
              : "Smart laddning använder elprisprognos från Heartbeat och prioriterar solel. När avresa eller klar senast närmar sig laddas det från nätet oavsett pris. Bilen stoppar själv vid mål-SoC."}
        </p>

        <button type="submit" className="btn-primary">
          Uppdatera laddinställningar
        </button>
      </div>
    </form>
  );
}

function formatOverrideUntil(until: string): string {
  const date = new Date(until);

  if (Number.isNaN(date.getTime())) return until;

  return date.toLocaleString("sv-SE", {

    day: "numeric",

    month: "short",

    hour: "2-digit",

    minute: "2-digit",

  });

}



function ChargingSavingsStats({

  siteSlug,

  chargerId,

  refreshSeconds,

}: {

  siteSlug: string;

  chargerId: number;

  refreshSeconds: number;

}) {

  const [savings, setSavings] = useState<EvChargingSavings | null>(null);



  const load = useCallback(async () => {

    const data = await fetchEvChargerSavings(siteSlug, chargerId, 30);

    setSavings(data);

  }, [siteSlug, chargerId]);



  useEffect(() => {

    load().catch(() => setSavings(null));

    const interval = setInterval(() => {

      load().catch(() => undefined);

    }, refreshSeconds * 1000);

    return () => clearInterval(interval);

  }, [load, refreshSeconds]);



  if (!savings) {

    return <p className="muted">Laddar smart laddningsstatistik…</p>;

  }



  if (!savings.has_data) {

    return (

      <div className="charger-savings">

        <p className="charger-override-title">Smart laddning – besparingar (30 dagar)</p>

        <p className="muted">

          Ingen ladddata ännu. Statistik visas när smart laddning har kört ett tag med bilen inkopplad.

        </p>

      </div>

    );

  }



  const saved = formatSekAmount(savings.savings_sek);

  const actual = formatSekAmount(savings.actual_cost_sek);

  const baseline = formatSekAmount(savings.baseline_cost_sek);



  return (

    <div className="charger-savings">

      <p className="charger-override-title">Smart laddning – besparingar (30 dagar)</p>

      <p className="muted">

        Jämför faktisk kostnad med att ladda samma energi till genomsnittspriset under perioden.

        Override och snabbladdning räknas inte med.

      </p>

      <dl className="price-summary">

        <div>

          <dt>Sparat</dt>

          <dd>

            {saved.label} ({savings.savings_pct.toFixed(1)} %)

          </dd>

        </div>

        <div>

          <dt>Faktisk kostnad</dt>

          <dd>{actual.label}</dd>

        </div>

        <div>

          <dt>Utan optimering</dt>

          <dd>{baseline.label}</dd>

        </div>

        <div>

          <dt>Smart laddat</dt>

          <dd>{savings.energy_kwh.toFixed(1)} kWh</dd>

        </div>

      </dl>

    </div>

  );

}



function formatSolarWindow(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString("sv-SE", {
    hour: "2-digit",
    minute: "2-digit",
  });
}



function BridgeStatusPanel({

  siteSlug,

  chargerId,

  refreshSeconds,

}: {

  siteSlug: string;

  chargerId: number;

  refreshSeconds: number;

}) {

  const [status, setStatus] = useState<EvBridgeStatus | null>(null);

  const [solarPlan, setSolarPlan] = useState<EvSolarChargingPlan | null>(null);

  const [error, setError] = useState<string | null>(null);



  const load = useCallback(async () => {

    const [bridge, plan] = await Promise.all([
      fetchEvBridgeStatus(siteSlug, chargerId),
      fetchEvSolarChargingPlan(siteSlug, chargerId),
    ]);

    setStatus(bridge);

    setSolarPlan(plan);

    setError(null);

  }, [siteSlug, chargerId]);



  useEffect(() => {

    load().catch((e) => {

      setStatus(null);

      setError(e instanceof Error ? e.message : "Kunde inte hämta bridge-status");

    });

    const interval = setInterval(() => {

      load().catch(() => undefined);

    }, refreshSeconds * 1000);

    return () => clearInterval(interval);

  }, [load, refreshSeconds]);



  if (error) {

    return <p className="form-error">{error}</p>;

  }



  if (!status) {

    return <p className="muted">Laddar motorstatus…</p>;

  }



  return (

    <div className="charger-savings">

      <p className="charger-override-title">Smart laddningsmotor</p>

      {status.display_status_sv && (
        <p className="charger-status-headline">
          <strong>{status.display_status_sv}</strong>
        </p>
      )}

      <dl className="price-summary">

        <div>

          <dt>Policy</dt>

          <dd>{status.active_policy}</dd>

        </div>

        <div>

          <dt>State</dt>

          <dd>{status.smart_charging_state ?? "—"}</dd>

        </div>

        <div>

          <dt>Beslut</dt>

          <dd>{status.decision_reason ?? "—"}</dd>

        </div>

        <div>

          <dt>EMIC önskar</dt>

          <dd>{status.requested_current_a != null ? `${status.requested_current_a.toFixed(1)} A` : "—"}</dd>

        </div>

        <div>

          <dt>Halo konfigurerad</dt>

          <dd>{status.configured_current_a != null ? `${status.configured_current_a.toFixed(1)} A` : "—"}</dd>

        </div>

        <div>

          <dt>Faktisk ström</dt>

          <dd>{status.actual_charging_current_a != null ? `${status.actual_charging_current_a.toFixed(1)} A` : "—"}</dd>

        </div>

        <div>

          <dt>Senast skickad</dt>

          <dd>{status.applied_current_a != null ? `${status.applied_current_a.toFixed(1)} A` : "—"}</dd>

        </div>

        <div>

          <dt>Halo</dt>

          <dd>{status.halo_connected == null ? "—" : status.halo_connected ? "Ansluten" : "Frånkopplad"}</dd>

        </div>

        <div>

          <dt>Fordon</dt>

          <dd>

            {status.vehicle_connected == null ? "—" : status.vehicle_connected ? "Inkoppad" : "Ej inkoppad"}

          </dd>

        </div>

        <div>

          <dt>Data</dt>

          <dd>{status.stale ? "Inaktuell" : "Aktuell"}</dd>

        </div>

        {(status.phase_current_l1_a != null ||
          status.phase_current_l2_a != null ||
          status.phase_current_l3_a != null) && (
          <div>
            <dt>Per-fas (A)</dt>
            <dd>
              L1 {status.phase_current_l1_a?.toFixed(1) ?? "—"} · L2{" "}
              {status.phase_current_l2_a?.toFixed(1) ?? "—"} · L3{" "}
              {status.phase_current_l3_a?.toFixed(1) ?? "—"}
            </dd>
          </div>
        )}

      </dl>

      {status.last_error_code && (

        <p className="form-error">Senaste fel: {status.last_error_code}</p>

      )}

      {status.discovery_hints.length > 0 && (

        <p className="muted">{status.discovery_hints.join(" · ")}</p>

      )}

      {solarPlan && status.charging_mode !== "PRICE_CHARGE" && (
        <div className="charger-solar-plan">
          <p className="charger-override-title">Solprognos (Smart laddning)</p>
          {solarPlan.explanation_sv && (
            <p className="muted">{solarPlan.explanation_sv}</p>
          )}
          {solarPlan.available ? (
            <dl className="price-summary">
              <div>
                <dt>Prioritet</dt>
                <dd>{solarPlan.solar_first ? "Solel först" : "Nät vid billiga timmar"}</dd>
              </div>
              <div>
                <dt>Förväntat solfönster</dt>
                <dd>
                  {formatSolarWindow(solarPlan.expected_solar_window_start) ?? "—"}
                  {solarPlan.expected_solar_window_end
                    ? ` – ${formatSolarWindow(solarPlan.expected_solar_window_end)}`
                    : ""}
                </dd>
              </div>
              {solarPlan.cheapest_grid_window && (
                <div>
                  <dt>Billigaste nät-fönster</dt>
                  <dd>{solarPlan.cheapest_grid_window}</dd>
                </div>
              )}
              <div>
                <dt>Prognoskvalitet</dt>
                <dd>
                  {solarPlan.quality ?? "—"}
                  {solarPlan.confidence != null
                    ? ` (${Math.round(solarPlan.confidence * 100)} %)`
                    : ""}
                </dd>
              </div>
            </dl>
          ) : (
            <p className="muted">
              {solarPlan.explanation_sv ??
                "Ange avresa eller klar senast för solbaserad planering."}
            </p>
          )}
        </div>
      )}

    </div>

  );

}



export function EvChargerPanel({ siteSlug }: { siteSlug: string }) {

  const [chargers, setChargers] = useState<EvCharger[]>([]);

  const [error, setError] = useState<string | null>(null);

  const [message, setMessage] = useState<string | null>(null);

  const [pendingOverrideId, setPendingOverrideId] = useState<number | null>(null);

  const refreshSeconds = useDashboardRefreshSeconds();



  const load = async () => {

    const data = await fetchEvChargers(siteSlug);

    setChargers(data);

  };



  useEffect(() => {

    load().catch((e) => setError(e instanceof Error ? e.message : "Kunde inte ladda laddboxar"));

    const interval = setInterval(() => {

      load().catch(() => undefined);

    }, refreshSeconds * 1000);

    return () => clearInterval(interval);

  }, [siteSlug, refreshSeconds]);



  const handleControl = async (

    charger: EvCharger,

    updates: {

      charging_mode?: string;

      target_soc_pct?: number;

      departure_time?: string;

      deadline_at?: string | null;

      clear_deadline_at?: boolean;

    },

  ) => {

    setError(null);

    setMessage(null);

    try {

      const updated = await controlEvCharger(siteSlug, charger.id, updates);

      setChargers((current) => current.map((c) => (c.id === updated.id ? updated : c)));

      setMessage(`Laddbox "${charger.name}" uppdaterad.`);

    } catch (e) {

      setError(e instanceof Error ? e.message : "Styrning misslyckades");

    }

  };



  const handleOverride = async (charger: EvCharger, hours: number) => {

    setError(null);

    setMessage(null);

    setPendingOverrideId(charger.id);

    try {

      const updated = await setEvChargerOverride(siteSlug, charger.id, { hours });

      setChargers((current) => current.map((c) => (c.id === updated.id ? updated : c)));

      setMessage(`Snabbladdning aktiv i ${hours} timmar på "${charger.name}".`);

    } catch (e) {

      setError(e instanceof Error ? e.message : "Override misslyckades");

    } finally {

      setPendingOverrideId(null);

    }

  };



  const handleClearOverride = async (charger: EvCharger) => {

    setError(null);

    setMessage(null);

    setPendingOverrideId(charger.id);

    try {

      const updated = await setEvChargerOverride(siteSlug, charger.id, { clear: true });

      setChargers((current) => current.map((c) => (c.id === updated.id ? updated : c)));

      setMessage(`Override avslutad för "${charger.name}".`);

    } catch (e) {

      setError(e instanceof Error ? e.message : "Kunde inte avsluta override");

    } finally {

      setPendingOverrideId(null);

    }

  };



  const handleForm = (charger: EvCharger) => async (event: FormEvent<HTMLFormElement>) => {

    event.preventDefault();

    const form = new FormData(event.currentTarget);

    const deadlineDate = String(form.get("deadline_date") || "");
    const deadlineTime = String(form.get("deadline_time") || "");
    const deadlineIso = combineDeadlineLocal(deadlineDate, deadlineTime);
    const chargingMode = String(form.get("charging_mode") || "") || undefined;
    const priceOnly = isPriceOnlyMode(chargingMode);

    await handleControl(charger, {
      charging_mode: chargingMode,
      target_soc_pct: form.get("target_soc_pct") ? Number(form.get("target_soc_pct")) : undefined,
      ...(priceOnly
        ? {}
        : {
            departure_time: String(form.get("departure_time") || "") || undefined,
            deadline_at: deadlineIso,
            clear_deadline_at: !deadlineIso,
          }),
    });

  };



  if (chargers.length === 0) {

    return (

      <div className="card config-card">

        <h3 className="config-section-title">Laddboxar</h3>

        <p className="muted">Inga laddboxar konfigurerade. Lägg till under Konfiguration.</p>

      </div>

    );

  }



  return (

    <div className="card config-card">

      <h3 className="config-section-title">Laddboxar</h3>

      {chargers.map((charger) => (

        <div key={charger.id} className="charger-block">
          <div className="charger-header">
            <div className="charger-header-text">
              <h4>{charger.name}</h4>
              <p className="muted">
                {charger.manufacturer} {charger.model} · Charge Amps
              </p>
            </div>
            <ChargeAmpsHaloVisual charger={charger} />
          </div>

          <HeartbeatSyncStatus charger={charger} />

          {charger.power_w != null && (

            <p>

              Aktuell effekt: <strong>{formatWatts(charger.power_w)}</strong>

            </p>

          )}

          {charger.charging_mode && (

            <p>

              Läge: <strong>{MODE_LABELS[charger.charging_mode] ?? charger.charging_mode}</strong>

            </p>

          )}

          {formatDeadline(charger.deadline_at) && !isPriceOnlyMode(charger.charging_mode) && (

            <p>

              Klar senast: <strong>{formatDeadline(charger.deadline_at)}</strong>

            </p>

          )}

          {charger.last_applied_current_a != null && (

            <p>

              Senast applicerad ström: <strong>{charger.last_applied_current_a.toFixed(1)} A</strong>

            </p>

          )}

          {charger.last_charging_reason && (

            <p>

              Senaste beslut: <strong>{charger.last_charging_reason}</strong>

            </p>

          )}

          {charger.last_charger_error_code && (

            <p className="form-error">Laddarfel: {charger.last_charger_error_code}</p>

          )}



          {charger.bridge_enabled && (

            <BridgeStatusPanel

              siteSlug={siteSlug}

              chargerId={charger.id}

              refreshSeconds={refreshSeconds}

            />

          )}

          {(charger.bridge_enabled || charger.virtual_evse_enabled) && (
            <VirtualEvseDiagnosticsPanel
              siteSlug={siteSlug}
              chargerId={charger.id}
              refreshSeconds={refreshSeconds}
              virtualEvseEnabled={Boolean(charger.virtual_evse_enabled)}
            />
          )}

          {charger.bridge_enabled && (
            <EnergyReasoningPanel
              siteSlug={siteSlug}
              chargerId={charger.id}
              refreshSeconds={refreshSeconds}
              onSettingsSaved={() => {
                load().catch(() => undefined);
              }}
            />
          )}



          {charger.bridge_enabled && (
            <>
            <ChargingSavingsStats

              siteSlug={siteSlug}

              chargerId={charger.id}

              refreshSeconds={refreshSeconds}

            />

            <EvChargingAnalytics siteSlug={siteSlug} chargerId={charger.id} />
            </>
          )}



          {charger.bridge_enabled && (
            <ChargerControlForm charger={charger} onSubmit={handleForm(charger)} />
          )}



          {charger.bridge_enabled && (

            <div className="charger-override">

              <p className="charger-override-title">Snabbladdning (override)</p>

              {charger.override_active && charger.override_until ? (

                <p className="form-success">

                  Override aktiv till {formatOverrideUntil(charger.override_until)}.

                </p>

              ) : (

                <p className="muted">Kringgå automatisk styrning och ladda med max ström direkt.</p>

              )}

              <div className="charger-override-actions">

                {OVERRIDE_HOURS.map((hours) => (

                  <button

                    key={hours}

                    type="button"

                    className="btn-secondary"

                    disabled={pendingOverrideId === charger.id}

                    onClick={() => handleOverride(charger, hours)}

                  >

                    {hours} h

                  </button>

                ))}

                {charger.override_active && (

                  <button

                    type="button"

                    className="btn-secondary"

                    disabled={pendingOverrideId === charger.id}

                    onClick={() => handleClearOverride(charger)}

                  >

                    Avsluta override

                  </button>

                )}

              </div>

            </div>

          )}



          {!charger.bridge_enabled && (

            <p className="muted">Aktivera bridge under Konfiguration för att styra laddboxen.</p>

          )}

        </div>

      ))}

      {message && <p className="form-success">{message}</p>}

      {error && <p className="form-error">{error}</p>}

    </div>

  );

}

