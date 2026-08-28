import type { SpaEnergyPeriod, SpaPlan, SpaStatus } from "@/lib/api";
import { buildInsights } from "./spaDashboardHelpers";

export function SpaInsightsPanel({
  status,
  today,
  month,
  plan,
  onShowAnalysis,
}: {
  status: SpaStatus;
  today: SpaEnergyPeriod | null;
  month: SpaEnergyPeriod | null;
  plan: SpaPlan | null;
  onShowAnalysis?: () => void;
}) {
  const insights = buildInsights(today, month, plan, status);

  return (
    <section className="sdash-panel sdash-insights-panel">
      <h2 className="sdash-panel-title">INSIKTER</h2>
      <ul className="sdash-insights-list">
        {insights.map((item, index) => (
          <li key={index} className={`sdash-insight sdash-insight-${item.tone}`}>
            {item.text}
          </li>
        ))}
      </ul>
      <button type="button" className="sdash-link-btn" onClick={onShowAnalysis}>
        Visa detaljerad analys
      </button>
    </section>
  );
}
