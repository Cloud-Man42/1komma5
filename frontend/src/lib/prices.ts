/** Convert Heartbeat price (kr/kWh) to öre/kWh for display. */
export function toOrePerKwh(pricePerKwh: number): number {
  return pricePerKwh * 100;
}

export function formatOrePerKwh(pricePerKwh: number): string {
  return `${toOrePerKwh(pricePerKwh).toFixed(1)} öre/kWh`;
}

/** Format SEK amount as "X kr Y öre" (Swedish). */
export function formatSekAmount(amountSek: number): { kronor: number; ore: number; label: string } {
  const totalOre = Math.max(0, Math.round(amountSek * 100));
  const kronor = Math.floor(totalOre / 100);
  const ore = totalOre % 100;
  const label = ore === 0 ? `${kronor} kr` : `${kronor} kr ${ore.toString().padStart(2, "0")} öre`;
  return { kronor, ore, label };
}

function formatSekDecimalCore(amountSek: number): string {
  return Math.abs(amountSek).toLocaleString("sv-SE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** Format SEK amount as "400,52 kr" (Swedish decimal, absolute value). */
export function formatSekDecimal(amountSek: number): string {
  return `${formatSekDecimalCore(amountSek)} kr`;
}

/** Format signed SEK amount as "+268,05 kr", "−125,40 kr" or "0,00 kr". */
export function formatSekSigned(amountSek: number): string {
  if (Math.abs(amountSek) < 0.005) {
    return "0,00 kr";
  }
  const sign = amountSek > 0 ? "+" : "−";
  return `${sign}${formatSekDecimalCore(amountSek)} kr`;
}
