"use client";

import type { DisplayOverview } from "@/lib/displayOverview";
import { PiAreaChart, PiGauge } from "./PiCharts";
import { IconBattery, IconHome, IconPylon, IconSun, type PiIcon } from "./PiIcons";
import { PiTouchCard } from "./PiTouchCard";
import { MISSING, kwReading, kwhReading, pctReading, sparklineValues } from "./piDashboardFormatters";
import { PI_CARD_SECTIONS, PI_SECTION_META, piHref } from "./piSections";

const HOURS = ["00", "04", "08", "12", "16", "20", "24"];

function MetricCard({
  variant,
  title,
  Icon,
  value,
  unit,
  sub,
  subAccent,
  values,
  colour,
  gradientId,
  href,
  ariaLabel,
}: {
  variant: string;
  title: string;
  Icon: PiIcon;
  value: string;
  unit: string;
  sub: string;
  subAccent?: boolean;
  values: number[];
  colour: string;
  gradientId: string;
  href: string;
  ariaLabel: string;
}) {
  return (
    <PiTouchCard href={href} className={`pi-card pi-metric is-${variant}`} ariaLabel={ariaLabel}>
      <h2 className="pi-metric-title">{title}</h2>
      <div className="pi-metric-main">
        <Icon className="pi-metric-icon" />
        <span className="pi-metric-value">
          {value}
          {unit ? <span>{unit}</span> : null}
        </span>
      </div>
      <span className={`pi-metric-sub${subAccent ? " is-accent" : ""}`} style={subAccent ? { color: colour } : undefined}>
        {sub}
      </span>
      <PiAreaChart className="pi-metric-chart" values={values} colour={colour} gradientId={gradientId} />
      <div className="pi-metric-axis" aria-hidden>
        {HOURS.map((hour) => (
          <span key={hour}>{hour}</span>
        ))}
      </div>
    </PiTouchCard>
  );
}

export function PiMetricCards({ slug, data }: { slug: string; data: DisplayOverview | null }) {
  const live = data?.live;

  const solar = kwReading(live?.solar_power_kw);
  const house = kwReading(live?.house_power_kw);
  const battery = pctReading(live?.battery_soc_pct);
  const gridNet = kwReading(live?.grid_net_power_kw);

  const producedToday = kwhReading(live?.produced_today_kwh);
  const consumedToday = kwhReading(live?.consumed_today_kwh);
  const stored = kwhReading(live?.battery_stored_kwh);
  const capacity = kwhReading(live?.battery_capacity_kwh);

  const surplus = kwReading(live?.solar_surplus_kw);
  const surplusFraction =
    live?.solar_surplus_kw != null && live?.solar_power_kw != null && live.solar_power_kw > 0
      ? live.solar_surplus_kw / live.solar_power_kw
      : null;

  return (
    <section className="pi-row-metrics">
      <MetricCard
        variant="solar"
        title="SOLPRODUKTION"
        Icon={IconSun}
        value={solar.value}
        unit={solar.unit}
        sub={producedToday.value === MISSING ? "Idag: --" : `Idag: ${producedToday.value} ${producedToday.unit}`}
        values={sparklineValues(data, "solar")}
        colour="#fcc206"
        gradientId="pi-grad-solar"
        href={piHref(slug, PI_CARD_SECTIONS.solarProduction)}
        ariaLabel={PI_SECTION_META.solar.touchLabel}
      />

      <MetricCard
        variant="house"
        title="HUSFÖRBRUKNING"
        Icon={IconHome}
        value={house.value}
        unit={house.unit}
        sub={consumedToday.value === MISSING ? "Idag: --" : `Idag: ${consumedToday.value} ${consumedToday.unit}`}
        values={sparklineValues(data, "house")}
        colour="#06baf8"
        gradientId="pi-grad-house"
        href={piHref(slug, PI_CARD_SECTIONS.houseConsumption)}
        ariaLabel={PI_SECTION_META.energy.touchLabel}
      />

      <MetricCard
        variant="battery"
        title="BATTERI"
        Icon={IconBattery}
        value={battery.value}
        unit={battery.unit}
        sub={
          stored.value === MISSING || capacity.value === MISSING
            ? MISSING
            : `${stored.value} ${stored.unit} / ${capacity.value} ${capacity.unit}`
        }
        values={sparklineValues(data, "battery")}
        colour="#c94ad4"
        gradientId="pi-grad-battery"
        href={piHref(slug, PI_CARD_SECTIONS.battery)}
        ariaLabel={PI_SECTION_META.battery.touchLabel}
      />

      <MetricCard
        variant="grid"
        title="NETTO MOT NÄT"
        Icon={IconPylon}
        value={gridNet.value}
        unit={gridNet.unit}
        sub={live?.grid_direction_sv ?? MISSING}
        values={sparklineValues(data, "grid")}
        colour="#21cc3e"
        gradientId="pi-grad-grid"
        href={piHref(slug, PI_CARD_SECTIONS.gridNet)}
        ariaLabel={PI_SECTION_META.grid.touchLabel}
      />

      <PiTouchCard
        href={piHref(slug, PI_CARD_SECTIONS.solarSurplus)}
        className="pi-card pi-gauge-card"
        ariaLabel={PI_SECTION_META.solar.touchLabel}
      >
        <h2 className="pi-metric-title">SOLÖVERSKOTT</h2>
        <div className="pi-gauge-wrap">
          <PiGauge fraction={surplusFraction} />
          <div className="pi-gauge-center">
            <span className="pi-gauge-value">
              {surplus.value}
              {surplus.unit ? <span>{surplus.unit}</span> : null}
            </span>
            <span className="pi-gauge-label">Just nu</span>
            <span className="pi-gauge-state">{live?.grid_direction_sv ?? MISSING}</span>
          </div>
        </div>
      </PiTouchCard>
    </section>
  );
}
