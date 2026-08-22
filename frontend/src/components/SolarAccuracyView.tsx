"use client";

import { useEffect, useState } from "react";
import { SolarAccuracy, fetchSolarAccuracy } from "@/lib/api";

interface SolarAccuracyViewProps {
  siteSlug: string;
}

const TOOLTIPS: Record<string, string> = {
  mape: "Genomsnittlig procentuell avvikelse mellan prognostiserad och faktisk solproduktion. Lägre är bättre.",
  mae: "Genomsnittlig skillnad mellan prognostiserad och faktisk solproduktion, uttryckt i kWh per dag. Lägre är bättre.",
  bias: "Visar om modellen systematiskt prognostiserar för högt (positivt) eller för lågt (negativt).",
  correction: "EMIC justerar grundprognosen baserat på historisk produktion för just denna anläggning.",
  confidence: "Hur säker modellen är baserat på historik, felnivå och datatäckning.",
  samples: "Antal dagar med faktisk produktion som modellen har lärt sig från.",
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

  return (
    <section className="peaks-section">
      <h3 className="section-title">Modellkvalitet</h3>

      {learning ? (
        <div className="solar-learning-state">
          <p>
            <strong>Prognosmodellen lär sig</strong>
          </p>
          <p className="muted">
            Historiska observationer: {accuracy.historical_samples}
          </p>
          <p className="muted">
            Modellens träffsäkerhet kan ännu inte beräknas. EMIC jämför automatiskt
            prognostiserad solproduktion med faktisk produktion och kalibrerar modellen över tid.
          </p>
          <p className="muted">
            {accuracy.historical_samples} av rekommenderade {target} observationsdagar insamlade.
          </p>
        </div>
      ) : null}

      <dl className="metrics">
        <div>
          <dt>Status</dt>
          <dd>{modelStateLabel(accuracy.model_state)}</dd>
        </div>
        <div>
          <Tooltip label="Historiska dagar" text={TOOLTIPS.samples} />
          <dd>{accuracy.historical_samples}</dd>
        </div>

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
