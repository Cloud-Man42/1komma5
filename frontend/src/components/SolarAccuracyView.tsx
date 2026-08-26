"use client";

import { useEffect, useState } from "react";
import { SolarAccuracy, fetchSolarAccuracy } from "@/lib/api";

interface SolarAccuracyViewProps {
  siteSlug: string;
}

const TOOLTIPS: Record<string, string> = {
  mape: "Genomsnittlig procentuell avvikelse mellan prognostiserad och faktisk solproduktion. Lägre är bättre.",
  mae: "Genomsnittlig skillnad mellan prognostiserad och faktisk solproduktion, uttryckt i kWh per dag. Lägre är bättre.",
  bias: "Visar om modellen systematiskt prognostiserar för högt (positivt) eller för lågt (negativt). Positiv bias = överskattar.",
  wape: "Weighted Absolute Percentage Error — viktad procentuell avvikelse. Lägre är bättre.",
  rmse: "Root Mean Square Error i kWh — straffar stora avvikelser hårdare än MAE.",
  correction: "EMIC justerar grundprognosen baserat på historisk produktion för just denna anläggning.",
  confidence: "Hur säker modellen är baserat på historik, felnivå och datatäckning.",
  samples: "Antal hela dagar där EMIC jämfört prognos med faktisk produktion och räknat dem som träningsdata.",
  production: "Antal dagar med mätbar solproduktion i EMIC:s historik (senaste 60 dagarna).",
};

function Tooltip({ label, text }: { label: string; text: string }) {
  return (
    <dt title={text}>
      {label} <span className="muted" aria-hidden="true">ⓘ</span>
    </dt>
  );
}

function modelStateLabel(state: string): string {
  switch (state) {
    case "NO_DATA":
      return "Ingen historik";
    case "LEARNING":
      return "Lär sig";
    case "PRELIMINARY":
      return "Preliminär";
    case "CALIBRATED":
      return "Kalibrerad";
    case "MATURE":
      return "Mogen";
    default:
      return state;
  }
}

export function SolarAccuracyView({ siteSlug }: SolarAccuracyViewProps) {
  const [accuracy, setAccuracy] = useState<SolarAccuracy | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetchSolarAccuracy(siteSlug)
      .then((data) => {
        if (active) {
          setAccuracy(data);
          setError(null);
        }
      })
      .catch((e) => {
        if (active) {
          setAccuracy(null);
          setError(e instanceof Error ? e.message : "Kunde inte ladda modellkvalitet");
        }
      });
    return () => {
      active = false;
    };
  }, [siteSlug]);

  if (error) return null;
  if (!accuracy) return <p className="muted">Laddar modellkvalitet…</p>;

  const learning =
    accuracy.metrics_insufficient ||
    accuracy.model_state === "NO_DATA" ||
    accuracy.model_state === "LEARNING" ||
    accuracy.historical_samples === 0;

  const target = accuracy.min_samples_for_calibrated || 30;
  const productionDays = accuracy.production_days_observed ?? 0;
  const evaluatedDays = accuracy.historical_samples;

  return (
    <section className="peaks-section">
      <h3 className="section-title">Modellkvalitet</h3>

      {learning ? (
        <div className="solar-learning-state">
          <p>
            <strong>Prognosmodellen lär sig</strong>
          </p>
          <p className="muted">
            Utvärderade dagar: {evaluatedDays}
            {productionDays > evaluatedDays ? ` (${productionDays} dagar med mätdata i historiken)` : ""}
          </p>
          <p className="muted">
            Modellens träffsäkerhet kan ännu inte beräknas. EMIC jämför automatiskt
            prognostiserad solproduktion med faktisk produktion och kalibrerar modellen över tid.
          </p>
          <p className="muted">
            {accuracy.insufficient_reason === "no_training_samples"
              ? "Inga utvärderade träningsdagar ännu."
              : accuracy.insufficient_reason === "model_learning"
                ? "Modellen samlar fortfarande in data."
                : "Otillräckligt underlag för meningsfulla metrics."}
          </p>
          <p className="muted">
            {evaluatedDays} av rekommenderade {target} utvärderingsdagar insamlade.
          </p>
        </div>
      ) : null}

      <dl className="metrics">
        <div>
          <dt>Status</dt>
          <dd>{modelStateLabel(accuracy.model_state)}</dd>
        </div>
        <div>
          <Tooltip label="Utvärderade dagar" text={TOOLTIPS.samples} />
          <dd>{evaluatedDays}</dd>
        </div>
        {productionDays > 0 ? (
          <div>
            <Tooltip label="Dagar med mätdata" text={TOOLTIPS.production} />
            <dd>{productionDays}</dd>
          </div>
        ) : null}

        {!learning && accuracy.mape_7d_pct != null ? (
          <div>
            <Tooltip label="MAPE 7 dagar" text={TOOLTIPS.mape} />
            <dd>
              {accuracy.mape_7d_pct.toFixed(1)} %
              {accuracy.mape_7d_valid_days > 0 ? (
                <span className="muted"> · baserat på {accuracy.mape_7d_valid_days} giltiga dagar</span>
              ) : null}
            </dd>
          </div>
        ) : null}

        {!learning && accuracy.mape_30d_pct != null ? (
          <div>
            <Tooltip label="MAPE 30 dagar" text={TOOLTIPS.mape} />
            <dd>
              {accuracy.mape_30d_pct.toFixed(1)} %
              {accuracy.mape_30d_valid_days > 0 ? (
                <span className="muted"> · baserat på {accuracy.mape_30d_valid_days} giltiga dagar</span>
              ) : null}
            </dd>
          </div>
        ) : null}

        {!learning && accuracy.mae_kwh_30d != null ? (
          <div>
            <Tooltip label="MAE 30 dagar" text={TOOLTIPS.mae} />
            <dd>{accuracy.mae_kwh_30d.toFixed(2)} kWh/dag</dd>
          </div>
        ) : null}

        {!learning && accuracy.bias_pct_30d != null ? (
          <div>
            <Tooltip label="Bias" text={TOOLTIPS.bias} />
            <dd>{accuracy.bias_pct_30d.toFixed(1)} %</dd>
          </div>
        ) : null}

        {!learning && accuracy.wape_30d_pct != null ? (
          <div>
            <Tooltip label="WAPE 30 dagar" text={TOOLTIPS.wape} />
            <dd>{accuracy.wape_30d_pct.toFixed(1)} %</dd>
          </div>
        ) : null}

        {!learning && accuracy.rmse_kwh_30d != null ? (
          <div>
            <Tooltip label="RMSE 30 dagar" text={TOOLTIPS.rmse} />
            <dd>{accuracy.rmse_kwh_30d.toFixed(2)} kWh</dd>
          </div>
        ) : null}

        {!learning ? (
          <>
            <div>
              <Tooltip label="Correction factor" text={TOOLTIPS.correction} />
              <dd>{accuracy.correction_factor.toFixed(3)}</dd>
            </div>
            {accuracy.confidence_score != null ? (
              <div>
                <Tooltip label="Confidence" text={TOOLTIPS.confidence} />
                <dd>
                  {Math.round(accuracy.confidence_score)} %{" "}
                  {accuracy.confidence_label ?? ""}
                </dd>
              </div>
            ) : null}
            {accuracy.raw_mae_30d != null && accuracy.corrected_mae_30d != null ? (
              <div>
                <dt>Modellförbättring</dt>
                <dd>
                  Vädermodell MAE: {accuracy.raw_mae_30d.toFixed(2)} kWh/dag · EMIC MAE:{" "}
                  {accuracy.corrected_mae_30d.toFixed(2)} kWh/dag
                  {accuracy.improvement_pct_30d != null
                    ? ` · ${accuracy.improvement_pct_30d.toFixed(1)} %`
                    : ""}
                </dd>
              </div>
            ) : null}
          </>
        ) : null}

        <div>
          <dt>Modell</dt>
          <dd>{accuracy.model_version}</dd>
        </div>
      </dl>
    </section>
  );
}
