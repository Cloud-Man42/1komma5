"use client";

import { useEffect, useState } from "react";

import { HorizonOptimizerCard } from "@/components/HorizonOptimizerCard";
import type { HorizonOptimizerPlan } from "@/lib/api";
import { fetchHorizonOptimizer } from "@/lib/api";

export function HorizonOptimizerPanel({ slug }: { slug: string }) {
  const [plan, setPlan] = useState<HorizonOptimizerPlan | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = () =>
      fetchHorizonOptimizer(slug)
        .then((payload) => {
          if (active) {
            setPlan(payload);
            setError(null);
          }
        })
        .catch((err: Error) => {
          if (active) {
            setPlan(null);
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

  if (error && !plan) {
    return (
      <section data-testid="horizon-optimizer-panel">
        <HorizonOptimizerCard
          plan={{
            slug,
            timezone: "Europe/Stockholm",
            available: false,
            monitor_only: true,
            unavailable_reason_sv: "Horizon-plan otillgänglig.",
            horizon_hours: 48,
            horizon_blocks: 0,
            generated_at: null,
            total_planned_savings_sek: null,
            headline_sv: null,
            summary_sv: null,
            loads: [],
            battery: null,
          }}
        />
      </section>
    );
  }

  if (!plan) {
    return (
      <section className="idash-horizon-card" data-testid="horizon-optimizer-panel">
        <header className="idash-horizon-header">
          <div>
            <h2>HORIZON OPTIMIZER</h2>
            <p className="idash-horizon-meta">48h horisont</p>
          </div>
        </header>
        <p className="idash-horizon-empty">Hämtar horizon-plan…</p>
      </section>
    );
  }

  return (
    <section data-testid="horizon-optimizer-panel">
      <HorizonOptimizerCard plan={plan} />
    </section>
  );
}
