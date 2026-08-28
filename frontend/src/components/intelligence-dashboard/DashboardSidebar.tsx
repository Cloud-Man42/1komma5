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
import type { MarketPricesResponse, SiteDashboard, SolarWeather } from "@/lib/api";
import { fetchMarketPrices } from "@/lib/api";
import { SidebarElectricityPriceCard } from "@/components/intelligence-dashboard/SidebarElectricityPriceCard";
import { DashboardNavIcon, isNavActive, visibleNavItems } from "./navItems";
import { WeatherIcon } from "./weatherIcons";
import {
  VEHICLE_SIDEBAR_NAV,
  isVehicleSidebarNavActive,
} from "@/components/vehicle-dashboard/vehicleSidebarNavItems";
import { navigateVehicleSection } from "@/components/vehicle-dashboard/vehicleSection";
import {
  ECONOMY_SIDEBAR_SUBNAV,
  isEconomySidebarSubnavActive,
} from "@/components/economy-dashboard/economySidebarNavItems";
import { navigateEconomySection } from "@/components/economy-dashboard/economySection";
import {
  ENERGY_SIDEBAR_NAV,
  isEnergySidebarNavActive,
} from "@/components/energy-dashboard/energySidebarNavItems";
import { navigateEnergySection } from "@/components/energy-dashboard/energySection";
import {
  EV_SIDEBAR_NAV,
  isEvSidebarNavActive,
} from "@/components/ev-dashboard/evSidebarNavItems";
import { navigateEvSection } from "@/components/ev-dashboard/evSection";
import {
  SOLAR_SIDEBAR_NAV,
  isSolarSidebarNavActive,
} from "@/components/solar-dashboard/solarSidebarNavItems";
import { navigateSolarSection } from "@/components/solar-dashboard/solarSection";
import { EV_SIDEBAR_PHOTO } from "@/lib/evScenePhoto";

function formatClock(iso: string, timezone: string): string {
  return new Date(iso).toLocaleTimeString("sv-SE", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  });
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
  const [vehicleHash, setVehicleHash] = useState("");
  const [economyHash, setEconomyHash] = useState("");
  const [energyHash, setEnergyHash] = useState("");
  const [evHash, setEvHash] = useState("");
  const [solarHash, setSolarHash] = useState("");
  const [marketPrices, setMarketPrices] = useState<MarketPricesResponse | null>(null);

  useEffect(() => {
    let active = true;
    fetchMarketPrices(slug, 24)
      .then((data) => {
        if (active) setMarketPrices(data);
      })
      .catch(() => {
        if (active) setMarketPrices(null);
      });
    const interval = setInterval(() => {
      fetchMarketPrices(slug, 24)
        .then((data) => {
          if (active) setMarketPrices(data);
        })
        .catch(() => {
          if (active) setMarketPrices(null);
        });
    }, 300_000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [slug]);
  useEffect(() => {
    if (!isVehicleRoute) return;
    const update = () => setVehicleHash(window.location.href.includes("#") ? window.location.href.slice(window.location.href.indexOf("#")) : "");
    update();
    window.addEventListener("hashchange", update);
    window.addEventListener("popstate", update);
    return () => {
      window.removeEventListener("hashchange", update);
      window.removeEventListener("popstate", update);
    };
  }, [isVehicleRoute]);
  useEffect(() => {
    if (!isCostsRoute) return;
    const update = () => setEconomyHash(window.location.href.includes("#") ? window.location.href.slice(window.location.href.indexOf("#")) : "");
    update();
    window.addEventListener("hashchange", update);
    window.addEventListener("popstate", update);
    return () => {
      window.removeEventListener("hashchange", update);
      window.removeEventListener("popstate", update);
    };
  }, [isCostsRoute]);
  useEffect(() => {
    if (!isEnergyRoute) return;
    const update = () => setEnergyHash(window.location.href.includes("#") ? window.location.href.slice(window.location.href.indexOf("#")) : "");
    update();
    window.addEventListener("hashchange", update);
    window.addEventListener("popstate", update);
    return () => {
      window.removeEventListener("hashchange", update);
      window.removeEventListener("popstate", update);
    };
  }, [isEnergyRoute]);
  useEffect(() => {
    if (!isEvRoute) return;
    const update = () => setEvHash(window.location.href.includes("#") ? window.location.href.slice(window.location.href.indexOf("#")) : "");
    update();
    window.addEventListener("hashchange", update);
    window.addEventListener("popstate", update);
    return () => {
      window.removeEventListener("hashchange", update);
      window.removeEventListener("popstate", update);
    };
  }, [isEvRoute]);
  useEffect(() => {
    if (!isSolarRoute) return;
    const update = () => setSolarHash(window.location.href.includes("#") ? window.location.href.slice(window.location.href.indexOf("#")) : "");
    update();
    window.addEventListener("hashchange", update);
    window.addEventListener("popstate", update);
    return () => {
      window.removeEventListener("hashchange", update);
      window.removeEventListener("popstate", update);
    };
  }, [isSolarRoute]);
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

      <SidebarElectricityPriceCard prices={marketPrices} />

      <nav className="idash-sidebar-nav">
        {isVehicleRoute
          ? VEHICLE_SIDEBAR_NAV.map((item) => {
              const active = isVehicleSidebarNavActive(pathname, slug, item, vehicleHash);
              return (
                <Link
                  key={item.id}
                  href={item.href(slug)}
                  onClick={(event) => {
                    event.preventDefault();
                    navigateVehicleSection(slug, item.id);
                  }}
                  className={`idash-sidebar-link ${active ? "idash-sidebar-link-active idash-sidebar-link-active-vehicle" : ""}`.trim()}
                >
                  <span>{item.label}</span>
                </Link>
              );
            })
          : isEnergyRoute
            ? ENERGY_SIDEBAR_NAV.map((item) => {
                const active = isEnergySidebarNavActive(pathname, slug, item, energyHash);
                return (
                  <Link
                    key={item.id}
                    href={item.href(slug)}
                    onClick={(event) => {
                      if (item.id === "overview") return;
                      event.preventDefault();
                      navigateEnergySection(slug, item.id);
                    }}
                    className={`idash-sidebar-link ${active ? "idash-sidebar-link-active idash-sidebar-link-active-energy" : ""}`.trim()}
                  >
                    <span>{item.label}</span>
                  </Link>
                );
              })
            : isEvRoute
              ? EV_SIDEBAR_NAV.map((item) => {
                  const active = isEvSidebarNavActive(pathname, slug, item, evHash);
                  return (
                    <Link
                      key={item.id}
                      href={item.href(slug)}
                      onClick={(event) => {
                        if (item.id === "settings") return;
                        event.preventDefault();
                        navigateEvSection(slug, item.id);
                      }}
                      className={`idash-sidebar-link ${active ? "idash-sidebar-link-active idash-sidebar-link-active-ev" : ""}`.trim()}
                    >
                      <span>{item.label}</span>
                    </Link>
                  );
                })
              : isSolarRoute
                ? SOLAR_SIDEBAR_NAV.map((item) => {
                    const active = isSolarSidebarNavActive(pathname, slug, item, solarHash);
                    return (
                      <Link
                        key={item.id}
                        href={item.href(slug)}
                        onClick={(event) => {
                          event.preventDefault();
                          navigateSolarSection(slug, item.id);
                        }}
                        className={`idash-sidebar-link ${active ? "idash-sidebar-link-active idash-sidebar-link-active-solar" : ""}`.trim()}
                      >
                        <span>{item.label}</span>
                      </Link>
                    );
                  })
                : items.map((item) => {
              const active = isNavActive(pathname, slug, item);
              const isEconomyItem = item.id === "costs" && isCostsRoute;
              return (
                <div key={item.id}>
                  <Link
                    href={item.href(slug)}
                    className={`idash-sidebar-link ${active ? "idash-sidebar-link-active" : ""} ${isEconomyItem ? "idash-sidebar-link-economy-active" : ""}`.trim()}
                  >
                    <NavIcon name={item.id} />
                    <span>{item.label}</span>
                  </Link>
                  {isEconomyItem
                    ? ECONOMY_SIDEBAR_SUBNAV.map((sub) => {
                        const subActive = isEconomySidebarSubnavActive(pathname, slug, sub, economyHash);
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
