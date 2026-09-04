"use client";

import { useEffect, useState } from "react";

import { HorizonOptimizerCard } from "@/components/HorizonOptimizerCard";
import type { HorizonOptimizerPlan } from "@/lib/api";
import { fetchHorizonOptimizer } from "@/lib/api";

export function HorizonOptimizerPanel({ slug }: { slug: string }) {
  const [plan, setPlan] = useState<HorizonOptimizerPlan | null>(null);

  useEffect(() => {
    let active = true;
    const load = () =>
      fetchHorizonOptimizer(slug)
        .then((payload) => {
          if (active) setPlan(payload);
        })
        .catch(() => {
          if (active) setPlan(null);
        });
    load();
    const interval = setInterval(load, 120_000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [slug]);

  if (!plan) {
    return (
      <section data-testid="horizon-optimizer-panel" className="rounded-xl border border-slate-200 p-4">
        <p className="text-sm text-slate-500">Hämtar horizon-plan…</p>
      </section>
    );
  }

  return (
    <section data-testid="horizon-optimizer-panel">
      <HorizonOptimizerCard plan={plan} />
    </section>
  );
}
