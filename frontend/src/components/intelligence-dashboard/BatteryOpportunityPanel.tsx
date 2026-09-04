"use client";

import { useEffect, useState } from "react";

import { BatteryOpportunityCard } from "@/components/BatteryOpportunityCard";
import type { BatteryOpportunity } from "@/lib/api";
import { fetchBatteryOpportunity } from "@/lib/api";

export function BatteryOpportunityPanel({ slug }: { slug: string }) {
  const [advice, setAdvice] = useState<BatteryOpportunity | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = () =>
      fetchBatteryOpportunity(slug)
        .then((payload) => {
          if (active) {
            setAdvice(payload);
            setError(null);
          }
        })
        .catch((err: Error) => {
          if (active) {
            setAdvice(null);
            setError(err.message);
          }
        });
    load();
    const interval = setInterval(load, 120_000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [slug]);

  if (error && !advice) {
    return (
      <section data-testid="battery-opportunity-panel">
        <BatteryOpportunityCard
          advice={{
            slug,
            timezone: "Europe/Stockholm",
            available: false,
            monitor_only: true,
            unavailable_reason_sv: "Batteriråd otillgängligt.",
            action: null,
            action_label_sv: null,
            headline_sv: null,
            reason_sv: null,
            confidence: null,
            battery_soc_pct: null,
            recommended_reserve_soc_pct: null,
            expected_value_sek_kwh: null,
            next_peak_at: null,
            next_peak_import_sek_kwh: null,
            optimization_mode: null,
            strategy_state: null,
          }}
        />
      </section>
    );
  }

  if (!advice) {
    return (
      <section data-testid="battery-opportunity-panel" className="rounded-xl border border-slate-200 p-4">
        <p className="text-sm text-slate-500">Hämtar batteriråd…</p>
      </section>
    );
  }

  return (
    <section data-testid="battery-opportunity-panel">
      <BatteryOpportunityCard advice={advice} />
    </section>
  );
}
