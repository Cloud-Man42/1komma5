import type { ReactNode } from "react";

export type IconName =
  | "sun"
  | "battery"
  | "house"
  | "grid"
  | "car"
  | "cost"
  | "forecast"
  | "warning"
  | "check";

const paths: Record<IconName, ReactNode> = {
  sun: (
    <circle cx="12" cy="12" r="4" fill="currentColor" />
  ),
  battery: (
    <rect x="4" y="7" width="14" height="10" rx="2" fill="none" stroke="currentColor" strokeWidth="1.5" />
  ),
  house: (
    <path d="M4 11 12 4l8 7v9H4z" fill="none" stroke="currentColor" strokeWidth="1.5" />
  ),
  grid: (
    <path d="M4 8h16M4 16h16M8 4v16M16 4v16" fill="none" stroke="currentColor" strokeWidth="1.5" />
  ),
  car: (
    <path
      d="M5 14h14l-1.5-5H6.5L5 14zm2.5 3a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zm9 0a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    />
  ),
  cost: (
    <path d="M6 6h12v12H6z M9 9h6M9 12h4" fill="none" stroke="currentColor" strokeWidth="1.5" />
  ),
  forecast: (
    <path d="M4 14c2-4 6-6 8-6s6 2 8 6" fill="none" stroke="currentColor" strokeWidth="1.5" />
  ),
  warning: (
    <path d="M12 5 20 19H4z M12 10v4M12 16h.01" fill="none" stroke="currentColor" strokeWidth="1.5" />
  ),
  check: (
    <path d="M5 12l4 4 10-10" fill="none" stroke="currentColor" strokeWidth="1.5" />
  ),
};

export function Icon({ name, className }: { name: IconName; className?: string }) {
  return (
    <svg
      className={className ?? "dashboard-icon"}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      {paths[name]}
    </svg>
  );
}
