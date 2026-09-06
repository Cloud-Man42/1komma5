import type { BatteryOpportunity } from "../lib/api";
import {
  batteryActionLabel,
  formatConfidence,
  formatOre,
  formatPct,
  formatSekKwh,
  formatTime,
} from "./intelligence-dashboard/advisorFormatters";

interface BatteryOpportunityCardProps {
  advice: BatteryOpportunity;
}

export function BatteryOpportunityCard({ advice }: BatteryOpportunityCardProps) {
  const headline =
    advice.headline_sv ??
    advice.action_label_sv ??
    batteryActionLabel(advice.action, "Batteriråd");

  return (
    <section className="idash-advisor-card" data-testid="battery-opportunity-card">
      <header className="idash-advisor-header">
        <div>
          <h2>BATTERIRÅDGIVARE</h2>
          <p className="idash-advisor-subtitle">Read-only råd baserat på pris, SOC och EOV</p>
        </div>
        {advice.monitor_only ? (
          <span className="idash-advisor-badge">Endast övervakning</span>
        ) : null}
      </header>

      {advice.available ? (
        <>
          <div className="idash-advisor-action">
            <span className="idash-advisor-dot" aria-hidden="true" />
            <strong>{headline}</strong>
          </div>

          <div className="idash-advisor-metrics">
            <div>
              <span>Batteri SOC</span>
              <strong>{formatPct(advice.battery_soc_pct)}</strong>
            </div>
            <div>
              <span>Rekomm. reserv</span>
              <strong>{formatPct(advice.recommended_reserve_soc_pct)}</strong>
            </div>
            <div>
              <span>Förväntat värde</span>
              <strong>{formatSekKwh(advice.expected_value_sek_kwh)}</strong>
            </div>
            <div>
              <span>Konfidens</span>
              <strong>{formatConfidence(advice.confidence)}</strong>
            </div>
          </div>

          {advice.next_peak_at || advice.next_peak_import_sek_kwh != null ? (
            <div className="idash-advisor-peak">
              <div>
                <span>Nästa pristopp</span>
                <strong>{formatTime(advice.next_peak_at, advice.timezone)}</strong>
              </div>
              <div>
                <span>Förväntat köp då</span>
                <strong>{formatOre(advice.next_peak_import_sek_kwh)}</strong>
              </div>
            </div>
          ) : null}

          {advice.reason_sv ? <p className="idash-advisor-reason">{advice.reason_sv}</p> : null}
        </>
      ) : (
        <p className="idash-advisor-empty">
          {advice.unavailable_reason_sv ?? "Batteriråd är inte tillgängligt just nu."}
        </p>
      )}
    </section>
  );
}
