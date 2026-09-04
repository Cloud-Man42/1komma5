/** Match backend EUR_TO_SEK_RATE default. */
export const DEFAULT_EUR_TO_SEK_RATE = 11;

/** Values above this in legacy Heartbeat DB *_eur_kwh columns were stored as SEK/kWh. */
export const LEGACY_SEK_IN_EUR_COLUMN_THRESHOLD = 0.25;

/** Convert SEK/kWh to öre/kWh. */
export function toOrePerKwh(sekKwh: number): number {
  return sekKwh * 100;
}

/** Convert öre/kWh display value from SEK/kWh. */
export function sekKwhToOre(sekKwh: number): number {
  return Math.round(toOrePerKwh(sekKwh));
}

/** Price-engine API values from sek_to_eur() — always multiply back to SEK. */
export function priceEngineEurToSekKwh(
  priceEur: number,
  eurToSek = DEFAULT_EUR_TO_SEK_RATE,
): number {
  return priceEur * eurToSek;
}

/** Legacy Heartbeat rows stored as SEK in *_eur_kwh columns (pre-migration). */
export function legacyMarketEurToSekKwh(pricePerKwh: number): number {
  if (pricePerKwh > LEGACY_SEK_IN_EUR_COLUMN_THRESHOLD) {
    return pricePerKwh;
  }
  return priceEngineEurToSekKwh(pricePerKwh);
}

export interface MarketPricePointLike {
  spot_eur_kwh: number;
  all_in_eur_kwh?: number | null;
  spot_sek_kwh?: number | null;
  import_sek_kwh?: number | null;
}

export function marketPointSpotSek(point: MarketPricePointLike): number | null {
  if (point.spot_sek_kwh != null) {
    return point.spot_sek_kwh;
  }
  if (!Number.isFinite(point.spot_eur_kwh)) {
    return null;
  }
  return legacyMarketEurToSekKwh(point.spot_eur_kwh);
}

export function marketPointImportSek(point: MarketPricePointLike): number | null {
  if (point.import_sek_kwh != null) {
    return point.import_sek_kwh;
  }
  if (point.all_in_eur_kwh != null) {
    return legacyMarketEurToSekKwh(point.all_in_eur_kwh);
  }
  return marketPointSpotSek(point);
}

export function marketPointSpotOre(point: MarketPricePointLike): number | null {
  const sek = marketPointSpotSek(point);
  return sek == null ? null : sekKwhToOre(sek);
}

export function marketPointImportOre(point: MarketPricePointLike): number | null {
  const sek = marketPointImportSek(point);
  return sek == null ? null : sekKwhToOre(sek);
}

/** @deprecated Prefer marketPointSpotOre / marketPointImportOre with SEK fields from API. */
export function marketApiPriceToSekKwh(
  pricePerKwh: number,
  eurToSek = DEFAULT_EUR_TO_SEK_RATE,
): number {
  return legacyMarketEurToSekKwh(pricePerKwh);
}

/** @deprecated Prefer marketPointSpotOre / marketPointImportOre with SEK fields from API. */
export function marketApiPriceToOre(pricePerKwh: number): number {
  return sekKwhToOre(marketApiPriceToSekKwh(pricePerKwh));
}

export function formatOrePerKwh(sekKwh: number): string {
  return `${toOrePerKwh(sekKwh).toFixed(1)} öre/kWh`;
}

export function formatMarketPointImportOrePerKwh(point: MarketPricePointLike): string {
  const ore = marketPointImportOre(point);
  return ore == null ? "—" : `${ore.toFixed(1)} öre/kWh`;
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
