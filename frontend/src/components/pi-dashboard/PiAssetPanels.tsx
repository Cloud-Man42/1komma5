"use client";

import Image from "next/image";
import type { DisplayOverview } from "@/lib/displayOverview";
import { IconBolt, IconCheckCircle, IconClock, IconThermometer, IconWallet } from "./PiIcons";
import {
  MISSING,
  ampReading,
  formatDayTime,
  formatKr,
  krReading,
  kwhReading,
  pctReading,
  powerReading,
  sectionText,
  tempReading,
} from "./piDashboardFormatters";
import { PiTouchCard } from "./PiTouchCard";
import { PI_CARD_SECTIONS, PI_SECTION_META, piHref } from "./piSections";

const DEFAULT_TZ = "Europe/Stockholm";

/**
 * Panel heading for the vehicle, e.g. "MERCEDES EQE 500". The model is appended
 * only when it adds information: EMIC stores make and model separately, and for
 * some vehicles both fields hold the same string.
 */
function vehicleLabel(vehicle: DisplayOverview["vehicle"] | undefined): string {
  const name = vehicle?.display_name?.trim() ?? "";
  const model = vehicle?.model?.trim() ?? "";
  if (!name) return model.toUpperCase();
  if (!model || name.toLowerCase().includes(model.toLowerCase())) return name.toUpperCase();
  return `${name} ${model}`.toUpperCase();
}

export function PiVehiclePanel({ slug, data }: { slug: string; data: DisplayOverview | null }) {
  const timezone = data?.site?.timezone ?? DEFAULT_TZ;
  const vehicle = data?.vehicle;
  const available = vehicle?.available !== false && data != null;

  const soc = pctReading(vehicle?.soc_pct);
  const range = vehicle?.range_km != null ? `~ ${Math.round(vehicle.range_km)} km` : MISSING;
  const title = `FORDON${vehicleLabel(vehicle) ? ` – ${vehicleLabel(vehicle)}` : ""}`;

  return (
    <PiTouchCard
      href={piHref(slug, PI_CARD_SECTIONS.vehicle)}
      className="pi-card pi-vehicle"
      ariaLabel={PI_SECTION_META.vehicle.touchLabel}
    >
      <div className="pi-panel-head">
        <h2 className="pi-card-title">{title}</h2>
        <span className="pi-panel-status">{sectionText(available, vehicle?.status_sv)}</span>
      </div>

      <div className="pi-vehicle-body">
        <div className="pi-vehicle-stats">
          <span className="pi-vehicle-soc">
            {soc.value}
            {soc.unit ? <span>{soc.unit}</span> : null}
          </span>
          <span className="pi-vehicle-range">{range}</span>
          <div className="pi-bar-track">
            <div className="pi-bar-fill" style={{ width: `${Math.min(100, Math.max(0, vehicle?.soc_pct ?? 0))}%` }} />
          </div>
        </div>
        <Image
          className="pi-vehicle-image"
          src="/images/vehicle-eqe-profile.png"
          alt=""
          width={392}
          height={160}
          priority
        />
      </div>

      <div className="pi-mini-row">
        <div className="pi-mini">
          <IconBolt className="pi-icon-grid" />
          <span className="pi-mini-label">Laddläge</span>
          <span className="pi-mini-value">{sectionText(available, vehicle?.charging_mode_sv)}</span>
        </div>
        <div className="pi-mini">
          <IconClock className="pi-icon-house" />
          <span className="pi-mini-label">Klart senast</span>
          <span className="pi-mini-value">{formatDayTime(vehicle?.ready_by, timezone)}</span>
        </div>
        <div className="pi-mini">
          <IconWallet className="pi-icon-solar" />
          <span className="pi-mini-label">Kostnad idag</span>
          <span className="pi-mini-value">{formatKr(vehicle?.cost_today_sek)}</span>
        </div>
      </div>
    </PiTouchCard>
  );
}

export function PiChargerPanel({ slug, data }: { slug: string; data: DisplayOverview | null }) {
  const timezone = data?.site?.timezone ?? DEFAULT_TZ;
  const charger = data?.charger;
  const available = charger?.available !== false && data != null;

  const power = powerReading(charger?.power_w);
  const current = ampReading(charger?.available_current_a);
  const title = charger?.name ? `LADDBOX – ${charger.name.toUpperCase()}` : "LADDBOX";
  const priceTier = charger?.price_tier_label_sv ?? MISSING;
  const priceDanger = priceTier.toLowerCase().includes("rött") || priceTier.toLowerCase().includes("dyrt");

  return (
    <PiTouchCard
      href={piHref(slug, PI_CARD_SECTIONS.charger)}
      className="pi-card pi-charger"
      ariaLabel={PI_SECTION_META.charger.touchLabel}
    >
      <div className="pi-panel-head">
        <h2 className="pi-card-title">{title}</h2>
        <span className="pi-panel-status">{sectionText(available, charger?.status_sv)}</span>
      </div>

      <div className="pi-charger-body">
        <div className="pi-charger-stats">
          <div>
            <span className="pi-stat-value">
              {power.value}
              {power.unit ? <span>{power.unit}</span> : null}
            </span>
            <span className="pi-stat-label">Aktuell effekt</span>
          </div>
          <div>
            <span className="pi-stat-value">
              {current.value}
              {current.unit ? <span>{current.unit}</span> : null}
            </span>
            <span className="pi-stat-label">Tillgänglig ström</span>
          </div>
          <div>
            <span className="pi-stat-heading">Smart laddning</span>
            <span className="pi-stat-strong">
              {charger?.smart_charging_active == null
                ? MISSING
                : charger.smart_charging_active
                  ? "Aktiv"
                  : "Av"}
            </span>
          </div>
        </div>
        <Image
          className="pi-charger-image"
          src="/images/charge-amps-halo.png"
          alt=""
          width={208}
          height={208}
          priority
        />
      </div>

      <div className="pi-mini-row is-two">
        <div className="pi-mini">
          <span className="pi-mini-label">Klar senast</span>
          <span className="pi-mini-value">{formatDayTime(charger?.ready_by, timezone)}</span>
        </div>
        <div className="pi-mini">
          <span className="pi-mini-label">Prisnivå</span>
          <span className={`pi-mini-value${priceDanger ? " is-danger" : ""}`}>{priceTier}</span>
        </div>
      </div>
    </PiTouchCard>
  );
}

export function PiSpaPanel({ slug, data }: { slug: string; data: DisplayOverview | null }) {
  const timezone = data?.site?.timezone ?? DEFAULT_TZ;
  const spa = data?.spa;
  const available = spa?.available !== false && data != null;

  const temp = tempReading(spa?.water_temperature_c);
  const consumption = kwhReading(spa?.consumption_today_kwh);
  const cost = krReading(spa?.cost_today_sek, 2);

  return (
    <PiTouchCard
      href={piHref(slug, PI_CARD_SECTIONS.spa)}
      className="pi-card pi-spa"
      ariaLabel={PI_SECTION_META.spa.touchLabel}
    >
      <h2 className="pi-card-title">SPA – ARCTIC SPA</h2>

      <div className="pi-spa-body">
        <Image
          className="pi-spa-image"
          src="/images/spa-hero.png"
          alt=""
          width={244}
          height={164}
          priority
        />
        <div className="pi-spa-rows">
          <div className="pi-spa-row">
            <IconThermometer className="pi-icon-danger" />
            <div>
              <span className="pi-spa-temp">
                {temp.value}
                {temp.unit ? <span>{temp.unit}</span> : null}
              </span>
              <span className="pi-stat-label">Vattentemperatur</span>
            </div>
          </div>
          <div className="pi-spa-row">
            <IconCheckCircle className="pi-icon-grid" />
            <div>
              <span className="pi-stat-label">Filtrering</span>
              <span className="pi-spa-strong">{sectionText(available, spa?.filter_status_sv)}</span>
            </div>
          </div>
          <div className="pi-spa-row">
            <IconCheckCircle className="pi-icon-grid" />
            <div>
              <span className="pi-stat-label">Nästa rengöring</span>
              <span className="pi-spa-strong">{formatDayTime(spa?.next_cleaning_at, timezone)}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="pi-mini-row is-two">
        <div className="pi-mini">
          <span className="pi-mini-label">Förbrukning idag</span>
          <span className="pi-mini-value">
            {consumption.value === MISSING ? MISSING : `${consumption.value} ${consumption.unit}`}
          </span>
        </div>
        <div className="pi-mini">
          <span className="pi-mini-label">Kostnad idag</span>
          <span className="pi-mini-value">
            {cost.value === MISSING ? MISSING : `${cost.value} ${cost.unit}`}
          </span>
        </div>
      </div>
    </PiTouchCard>
  );
}
