export function pctDelta(today: number | null | undefined, yesterday: number | null | undefined): string | null {
  if (today == null || yesterday == null || yesterday === 0) return null;
  const delta = ((today - yesterday) / Math.abs(yesterday)) * 100;
  const sign = delta >= 0 ? "+" : "";
  return `${sign}${delta.toFixed(0)}%`;
}

export function yesterdayComparisonLabel(
  today: number | null | undefined,
  yesterday: number | null | undefined,
): string | null {
  if (yesterday == null) return null;
  const delta = pctDelta(today, yesterday);
  return delta ? `Igår: ${delta}` : "Igår: —";
}
