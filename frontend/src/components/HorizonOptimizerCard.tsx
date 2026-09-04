import type { HorizonOptimizerPlan } from "../lib/api";

interface HorizonOptimizerCardProps {
  plan: HorizonOptimizerPlan;
}

function formatWindow(start: string | null, end: string | null, timezone: string): string {
  if (!start || !end) {
    return "Inget fönster";
  }
  const opts: Intl.DateTimeFormatOptions = {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  };
  return `${new Date(start).toLocaleString("sv-SE", opts)}–${new Date(end).toLocaleString("sv-SE", opts)}`;
}

export function HorizonOptimizerCard({ plan }: HorizonOptimizerCardProps) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Horizon Optimizer</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            48h koordinerad plan för EV, spa och batteri
          </p>
        </div>
        {plan.monitor_only ? (
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
            Endast övervakning
          </span>
        ) : null}
      </div>

      {plan.available ? (
        <div className="space-y-4">
          <div>
            <p className="text-base font-medium text-slate-900 dark:text-slate-100">
              {plan.headline_sv ?? "Horizon-plan"}
            </p>
            {plan.summary_sv ? (
              <p className="text-sm text-slate-600 dark:text-slate-300">{plan.summary_sv}</p>
            ) : null}
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              {plan.horizon_blocks} block · {plan.horizon_hours}h horisont
            </p>
          </div>

          {plan.loads.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-slate-500 dark:text-slate-400">
                    <th className="pb-2 pr-3">Last</th>
                    <th className="pb-2 pr-3">Fönster</th>
                    <th className="pb-2 pr-3">Besparing</th>
                  </tr>
                </thead>
                <tbody>
                  {plan.loads.map((load) => (
                    <tr key={load.load_id} className="border-t border-slate-100 dark:border-slate-800">
                      <td className="py-2 pr-3 font-medium text-slate-900 dark:text-slate-100">
                        {load.name}
                        <span className="ml-2 text-xs uppercase text-slate-500">{load.load_type}</span>
                      </td>
                      <td className="py-2 pr-3 text-slate-600 dark:text-slate-300">
                        {formatWindow(load.window_start, load.window_end, plan.timezone)}
                      </td>
                      <td className="py-2 pr-3 text-slate-600 dark:text-slate-300">
                        {load.savings_sek != null ? `${load.savings_sek.toFixed(2)} kr` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}

          {plan.battery?.available && plan.battery.headline_sv ? (
            <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/60">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Batteri
              </p>
              <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                {plan.battery.headline_sv}
              </p>
              {plan.battery.reason_sv ? (
                <p className="text-sm text-slate-600 dark:text-slate-300">{plan.battery.reason_sv}</p>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : (
        <p className="text-sm text-slate-600 dark:text-slate-300">
          {plan.unavailable_reason_sv ?? "Horizon-plan är inte tillgänglig just nu."}
        </p>
      )}
    </section>
  );
}
