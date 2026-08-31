"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "@/components/ThemeToggle";
import { navigateEconomySection } from "@/components/economy-dashboard/economySection";
import { navigateEnergySection } from "@/components/energy-dashboard/energySection";
import { navigateEvSection } from "@/components/ev-dashboard/evSection";
import { navigateSolarSection } from "@/components/solar-dashboard/solarSection";
import { navigateVehicleSection } from "@/components/vehicle-dashboard/vehicleSection";
import { isNavActive, visibleNavItems } from "./navItems";

export function DashboardTopBar({
  slug,
  spaEnabled,
  vehicleEnabled,
}: {
  slug: string;
  spaEnabled?: boolean;
  vehicleEnabled?: boolean;
}) {
  const pathname = usePathname();
  const items = visibleNavItems(spaEnabled, vehicleEnabled);
  const isEnergyRoute = pathname.includes(`/sites/${slug}/energy`);
  const isSolarRoute = pathname.includes(`/sites/${slug}/solar`) && !pathname.includes("/intelligence");
  const isEvRoute = pathname.includes(`/sites/${slug}/ev`);
  const isVehicleRoute = pathname.includes(`/sites/${slug}/vehicle`);
  const isCostsRoute = pathname.includes(`/sites/${slug}/costs`);

  return (
    <header className="idash-topbar">
      <nav className="idash-topbar-nav" aria-label="Sidnavigering">
        {items.map((item) => {
          const active = isNavActive(pathname, slug, item);
          return (
            <Link
              key={item.id}
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
              className={`idash-topbar-link ${active ? "idash-topbar-link-active" : ""}`.trim()}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="idash-topbar-actions">
        <button type="button" className="idash-icon-btn" aria-label="Notiser">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M12 4a5 5 0 0 0-5 5v3l-2 2v1h14v-1l-2-2V9a5 5 0 0 0-5-5zM10 20a2 2 0 0 0 4 0"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
            />
          </svg>
          <span className="idash-notify-badge">3</span>
        </button>
        <ThemeToggle />
        <span className="idash-user-avatar" aria-label="Användare">
          HM
        </span>
      </div>
    </header>
  );
}
