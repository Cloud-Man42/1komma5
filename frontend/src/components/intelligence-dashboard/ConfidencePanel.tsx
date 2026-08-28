import { CircularGauge } from "./CircularGauge";
import {
  confidenceHeadlineSv,
  confidenceTierSv,
  modelStateSv,
} from "./confidenceLabels";

export function ConfidencePanel({
  score,
  label,
  modelScore,
  modelState,
  historicalSamples,
}: {
  score: number | null;
  label: string;
  modelScore?: number | null;
  modelState?: string;
  historicalSamples?: number;
}) {
  const value = score ?? 0;

  return (
    <section className="idash-panel idash-confidence-panel">
      <h2 className="idash-panel-title">CONFIDENCE</h2>
      <div className="idash-confidence-body">
        <CircularGauge
          value={value}
          label={`${Math.round(value)}%`}
          color="#38bdf8"
          size={120}
        />
        <div>
          <strong>{confidenceHeadlineSv(score)}</strong>
          <p className="idash-muted">Prognosens tillförlitlighet · {label}</p>
          {modelScore != null ? (
            <p className="idash-muted idash-confidence-model">
              Modellkalibrering · {Math.round(modelScore)}%
              {modelState ? ` (${modelStateSv(modelState) ?? modelState})` : ""}
              {historicalSamples != null ? ` · ${historicalSamples} dagar` : ""}
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}

export { confidenceTierSv };
