import { CircularGauge } from "./CircularGauge";

export interface PerformanceMetrics {
  headlinePct: number | null;
  headlineLabel: string;
  rows: Array<{ label: string; value: string; tone?: "positive" | "negative" | "neutral" }>;
}

function performanceLabel(pct: number): string {
  if (pct >= 94) return "Utmärkt";
  if (pct >= 85) return "Bra";
  if (pct >= 70) return "Acceptabelt";
  return "Låg";
}

export function buildPerformanceMetrics(input: {
  headlineRatio: number | null;
  todayDeviation: number | null;
  weekAvg: number | null;
  monthAvg: number | null;
  quarterAvg: number | null;
  ytdAvg: number | null;
}): PerformanceMetrics {
  const headline = input.headlineRatio;
  const fmtRatio = (v: number | null) => {
    if (v == null) return "—";
    return `${(v * 100).toFixed(1).replace(".", ",")} %`;
  };
  const fmtDeviation = (v: number | null) => {
    if (v == null) return "—";
    const sign = v > 0 ? "+" : "";
    return `${sign}${v.toFixed(1).replace(".", ",")} %`;
  };

  return {
    headlinePct: headline != null ? headline * 100 : null,
    headlineLabel: headline != null ? performanceLabel(headline * 100) : "—",
    rows: [
      {
        label: "Idag",
        value: fmtDeviation(input.todayDeviation),
        tone:
          input.todayDeviation == null
            ? "neutral"
            : input.todayDeviation >= 0
              ? "positive"
              : "negative",
      },
      { label: "7 dagar", value: fmtRatio(input.weekAvg), tone: "positive" },
      { label: "30 dagar", value: fmtRatio(input.monthAvg), tone: "positive" },
      { label: "90 dagar", value: fmtRatio(input.quarterAvg), tone: "positive" },
      { label: "YTD", value: fmtRatio(input.ytdAvg), tone: "positive" },
    ],
  };
}

export function PerformancePanel({ metrics }: { metrics: PerformanceMetrics }) {
  return (
    <section className="idash-panel idash-performance-panel">
      <h2 className="idash-panel-title">PRESTANDA</h2>
      <p className="idash-panel-subtitle">VÄDERNORMALISERAD</p>
      <div className="idash-performance-body">
        <CircularGauge
          value={metrics.headlinePct ?? 0}
          label={metrics.headlinePct != null ? `${metrics.headlinePct.toFixed(1).replace(".", ",")}%` : "—"}
          sublabel={metrics.headlineLabel}
        />
        <ul className="idash-performance-list">
          {metrics.rows.map((row) => (
            <li key={row.label}>
              <span>{row.label}</span>
              <strong className={`idash-performance-value idash-performance-${row.tone ?? "neutral"}`}>
                {row.value}
              </strong>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
