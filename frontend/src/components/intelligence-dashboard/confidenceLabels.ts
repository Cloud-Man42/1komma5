import type { SolarForecast } from "@/lib/api";

export function forecastConfidencePct(
  forecast: SolarForecast | null | undefined,
  fallbackPct?: number | null,
): number | null {
  if (forecast != null) {
    return Math.round(forecast.confidence * 100);
  }
  return fallbackPct ?? null;
}

export function confidenceTierSv(pct: number | null): string {
  if (pct == null) return "—";
  if (pct >= 75) return "Hög";
  if (pct >= 45) return "Medel";
  return "Låg";
}

export function confidenceHeadlineSv(pct: number | null): string {
  if (pct == null) return "Okänd tilltro";
  if (pct >= 80) return "Hög tilltro";
  if (pct >= 50) return "Medel tilltro";
  return "Låg tilltro";
}

export function modelStateSv(state: string | undefined): string | null {
  switch (state) {
    case "NO_DATA":
      return "Ingen historik";
    case "LEARNING":
      return "Inlärning";
    case "PRELIMINARY":
      return "Preliminär modell";
    case "CALIBRATED":
      return "Kalibrerad";
    case "MATURE":
      return "Mogen modell";
    default:
      return state ?? null;
  }
}

export function shouldShowModelCalibration(
  forecast: SolarForecast | null | undefined,
): boolean {
  if (!forecast?.confidence_score && forecast?.confidence_score !== 0) return false;
  if (forecast.model_state === "CALIBRATED" || forecast.model_state === "MATURE") {
    return false;
  }
  return true;
}
