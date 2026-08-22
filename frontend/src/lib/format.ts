/** Centralized number formatting for EMIC dashboard. */

export function formatPower(w: number | null | undefined): string {
  if (w == null || Number.isNaN(w)) return "—";
  const abs = Math.abs(w);
  if (abs >= 1000) {
    return `${(w / 1000).toFixed(1).replace(".", ",")} kW`;
  }
  return `${Math.round(w)} W`;
}

export function formatEnergy(kwh: number | null | undefined): string {
  if (kwh == null || Number.isNaN(kwh)) return "—";
  return `${kwh.toFixed(1).replace(".", ",")} kWh`;
}

export function formatMoney(sek: number | null | undefined): string {
  if (sek == null || Number.isNaN(sek)) return "—";
  const abs = Math.abs(sek);
  const decimals = abs >= 100 ? 0 : 2;
  const formatted = sek.toLocaleString("sv-SE", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  return `${formatted} kr`;
}

export function formatPercent(p: number | null | undefined): string {
  if (p == null || Number.isNaN(p)) return "—";
  const rounded = Math.round(p * 10) / 10;
  const text = Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1).replace(".", ",");
  return `${text} %`;
}

export function formatOre(ore: number | null | undefined): string {
  if (ore == null || Number.isNaN(ore)) return "—";
  return `${ore.toFixed(1).replace(".", ",")} öre/kWh`;
}

export function formatRelativeTime(iso: string | null | undefined, now = Date.now()): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const seconds = Math.max(0, Math.floor((now - then) / 1000));
  if (seconds < 60) return `${seconds} sek sedan`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min sedan`;
  const hours = Math.floor(minutes / 60);
  return `${hours} tim sedan`;
}

/** Alias kept for backward compatibility with existing formatWatts usage. */
export function formatWatts(w: number): string {
  return formatPower(w);
}
