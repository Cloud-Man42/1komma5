"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { APP_ACRONYM } from "@/lib/brand";
import { formatRelativeTime } from "@/lib/format";
import { formatSunTime, getSunTimes } from "@/lib/sunTimes";
import { DEFAULT_SCENE_PHOTO } from "@/lib/energyScenePhoto";
import { SPA_SIDEBAR_PHOTO } from "@/lib/spaScenePhoto";
import { VEHICLE_SIDEBAR_PHOTO } from "@/lib/vehicleScenePhoto";
import type { EnergyStrategyCurrent, PricePeriodSnapshot, SiteDashboard, SolarWeather } from "@/lib/api";
import { fetchEnergyStrategyCurrent, fetchPriceEngineToday } from "@/lib/api";
import { SidebarElectricityPriceCard } from "@/components/intelligence-dashboard/SidebarElectricityPriceCard";
import { DashboardNavIcon, isNavActive, visibleNavItems } from "./navItems";
import { WeatherIcon } from "./weatherIcons";
import {
  VEHICLE_SIDEBAR_SUBNAV,
  isVehicleSidebarNavActive,
} from "@/components/vehicle-dashboard/vehicleSidebarNavItems";
import { navigateVehicleSection } from "@/components/vehicle-dashboard/vehicleSection";
import {
  ECONOMY_SIDEBAR_SUBNAV,
  isEconomySidebarSubnavActive,
} from "@/components/economy-dashboard/economySidebarNavItems";
import { navigateEconomySection } from "@/components/economy-dashboard/economySection";
import {
  ENERGY_SIDEBAR_SUBNAV,
  isEnergySidebarNavActive,
} from "@/components/energy-dashboard/energySidebarNavItems";
import { navigateEnergySection } from "@/components/energy-dashboard/energySection";
import {
  EV_SIDEBAR_SUBNAV,
  isEvSidebarNavActive,
} from "@/components/ev-dashboard/evSidebarNavItems";
import { navigateEvSection } from "@/components/ev-dashboard/evSection";
import {
  SOLAR_SIDEBAR_SUBNAV,
  isSolarSidebarNavActive,
} from "@/components/solar-dashboard/solarSidebarNavItems";
import { navigateSolarSection } from "@/components/solar-dashboard/solarSection";
import { readLocationHash, subscribeToHashNavigation } from "@/lib/hashSectionNavigation";
import { EV_SIDEBAR_PHOTO } from "@/lib/evScenePhoto";

function formatClock(iso: string, timezone: string): string {
  return new Date(iso).toLocaleTimeString("sv-SE", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  });
}

function sectionAccentClass(itemId: DashboardNavIcon): string {
  switch (itemId) {
    case "energy":
      return "idash-sidebar-link-active-energy";
    case "solar":
      return "idash-sidebar-link-active-solar";
    case "ev":
      return "idash-sidebar-link-active-ev";
    case "vehicle":
      return "idash-sidebar-link-active-vehicle";
    case "costs":
      return "idash-sidebar-link-economy-active";
    default:
      return "";
  }
}

function NavIcon({ name }: { name: DashboardNavIcon }) {
  const paths: Record<DashboardNavIcon, ReactNode> = {
    overview: (
      <path d="M4 10.5 12 4l8 6.5V20H4z" fill="none" stroke="currentColor" strokeWidth="1.6" />
    ),
    energy: (
      <path d="M12 3v18M8 7l4-4 4 4M8 17l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.6" />
    ),
    solar: (
      <>
        <circle cx="12" cy="12" r="4" fill="currentColor" />
        <path d="M12 2v2M12 20v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M2 12h2M20 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4" stroke="currentColor" strokeWidth="1.4" />
      </>
    ),
    ev: (
      <path
        d="M5 14h14l-1.5-5H6.5L5 14zm2.5 3a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zm9 0a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
      />
    ),
    costs: (
      <path d="M6 6h12v12H6zM9 9h6M9 12h4" fill="none" stroke="currentColor" strokeWidth="1.6" />
    ),
    diagnostics: (
      <path d="M12 4v4M12 16v4M4 12h4M16 12h4" fill="none" stroke="currentColor" strokeWidth="1.6" />
    ),
    spa: (
      <path d="M4 14c2-6 5-8 8-8s6 2 8 8" fill="none" stroke="currentColor" strokeWidth="1.6" />
    ),
    vehicle: (
      <path
        d="M5 14h14l-1.5-5H6.5L5 14z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
      />
    ),
    settings: (
      <path
        d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zm8.5 4a7.5 7.5 0 0 0-.2-1.7l2-1.5-2-3.5-2.3 1a7.6 7.6 0 0 0-2.9-1.7L14.5 2h-5l-.6 2.6a7.6 7.6 0 0 0-2.9 1.7l-2.3-1-2 3.5 2 1.5a7.5 7.5 0 0 0 0 3.4l-2 1.5 2 3.5 2.3-1a7.6 7.6 0 0 0 2.9 1.7L9.5 22h5l.6-2.6a7.6 7.6 0 0 0 2.9-1.7l2.3 1 2-3.5-2-1.5c.1-.55.2-1.12.2-1.7z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.2"
      />
    ),
  };

  return (
    <svg className="idash-nav-icon" viewBox="0 0 24 24" aria-hidden="true">
      {paths[name]}
    </svg>
  );
}

export function DashboardSidebar({
  slug,
  dashboard,
  latitude,
  longitude,
  weather,
}: {
  slug: string;
  dashboard: SiteDashboard | null;
  latitude?: number | null;
  longitude?: number | null;
  weather?: SolarWeather | null;
}) {
  const pathname = usePathname();
  const items = visibleNavItems(
    dashboard?.spa_integration_enabled,
    dashboard?.vehicle_integration_enabled,
  );

  const siteName = dashboard?.site.name ?? slug;
  const timezone = dashboard?.site.timezone ?? "Europe/Stockholm";
  const lat = latitude ?? 55.60;
  const lon = longitude ?? 13.004;
  const fallbackSun = getSunTimes(lat, lon);
  const sunriseText = weather?.sunrise
    ? formatClock(weather.sunrise, timezone)
    : formatSunTime(fallbackSun.sunrise, timezone);
  const sunsetText = weather?.sunset
    ? formatClock(weather.sunset, timezone)
    : formatSunTime(fallbackSun.sunset, timezone);
  const statusOk = dashboard ? dashboard.alerts.length === 0 && !dashboard.freshness.stale : true;
  const isSpaRoute = pathname.includes(`/sites/${slug}/spa`);
  const isVehicleRoute = pathname.includes(`/sites/${slug}/vehicle`);
  const isCostsRoute = pathname.includes(`/sites/${slug}/costs`);
  const isEnergyRoute = pathname.includes(`/sites/${slug}/energy`);
  const isEvRoute = pathname.includes(`/sites/${slug}/ev`);
  const isSolarRoute = pathname.includes(`/sites/${slug}/solar`) && !pathname.includes("/intelligence");
  const usesHashSubnav =
    isEnergyRoute || isEvRoute || isSolarRoute || isVehicleRoute || isCostsRoute;
  const [locationHash, setLocationHash] = useState("");
  const [importPeriods, setImportPeriods] = useState<PricePeriodSnapshot[] | null>(null);
  const [energyStrategy, setEnergyStrategy] = useState<EnergyStrategyCurrent | null>(null);

  useEffect(() => {
    let active = true;
    const load = () => {
      fetchPriceEngineToday(slug)
        .then((data) => {
          if (active) setImportPeriods(data.periods);
        })
        .catch(() => {
          if (active) setImportPeriods(null);
        });
      fetchEnergyStrategyCurrent(slug)
        .then((data) => {
          if (active) setEnergyStrategy(data);
        })
        .catch(() => {
          if (active) setEnergyStrategy(null);
        });
    };
    load();
    const interval = setInterval(load, 300_000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [slug, timezone]);
  useEffect(() => {
    if (!usesHashSubnav) {
      setLocationHash("");
      return;
    }
    const update = () => setLocationHash(readLocationHash());
    update();
    return subscribeToHashNavigation(update);
  }, [usesHashSubnav]);
  const locationPhoto = isSpaRoute
    ? SPA_SIDEBAR_PHOTO
    : isVehicleRoute
      ? VEHICLE_SIDEBAR_PHOTO
      : isEvRoute
        ? EV_SIDEBAR_PHOTO
        : DEFAULT_SCENE_PHOTO;
  const sceneClass = isSpaRoute ? "is-spa-scene" : isVehicleRoute ? "is-vehicle-scene" : isEvRoute ? "is-ev-scene" : "";
  const evOnline = dashboard?.ev?.available !== false;

  return (
    <aside className="idash-sidebar" aria-label="Huvudnavigering">
      <div className="idash-sidebar-brand">
        <span className="idash-brand-mark">{APP_ACRONYM}</span>
        <span className="idash-brand-sub">ENERGY INTELLIGENCE</span>
      </div>

      <div className="idash-location-card">
        <div className={`idash-location-photo-wrap ${sceneClass}`.trim()}>
          <img src={locationPhoto} alt="" className="idash-location-photo" />
          <div className="idash-location-overlay">
            <div className="idash-location-top">
              <strong>{siteName.toUpperCase()}</strong>
              {!isVehicleRoute ? <span className="idash-live-badge">● LIVE</span> : null}
            </div>
            <p className="idash-location-coords">
              {isVehicleRoute ? timezone : `${timezone} | ${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E`}
            </p>
            {isVehicleRoute ? (
              <div className="idash-vehicle-weather">
                <div className="idash-location-weather">
                  <WeatherIcon icon={weather?.current?.condition_icon} size={20} />
                  <span className="idash-weather-temp">
                    {weather?.current?.temperature_c != null
                      ? `${weather.current.temperature_c.toLocaleString("sv-SE", { maximumFractionDigits: 0 })}°C`
                      : "18°C"}{" "}
                    {weather?.current?.condition_sv ?? "Klart"}
                  </span>
                </div>
                <span className="idash-vehicle-wind">
                  <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
                    <path d="M4 10h12a3 3 0 1 0-3-3M4 14h14a4 4 0 1 1-4 4" fill="none" stroke="currentColor" strokeWidth="1.4" />
                  </svg>
                  {weather?.current?.wind_speed_ms != null
                    ? `${weather.current.wind_speed_ms.toFixed(1)} m/s`
                    : "2.1 m/s"}{" "}
                  Vind
                </span>
              </div>
            ) : (
              <>
                <div className="idash-location-weather">
                  <WeatherIcon icon={weather?.current?.condition_icon} size={20} />
                  <span className="idash-weather-temp">
                    {weather?.current?.temperature_c != null
                      ? `${weather.current.temperature_c.toLocaleString("sv-SE", { maximumFractionDigits: 0 })}°C`
                      : "—"}{" "}
                    {weather?.current?.condition_sv ?? ""}
                  </span>
                </div>
                <div className="idash-location-sun">
                  <span>Soluppgång {sunriseText}</span>
                  <span>Solnedgång {sunsetText}</span>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      <SidebarElectricityPriceCard periods={importPeriods} timezone={timezone} strategy={energyStrategy} />

      <nav className="idash-sidebar-nav">
        {items.map((item) => {
          const active = isNavActive(pathname, slug, item);
          const accentClass = sectionAccentClass(item.id);
          const showSubnav =
            (item.id === "costs" && isCostsRoute) ||
            (item.id === "energy" && isEnergyRoute) ||
            (item.id === "solar" && isSolarRoute) ||
            (item.id === "ev" && isEvRoute) ||
            (item.id === "vehicle" && isVehicleRoute);

          return (
            <div key={item.id}>
              <Link
                href={item.href(slug)}
                onClick={(event) => {
                  if (item.id === "energy" && isEnergyRoute) {
                    event.preventDefault();
                    navigateEnergySection(slug, "flow");
                    return;
                  }
                  if (item.id === "solar" && isSolarRoute) {
                    event.preventDefault();
                    navigateSolarSection(slug, "overview");
                    return;
                  }
                  if (item.id === "ev" && isEvRoute) {
                    event.preventDefault();
                    navigateEvSection(slug, "overview");
                    return;
                  }
                  if (item.id === "vehicle" && isVehicleRoute) {
                    event.preventDefault();
                    navigateVehicleSection(slug, "overview");
                    return;
                  }
                  if (item.id === "costs" && isCostsRoute) {
                    event.preventDefault();
                    navigateEconomySection(slug, "analysis");
                  }
                }}
                className={`idash-sidebar-link ${active ? "idash-sidebar-link-active" : ""} ${showSubnav && accentClass ? accentClass : ""}`.trim()}
              >
                <NavIcon name={item.id} />
                <span>{item.label}</span>
              </Link>
              {showSubnav && item.id === "costs"
                ? ECONOMY_SIDEBAR_SUBNAV.map((sub) => {
                    const subActive = isEconomySidebarSubnavActive(pathname, slug, sub, locationHash);
                    return (
                      <Link
                        key={sub.id}
                        href={sub.href(slug)}
                        onClick={(event) => {
                          event.preventDefault();
                          navigateEconomySection(slug, sub.id);
                        }}
                        className={`idash-sidebar-link idash-sidebar-link-subnav ${subActive ? "idash-sidebar-link-subnav-active" : ""}`.trim()}
                      >
                        <span>{sub.label}</span>
                      </Link>
                    );
                  })
                : null}
              {showSubnav && item.id === "energy"
                ? ENERGY_SIDEBAR_SUBNAV.map((sub) => {
                    const subActive = isEnergySidebarNavActive(pathname, slug, sub, locationHash);
                    return (
                      <Link
                        key={sub.id}
                        href={sub.href(slug)}
                        onClick={(event) => {
                          event.preventDefault();
                          navigateEnergySection(slug, sub.id);
                        }}
                        className={`idash-sidebar-link idash-sidebar-link-subnav ${subActive ? `idash-sidebar-link-subnav-active ${accentClass}`.trim() : ""}`.trim()}
                      >
                        <span>{sub.label}</span>
                      </Link>
                    );
                  })
                : null}
              {showSubnav && item.id === "solar"
                ? SOLAR_SIDEBAR_SUBNAV.map((sub) => {
                    const subActive = isSolarSidebarNavActive(pathname, slug, sub, locationHash);
                    return (
                      <Link
                        key={sub.id}
                        href={sub.href(slug)}
                        onClick={(event) => {
                          event.preventDefault();
                          navigateSolarSection(slug, sub.id);
                        }}
                        className={`idash-sidebar-link idash-sidebar-link-subnav ${subActive ? `idash-sidebar-link-subnav-active ${accentClass}`.trim() : ""}`.trim()}
                      >
                        <span>{sub.label}</span>
                      </Link>
                    );
                  })
                : null}
              {showSubnav && item.id === "ev"
                ? EV_SIDEBAR_SUBNAV.map((sub) => {
                    const subActive = isEvSidebarNavActive(pathname, slug, sub, locationHash);
                    return (
                      <Link
                        key={sub.id}
                        href={sub.href(slug)}
                        onClick={(event) => {
                          event.preventDefault();
                          navigateEvSection(slug, sub.id);
                        }}
                        className={`idash-sidebar-link idash-sidebar-link-subnav ${subActive ? `idash-sidebar-link-subnav-active ${accentClass}`.trim() : ""}`.trim()}
                      >
                        <span>{sub.label}</span>
                      </Link>
                    );
                  })
                : null}
              {showSubnav && item.id === "vehicle"
                ? VEHICLE_SIDEBAR_SUBNAV.map((sub) => {
                    const subActive = isVehicleSidebarNavActive(pathname, slug, sub, locationHash);
                    return (
                      <Link
                        key={sub.id}
                        href={sub.href(slug)}
                        onClick={(event) => {
                          event.preventDefault();
                          navigateVehicleSection(slug, sub.id);
                        }}
                        className={`idash-sidebar-link idash-sidebar-link-subnav ${subActive ? `idash-sidebar-link-subnav-active ${accentClass}`.trim() : ""}`.trim()}
                      >
                        <span>{sub.label}</span>
                      </Link>
                    );
                  })
                : null}
            </div>
          );
        })}
      </nav>

      {isEvRoute ? (
        <div className="idash-ev-online-badge" data-testid="ev-sidebar-online">
          <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
            <path d="M9 12l2 2 4-4M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z" fill="none" stroke="currentColor" strokeWidth="1.6" />
          </svg>
          {evOnline ? "Laddbox online" : "Laddbox offline"}
        </div>
      ) : null}

      {isEnergyRoute ? (
        <div className="idash-energy-plant-ok" data-testid="energy-plant-ok">
          <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
            <path d="M9 12l2 2 4-4M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z" fill="none" stroke="currentColor" strokeWidth="1.6" />
          </svg>
          Anläggning OK
        </div>
      ) : null}

      {isSolarRoute ? (
        <div className="idash-energy-plant-ok" data-testid="solar-plant-ok">
          <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
            <path d="M9 12l2 2 4-4M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z" fill="none" stroke="currentColor" strokeWidth="1.6" />
          </svg>
          Anläggning OK
        </div>
      ) : null}

      <div className="idash-system-status">
        <p className="idash-system-status-label">SYSTEMSTATUS</p>
        <div className="idash-system-status-body">
          <span className={`idash-pulse-icon ${statusOk ? "idash-pulse-icon-ok" : "idash-pulse-icon-warn"}`}>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="M3 12h3l2-5 4 10 3-6 2 4h4"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.6"
              />
            </svg>
          </span>
          <div>
            <strong>{statusOk ? "Allt normalt" : "Behöver uppmärksamhet"}</strong>
            <p className="idash-system-status-meta">
              Senast uppdaterad{" "}
              {dashboard?.freshness.updated_at
                ? formatRelativeTime(dashboard.freshness.updated_at)
                : "—"}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
