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
