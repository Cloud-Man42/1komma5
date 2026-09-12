/** Client-side aggregate from per-site overview entries (visibility filter). */

import type { MultiSiteAggregate, MultiSiteOverviewResponse, MultiSiteSiteEntry } from "@/lib/multiSiteApi";

export type CurrencyRow = MultiSiteOverviewResponse["currencies"][number];

function sumOptional(values: Array<number | null | undefined>): number | null {
  const nums = values.filter((v): v is number => v != null && !Number.isNaN(v));
  if (nums.length === 0) return null;
  return Math.round(nums.reduce((a, b) => a + b, 0) * 1000) / 1000;
}

function round2(value: number | null): number | null {
  if (value == null) return null;
  return Math.round(value * 100) / 100;
}

export function aggregateSiteEntries(sites: MultiSiteSiteEntry[]): MultiSiteAggregate {
  const available = sites.filter((s) => s.available);

  const DEFAULT_BATTERY_KWH = 13.5;
  const batteryCap = sumOptional(
    available.map((s) => {
      if (s.live.batteryCapacityKwh != null) return s.live.batteryCapacityKwh;
      if (s.live.batterySocPercent != null) return DEFAULT_BATTERY_KWH;
      return null;
    }),
  );
  const batteryStored = sumOptional(
    available.map((s) => {
      if (s.live.batteryStoredKwh != null) return s.live.batteryStoredKwh;
      if (s.live.batterySocPercent != null && s.live.batteryCapacityKwh != null) {
        return (s.live.batteryCapacityKwh * s.live.batterySocPercent) / 100;
      }
      if (s.live.batterySocPercent != null) {
        return (DEFAULT_BATTERY_KWH * s.live.batterySocPercent) / 100;
      }
      return null;
    }),
  );
  let batterySoc: number | null = null;
  if (batteryCap && batteryCap > 0 && batteryStored != null) {
    batterySoc = Math.round((batteryStored / batteryCap) * 1000) / 10;
  }

  const chargeKw: number[] = [];
  const dischargeKw: number[] = [];
  for (const site of available) {
    const p = site.live.batteryPowerKw;
    if (p == null) continue;
    if (p > 0) {
      chargeKw.push(p);
      dischargeKw.push(0);
    } else if (p < 0) {
      chargeKw.push(0);
      dischargeKw.push(Math.abs(p));
    }
  }

  const importKw = sumOptional(available.map((s) => s.live.gridImportPowerKw));
  const exportKw = sumOptional(available.map((s) => s.live.gridExportPowerKw));
  let gridNet: number | null = null;
  if (importKw != null || exportKw != null) {
    gridNet = Math.round(((exportKw ?? 0) - (importKw ?? 0)) * 1000) / 1000;
  }

  const solarToday = sumOptional(available.map((s) => s.today.solarKwh));
  const consumptionToday = sumOptional(available.map((s) => s.today.consumptionKwh));
  const importToday = sumOptional(available.map((s) => s.today.gridImportKwh));
  const exportToday = sumOptional(available.map((s) => s.today.gridExportKwh));

  const bestSolar = available.reduce<{ slug: string | null; kwh: number | null }>(
    (best, site) => {
      const kwh = site.today.solarKwh;
      if (kwh == null) return best;
      if (best.kwh == null || kwh > best.kwh) return { slug: site.slug, kwh };
      return best;
    },
    { slug: null, kwh: null },
  );

  return {
    solarPowerKw: sumOptional(available.map((s) => s.live.solarPowerKw)),
    consumptionPowerKw: sumOptional(available.map((s) => s.live.consumptionPowerKw)),
    gridImportPowerKw: importKw,
    gridExportPowerKw: exportKw,
    gridNetPowerKw: gridNet,
    batteryChargePowerKw: chargeKw.length ? sumOptional(chargeKw) : null,
    batteryDischargePowerKw: dischargeKw.length ? sumOptional(dischargeKw) : null,
    batteryCapacityKwh: round2(batteryCap),
    batteryStoredKwh: round2(batteryStored),
    batterySocPercent: batterySoc,
    solarTodayKwh: round2(solarToday),
    consumptionTodayKwh: round2(consumptionToday),
    gridImportTodayKwh: round2(importToday),
    gridExportTodayKwh: round2(exportToday),
    evPowerKw: sumOptional(available.map((s) => s.live.evPowerKw ?? null)),
    bestSolarSiteSlug: bestSolar.slug,
    bestSolarSiteKwh: round2(bestSolar.kwh),
  };
}

export function aggregateSiteCurrencies(sites: MultiSiteSiteEntry[]): CurrencyRow[] {
  const byCurrency = new Map<string, { costToday: number | null; savingsToday: number | null }>();

  for (const site of sites.filter((s) => s.available)) {
    const currency = site.currency;
    if (!currency) continue;
    const row = byCurrency.get(currency) ?? { costToday: null, savingsToday: null };
    if (site.today.costToday != null) {
      row.costToday = round2((row.costToday ?? 0) + site.today.costToday);
    }
    if (site.today.savingsToday != null) {
      row.savingsToday = round2((row.savingsToday ?? 0) + site.today.savingsToday);
    }
    byCurrency.set(currency, row);
  }

  return Array.from(byCurrency.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([currency, values]) => ({ currency, ...values }));
}

export function aggregateSiteHealth(
  sites: MultiSiteSiteEntry[],
): MultiSiteOverviewResponse["health"] {
  return sites.reduce(
    (acc, site) => {
      if (site.health === "healthy") acc.healthy += 1;
      else if (site.health === "degraded") acc.degraded += 1;
      else acc.offline += 1;
      return acc;
    },
    { healthy: 0, degraded: 0, offline: 0 },
  );
}
