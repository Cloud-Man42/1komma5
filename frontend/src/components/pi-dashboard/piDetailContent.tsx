"use client";

import type { DisplayOverview } from "@/lib/displayOverview";
import { PiAreaChart, PiEconomyBars, PiGauge, economyAxisLabels } from "./PiCharts";
import { PiEnergyFlowDiagram } from "./PiEnergyFlowDiagram";
import {
  MISSING,
  formatDayTime,
  formatDelta,
  formatKr,
  formatKrSigned,
  formatOre,
  ampReading,
  kwReading,
  kwhReading,
  pctReading,
  powerReading,
  sectionText,
  sparklineValues,
  tempReading,
} from "./piDashboardFormatters";
import type { PiSection } from "./piSections";

const DEFAULT_TZ = "Europe/Stockholm";

export type DetailTile = {
  label: string;
  value: string;
  unit?: string;
  sub?: string;
};

function vehicleTitle(vehicle: DisplayOverview["vehicle"] | undefined): string {
  const name = vehicle?.display_name?.trim() ?? "";
  const model = vehicle?.model?.trim() ?? "";
  if (!name) return model.toUpperCase();
  if (!model || name.toLowerCase().includes(model.toLowerCase())) return name.toUpperCase();
  return `${name} ${model}`.toUpperCase();
}

function highlightByLabel(data: DisplayOverview | null, pattern: RegExp) {
  return data?.highlights?.items?.find((item) => pattern.test(item.label_sv));
}

function batterySocRange(data: DisplayOverview | null): { min: string; max: string } {
  const points = data?.sparklines?.battery?.points ?? [];
  if (points.length === 0) return { min: MISSING, max: MISSING };
  const values = points.map((p) => p.value).filter((v) => Number.isFinite(v));
  if (values.length === 0) return { min: MISSING, max: MISSING };
  return {
    min: `${Math.round(Math.min(...values))}%`,
    max: `${Math.round(Math.max(...values))}%`,
  };
}

function tilesForSection(section: PiSection, data: DisplayOverview | null): DetailTile[] {
  const live = data?.live;
  const timezone = data?.site?.timezone ?? DEFAULT_TZ;

  switch (section) {
    case "solar": {
      const peak = highlightByLabel(data, /soleffekt|sol/i);
      const produced = kwhReading(live?.produced_today_kwh);
      const power = kwReading(live?.solar_power_kw);
      const selfUse = pctReading(live?.self_consumption_pct);
      const forecast = kwhReading(data?.solar?.expected_today_kwh);
      const remaining = kwhReading(data?.solar?.remaining_today_kwh);
      return [
        { label: "Aktuell effekt", value: power.value, unit: power.unit },
        { label: "Producerat idag", value: produced.value, unit: produced.unit },
        { label: "Prognos idag", value: forecast.value, unit: forecast.unit },
        { label: "Kvar idag", value: remaining.value, unit: remaining.unit },
        { label: "Egenanvändning", value: selfUse.value, unit: selfUse.unit },
        { label: "Högsta soleffekt", value: peak?.value ?? MISSING, sub: peak?.detail_sv ?? undefined },
      ];
    }
    case "energy": {
      const house = kwReading(live?.house_power_kw);
      const consumed = kwhReading(live?.consumed_today_kwh);
      const imported = kwhReading(live?.imported_today_kwh);
      const exported = kwhReading(live?.exported_today_kwh);
      const sufficiency = pctReading(live?.self_sufficiency_pct);
      return [
        { label: "Husförbrukning", value: house.value, unit: house.unit },
        { label: "Förbrukat idag", value: consumed.value, unit: consumed.unit },
        { label: "Import idag", value: imported.value, unit: imported.unit },
        { label: "Export idag", value: exported.value, unit: exported.unit },
        { label: "Självförsörjning", value: sufficiency.value, unit: sufficiency.unit },
      ];
    }
    case "battery": {
      const soc = pctReading(live?.battery_soc_pct);
      const power = kwReading(live?.battery_power_kw);
      const stored = kwhReading(live?.battery_stored_kwh);
      const capacity = kwhReading(live?.battery_capacity_kwh);
      const charged = kwhReading(live?.battery_charged_today_kwh);
      const discharged = kwhReading(live?.battery_discharged_today_kwh);
      const range = batterySocRange(data);
      const soh = pctReading(live?.battery_soh_pct);
      return [
        { label: "Laddningsgrad", value: soc.value, unit: soc.unit },
        { label: "Effekt", value: power.value, unit: power.unit, sub: live?.battery_state_sv ?? undefined },
        { label: "Lagrad energi", value: stored.value, unit: stored.unit, sub: `${capacity.value} ${capacity.unit} kapacitet` },
        { label: "Laddat idag", value: charged.value, unit: charged.unit },
        { label: "Urladdat idag", value: discharged.value, unit: discharged.unit },
        { label: "Min / max idag", value: range.min, sub: range.max },
        { label: "SoH", value: soh.value, unit: soh.unit },
      ];
    }
    case "grid": {
      const net = kwReading(live?.grid_net_power_kw);
      const imported = kwhReading(live?.imported_today_kwh);
      const exported = kwhReading(live?.exported_today_kwh);
      const surplus = kwReading(live?.solar_surplus_kw);
      return [
        { label: "Netto mot nät", value: net.value, unit: net.unit, sub: live?.grid_direction_sv ?? undefined },
        { label: "Import idag", value: imported.value, unit: imported.unit },
        { label: "Export idag", value: exported.value, unit: exported.unit },
        { label: "Solöverskott", value: surplus.value, unit: surplus.unit },
      ];
    }
    case "vehicle": {
      const vehicle = data?.vehicle;
      const available = vehicle?.available !== false && data != null;
      const soc = pctReading(vehicle?.soc_pct);
      const range =
        vehicle?.range_km != null ? `${Math.round(vehicle.range_km)} km` : MISSING;
      return [
        { label: vehicleTitle(vehicle), value: sectionText(available, vehicle?.status_sv) },
        { label: "Laddningsgrad", value: soc.value, unit: soc.unit },
        { label: "Räckvidd", value: range },
        { label: "Laddläge", value: sectionText(available, vehicle?.charging_mode_sv) },
        { label: "Klart senast", value: formatDayTime(vehicle?.ready_by, timezone) },
        { label: "Kostnad idag", value: formatKr(vehicle?.cost_today_sek) },
        { label: "Mål-SoC", value: pctReading(vehicle?.target_soc_pct).value, unit: "%" },
      ];
    }
    case "charger": {
      const charger = data?.charger;
      const available = charger?.available !== false && data != null;
      const power = powerReading(charger?.power_w);
      const amps = ampReading(charger?.available_current_a);
      return [
        { label: charger?.name?.toUpperCase() ?? "LADDBOX", value: sectionText(available, charger?.status_sv) },
        { label: "Effekt", value: power.value, unit: power.unit },
        { label: "Tillgänglig ström", value: amps.value, unit: amps.unit },
        {
          label: "Smart laddning",
          value:
            charger?.smart_charging_active == null
              ? MISSING
              : charger.smart_charging_active
                ? "Aktiv"
                : "Av",
        },
        { label: "Beslut", value: sectionText(available, charger?.decision_reason_sv) },
        { label: "Klart senast", value: formatDayTime(charger?.ready_by, timezone) },
        { label: "Prisnivå", value: sectionText(available, charger?.price_tier_label_sv) },
      ];
    }
    case "spa": {
      const spa = data?.spa;
      const available = spa?.available !== false && data != null;
      const temp = tempReading(spa?.water_temperature_c);
      const consumption = kwhReading(spa?.consumption_today_kwh);
      const cost = formatKr(spa?.cost_today_sek);
      const power = powerReading(spa?.power_w);
      const cycles =
        spa?.filter_cycles_completed_today != null && spa?.filter_cycles_target_today != null
          ? `${spa.filter_cycles_completed_today}/${spa.filter_cycles_target_today}`
          : MISSING;
      return [
        { label: "Vattentemperatur", value: temp.value, unit: temp.unit },
        { label: "Filtrering", value: sectionText(available, spa?.filter_status_sv) },
        { label: "Filtercykler idag", value: cycles },
        { label: "Nästa rengöring", value: formatDayTime(spa?.next_cleaning_at, timezone) },
        { label: "Förbrukning idag", value: consumption.value, unit: consumption.unit },
        { label: "Kostnad idag", value: cost },
        { label: "Effekt", value: power.value, unit: power.unit },
      ];
    }
    case "economy": {
      const economy = data?.economy;
      const price = data?.price;
      const savings = formatDelta(economy?.total_savings_change_pct);
      const cost = formatDelta(economy?.total_cost_change_pct);
      const net = formatDelta(economy?.net_change_pct);
      return [
        { label: "Total besparing", value: formatKr(economy?.total_savings_sek), sub: savings.text },
        { label: "Kostnad", value: formatKr(economy?.total_cost_sek), sub: cost.text },
        { label: "Netto", value: formatKrSigned(economy?.net_sek), sub: net.text },
        {
          label: "Aktuellt elpris",
          value: price?.available === false ? MISSING : formatOre(price?.current_ore_kwh),
          sub: price?.tier_label_sv ?? undefined,
        },
        {
          label: "Lägst / högst idag",
          value:
            price?.lowest_ore_kwh != null && price?.highest_ore_kwh != null
              ? `${formatOre(price.lowest_ore_kwh)} / ${formatOre(price.highest_ore_kwh)}`
              : MISSING,
        },
      ];
    }
    case "insights": {
      const items = data?.highlights?.items ?? [];
      const sys = data?.system_status;
      const tiles: DetailTile[] = items.slice(0, 5).map((item) => ({
        label: item.label_sv,
        value: item.value,
        sub: item.detail_sv ?? undefined,
      }));
      tiles.push({
        label: "Systemstatus",
        value: sys?.status_sv ?? MISSING,
        sub: sys?.detail_sv ?? undefined,
      });
      return tiles;
    }
    default:
      return [];
  }
}

export function PiDetailChart({ section, data }: { section: PiSection; data: DisplayOverview | null }) {
  const live = data?.live;
  const economy = data?.economy;
  const monthIndex = data?.generated_at ? new Date(data.generated_at).getMonth() : new Date().getMonth();

  switch (section) {
    case "solar":
      return (
        <PiAreaChart
          className="pi-detail-chart-svg"
          values={
            (data?.solar?.forecast_curve?.length ?? 0) > 0
              ? data!.solar!.forecast_curve!.map((point) => point.value)
              : sparklineValues(data, "solar")
          }
          colour="#fcc206"
          gradientId="pi-detail-solar"
        />
      );
    case "energy":
      return (
        <PiAreaChart
          className="pi-detail-chart-svg"
          values={sparklineValues(data, "house")}
          colour="#06baf8"
          gradientId="pi-detail-house"
        />
      );
    case "battery":
      return (
        <PiAreaChart
          className="pi-detail-chart-svg"
          values={sparklineValues(data, "battery")}
          colour="#c94ad4"
          gradientId="pi-detail-battery"
        />
      );
    case "grid":
      return (
        <div className="pi-detail-flow-wrap">
          <PiEnergyFlowDiagram data={data} fit="contain" />
          <PiAreaChart
            className="pi-detail-chart-svg pi-detail-chart-inline"
            values={sparklineValues(data, "grid")}
            colour="#21cc3e"
            gradientId="pi-detail-grid"
          />
        </div>
      );
    case "economy":
      if (economy?.available !== false && (economy?.daily?.length ?? 0) > 0) {
        return (
          <div className="pi-detail-economy">
            <PiEconomyBars daily={economy!.daily} />
            <div className="pi-bars-xaxis" aria-hidden>
              {economyAxisLabels(economy!.daily, monthIndex).map((label) => (
                <span key={label}>{label}</span>
              ))}
            </div>
          </div>
        );
      }
      return <div className="pi-empty">Data saknas</div>;
    case "vehicle":
    case "charger":
    case "spa":
    case "insights":
      return null;
    default:
      return null;
  }
}

export function PiDetailTiles({ section, data }: { section: PiSection; data: DisplayOverview | null }) {
  const tiles = tilesForSection(section, data);
  const surplusFraction =
    liveSurplusFraction(data);

  return (
    <div className={`pi-detail-tiles pi-detail-tiles-${section}`}>
      {tiles.map((tile) => (
        <article key={tile.label} className="pi-detail-tile">
          <span className="pi-detail-tile-label">{tile.label}</span>
          <span className="pi-detail-tile-value">
            {tile.value}
            {tile.unit ? <span>{tile.unit}</span> : null}
          </span>
          {tile.sub ? <span className="pi-detail-tile-sub">{tile.sub}</span> : null}
        </article>
      ))}
      {section === "solar" && surplusFraction != null ? (
        <article className="pi-detail-tile pi-detail-tile-gauge">
          <span className="pi-detail-tile-label">Solöverskott</span>
          <div className="pi-detail-gauge-mini">
            <PiGauge fraction={surplusFraction} />
          </div>
        </article>
      ) : null}
    </div>
  );
}

function liveSurplusFraction(data: DisplayOverview | null): number | null {
  const live = data?.live;
  if (live?.solar_surplus_kw == null || live?.solar_power_kw == null || live.solar_power_kw <= 0) {
    return null;
  }
  return live.solar_surplus_kw / live.solar_power_kw;
}

export { tilesForSection };
