"use client";

import type { DisplayOverview } from "@/lib/displayOverview";
import { PiEconomyBars, economyAxisLabels } from "./PiCharts";
import {
  IconBatteryCharging,
  IconBolt,
  IconHome,
  IconLeaf,
  IconPiggy,
  IconPlug,
  IconPylon,
  IconRecycle,
  IconShieldHeart,
  IconSun,
  IconTag,
  IconTrendUp,
  type PiIcon,
} from "./PiIcons";
import {
  MISSING,
  formatDelta,
  formatKr,
  formatKrSigned,
  formatOre,
  kwhReading,
  pctReading,
} from "./piDashboardFormatters";
import { PiTouchCard } from "./PiTouchCard";
import { PI_CARD_SECTIONS, PI_SECTION_META, piHref } from "./piSections";

export function PiEconomyPanel({ slug, data }: { slug: string; data: DisplayOverview | null }) {
  const economy = data?.economy;
  const available = economy?.available !== false && data != null;
  const daily = economy?.daily ?? [];

  const savings = formatDelta(economy?.total_savings_change_pct);
  const cost = formatDelta(economy?.total_cost_change_pct);
  const net = formatDelta(economy?.net_change_pct);

  const monthIndex = data?.generated_at ? new Date(data.generated_at).getMonth() : new Date().getMonth();
  const axis = economyAxisLabels(daily, monthIndex);

  const kpis = [
    { label: "Total besparing", value: formatKr(economy?.total_savings_sek), delta: savings, tone: "is-solar", Icon: IconPiggy },
    { label: "Kostnad", value: formatKr(economy?.total_cost_sek), delta: cost, tone: "is-battery", Icon: IconTag },
    { label: "Netto", value: formatKrSigned(economy?.net_sek), delta: net, tone: "is-grid", Icon: IconTrendUp },
  ];

  return (
    <PiTouchCard
      href={piHref(slug, PI_CARD_SECTIONS.economy)}
      className="pi-card pi-economy"
      ariaLabel={PI_SECTION_META.economy.touchLabel}
    >
      <h2 className="pi-card-title">EKONOMI – DENNA MÅNAD</h2>

      <div className="pi-economy-kpis">
        {kpis.map(({ label, value, delta, tone, Icon }) => (
          <div key={label} className="pi-economy-kpi">
            <span className={`pi-kpi-icon ${tone}`}>
              <Icon />
            </span>
            <div>
              <span className="pi-kpi-label">{label}</span>
              <span className="pi-kpi-value">{available ? value : MISSING}</span>
              <span className={`pi-kpi-delta is-${delta.direction}`}>{delta.text}</span>
            </div>
          </div>
        ))}
      </div>

      {available && daily.length > 0 ? (
        <>
          <div className="pi-economy-chart">
            <PiEconomyBars daily={daily} />
          </div>
          <div>
            <div className="pi-bars-xaxis" aria-hidden>
              {axis.map((label) => (
                <span key={label}>{label}</span>
              ))}
            </div>
            <div className="pi-legend" aria-hidden>
              <span>
                <i style={{ background: "#21cc3e" }} />
                Besparing
              </span>
              <span>
                <i style={{ background: "#ab37c3" }} />
                Kostnad
              </span>
              <span>
                <i style={{ background: "#3aa0e8" }} />
                Netto
              </span>
            </div>
          </div>
        </>
      ) : (
        <div className="pi-empty">Data saknas</div>
      )}
    </PiTouchCard>
  );
}

/**
 * Maps a backend highlight label onto the mockup's row icon. Order matters:
 * "Batteri laddat från sol" must match the battery rule before the solar one.
 */
const HIGHLIGHT_ICONS: { match: RegExp; Icon: PiIcon; tone: string }[] = [
  { match: /batteri/i, Icon: IconBatteryCharging, tone: "pi-icon-grid" },
  { match: /export|nät/i, Icon: IconPylon, tone: "pi-icon-grid" },
  { match: /laddning/i, Icon: IconPlug, tone: "pi-icon-grid" },
  { match: /co₂|co2/i, Icon: IconLeaf, tone: "pi-icon-grid" },
  { match: /soleffekt|sol/i, Icon: IconSun, tone: "pi-icon-solar" },
];

function highlightIcon(label: string) {
  return HIGHLIGHT_ICONS.find((entry) => entry.match.test(label)) ?? { Icon: IconBolt, tone: "pi-icon-muted" };
}

/** Splits "8.8 kW" into value + unit so the unit can be typeset smaller. */
function splitValue(raw: string): { value: string; unit: string } {
  const match = /^(-?[\d\s.,]+)\s*(.*)$/.exec(raw.trim());
  if (!match) return { value: raw, unit: "" };
  return { value: match[1].trim(), unit: match[2].trim() };
}

export function PiHighlightsPanel({ slug, data }: { slug: string; data: DisplayOverview | null }) {
  const highlights = data?.highlights;
  const items = highlights?.items ?? [];
  const available = highlights?.available !== false && items.length > 0;

  return (
    <PiTouchCard
      href={piHref(slug, PI_CARD_SECTIONS.highlights)}
      className="pi-card pi-highlights"
      ariaLabel={PI_SECTION_META.insights.touchLabel}
    >
      <h2 className="pi-card-title">DAGENS HÖJDPUNKTER</h2>
      {available ? (
        <ul>
          {items.slice(0, 5).map((item) => {
            const { Icon, tone } = highlightIcon(item.label_sv);
            const { value, unit } = splitValue(item.value);
            return (
              <li key={item.label_sv}>
                <span className={`pi-highlight-icon ${tone}`}>
                  <Icon />
                </span>
                <span className="pi-highlight-label">{item.label_sv}</span>
                <span className="pi-highlight-value">
                  {value}
                  {unit ? <span>{unit}</span> : null}
                </span>
                <span className="pi-highlight-detail">{item.detail_sv ?? ""}</span>
              </li>
            );
          })}
        </ul>
      ) : (
        <div className="pi-empty">Data saknas</div>
      )}
    </PiTouchCard>
  );
}

export function PiKpiBar({ slug, data }: { slug: string; data: DisplayOverview | null }) {
  const live = data?.live;
  const price = data?.price;

  const produced = kwhReading(live?.produced_today_kwh);
  const consumed = kwhReading(live?.consumed_today_kwh);
  const soh = pctReading(live?.battery_soh_pct);
  const sufficiency = pctReading(live?.self_sufficiency_pct);
  const selfUse = pctReading(live?.self_consumption_pct);

  const tier = price?.available === false ? MISSING : (price?.tier_label_sv ?? MISSING);
  const tierTone = price?.tier === "red" ? "is-danger" : price?.tier === "green" ? "is-grid" : "";

  const cells: {
    label: string;
    value: string;
    unit?: string;
    sub?: string;
    Icon: PiIcon;
    tone: string;
    valueTone?: string;
    section: (typeof PI_CARD_SECTIONS)[keyof typeof PI_CARD_SECTIONS];
    touchLabel: string;
  }[] = [
    {
      label: "TOTAL PRODUKTION",
      value: produced.value,
      unit: produced.unit,
      Icon: IconSun,
      tone: "pi-icon-solar",
      section: PI_CARD_SECTIONS.kpiProduction,
      touchLabel: PI_SECTION_META.solar.touchLabel,
    },
    {
      label: "TOTAL FÖRBRUKNING",
      value: consumed.value,
      unit: consumed.unit,
      Icon: IconHome,
      tone: "pi-icon-house",
      section: PI_CARD_SECTIONS.kpiConsumption,
      touchLabel: PI_SECTION_META.energy.touchLabel,
    },
    {
      label: "BATTERI SOH",
      value: soh.value,
      unit: soh.unit,
      Icon: IconShieldHeart,
      tone: "pi-icon-grid",
      section: PI_CARD_SECTIONS.kpiBatterySoh,
      touchLabel: PI_SECTION_META.battery.touchLabel,
    },
    {
      label: "SJÄLVFÖRSÖRJNING",
      value: sufficiency.value,
      unit: sufficiency.unit,
      Icon: IconLeaf,
      tone: "pi-icon-grid",
      section: PI_CARD_SECTIONS.kpiSelfSufficiency,
      touchLabel: PI_SECTION_META.energy.touchLabel,
    },
    {
      label: "EGENANVÄNDNING",
      value: selfUse.value,
      unit: selfUse.unit,
      Icon: IconRecycle,
      tone: "pi-icon-grid",
      section: PI_CARD_SECTIONS.kpiSelfUse,
      touchLabel: PI_SECTION_META.energy.touchLabel,
    },
    {
      label: "AKTIV PRISNIVÅ",
      value: tier,
      sub: price?.available === false ? "Data saknas" : formatOre(price?.current_ore_kwh),
      Icon: IconTrendUp,
      tone: price?.tier === "red" ? "pi-icon-danger" : "pi-icon-grid",
      valueTone: tierTone,
      section: PI_CARD_SECTIONS.kpiPrice,
      touchLabel: PI_SECTION_META.economy.touchLabel,
    },
  ];

  return (
    <footer className="pi-kpibar">
      {cells.map(({ label, value, unit, sub, Icon, tone, valueTone, section, touchLabel }) => (
        <PiTouchCard
          key={label}
          href={piHref(slug, section)}
          className="pi-kpibar-cell"
          ariaLabel={`${label}: ${touchLabel}`}
        >
          <span className={`pi-kpibar-icon ${tone}`}>
            <Icon />
          </span>
          <div>
            <span className="pi-kpibar-label">{label}</span>
            <span className={`pi-kpibar-value ${valueTone ?? ""}`}>
              {value}
              {unit ? <span>{unit}</span> : null}
            </span>
            {sub ? <span className="pi-kpibar-sub">{sub}</span> : null}
          </div>
        </PiTouchCard>
      ))}
    </footer>
  );
}
