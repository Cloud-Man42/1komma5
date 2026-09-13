/** Formatting helpers for multi-site live flow diagram. */

export function formatFlowPowerFromKw(kw: number | null | undefined): string {
  if (kw == null || Number.isNaN(kw)) return "—";
  const w = kw * 1000;
  return formatFlowPowerFromW(w);
}

export function formatFlowPowerFromW(w: number | null | undefined): string {
  if (w == null || Number.isNaN(w)) return "—";
  const abs = Math.abs(w);
  if (abs >= 1000) return `${(w / 1000).toFixed(1)} kW`;
  return `${Math.round(w)} W`;
}

export function formatFlowPowerCompact(w: number | null | undefined): string {
  if (w == null || Number.isNaN(w)) return "0 W";
  const abs = Math.abs(w);
  if (abs < 25) return "0 W";
  if (abs >= 1000) return `${(w / 1000).toFixed(1)} kW`;
  return `${Math.round(w)} W`;
}
