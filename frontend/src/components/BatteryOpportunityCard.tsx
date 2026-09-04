import type { BatteryOpportunity } from "../lib/api";

interface BatteryOpportunityCardProps {
  advice: BatteryOpportunity;
}

function formatPct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  return `${Math.round(value)}%`;
}

function formatSek(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  return `${value.toFixed(2)} kr/kWh`;
}

export function BatteryOpportunityCard({ advice }: BatteryOpportunityCardProps) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            Batterirådgivare
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Read-only råd baserat på pris, SOC och EOV
          </p>
        </div>
        {advice.monitor_only ? (
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
            Endast övervakning
          </span>
        ) : null}
      </div>

      {advice.available ? (
        <div className="space-y-3">
          <p className="text-base font-medium text-slate-900 dark:text-slate-100">
            {advice.headline_sv ?? advice.action_label_sv ?? "Batteriråd"}
          </p>
          {advice.reason_sv ? (
            <p className="text-sm text-slate-600 dark:text-slate-300">{advice.reason_sv}</p>
          ) : null}
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-slate-500 dark:text-slate-400">Batteri SOC</dt>
              <dd className="font-medium text-slate-900 dark:text-slate-100">
                {formatPct(advice.battery_soc_pct)}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">Reservmål</dt>
              <dd className="font-medium text-slate-900 dark:text-slate-100">
                {formatPct(advice.recommended_reserve_soc_pct)}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">Förväntat värde</dt>
              <dd className="font-medium text-slate-900 dark:text-slate-100">
                {formatSek(advice.expected_value_sek_kwh)}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">Säkerhet</dt>
              <dd className="font-medium text-slate-900 dark:text-slate-100">
                {advice.confidence != null ? `${Math.round(advice.confidence * 100)}%` : "—"}
              </dd>
            </div>
          </dl>
        </div>
      ) : (
        <p className="text-sm text-slate-600 dark:text-slate-300">
          {advice.unavailable_reason_sv ?? "Batteriråd är inte tillgängligt just nu."}
        </p>
      )}
    </section>
  );
}
