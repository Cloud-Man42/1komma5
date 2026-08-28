import type { ReactNode } from "react";

export type WeatherIconKey =
  | "clear"
  | "mostly-clear"
  | "partly-cloudy"
  | "overcast"
  | "fog"
  | "drizzle"
  | "rain"
  | "showers"
  | "snow"
  | "thunder"
  | "unknown";

const SUN = (
  <>
    <circle cx="12" cy="12" r="4.2" fill="currentColor" />
    <path
      d="M12 2.5v2.2M12 19.3v2.2M4.6 4.6l1.6 1.6M17.8 17.8l1.6 1.6M2.5 12h2.2M19.3 12h2.2M4.6 19.4l1.6-1.6M17.8 6.2l1.6-1.6"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
    />
  </>
);

const CLOUD = (
  <path
    d="M7 17.5h9.5a3.5 3.5 0 0 0 .3-7 5 5 0 0 0-9.6-1.2A3.9 3.9 0 0 0 7 17.5z"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.6"
    strokeLinejoin="round"
  />
);

const ICONS: Record<WeatherIconKey, ReactNode> = {
  clear: SUN,
  "mostly-clear": (
    <>
      <circle cx="10" cy="10" r="3.4" fill="currentColor" />
      <path d="M10 4.2v1.8M4.6 10H2.8M5.7 5.7 4.4 4.4M14.3 5.7l1.3-1.3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <path
        d="M9 18.5h8a3 3 0 0 0 .2-6 4.3 4.3 0 0 0-8.2-1 3.4 3.4 0 0 0 0 7z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
    </>
  ),
  "partly-cloudy": (
    <>
      <circle cx="9.5" cy="9" r="3.1" fill="currentColor" opacity="0.9" />
      <path
        d="M9 18.5h8a3 3 0 0 0 .2-6 4.3 4.3 0 0 0-8.2-1 3.4 3.4 0 0 0 0 7z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </>
  ),
  overcast: CLOUD,
  fog: (
    <>
      {CLOUD}
      <path d="M5 20h14M7 22h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </>
  ),
  drizzle: (
    <>
      {CLOUD}
      <path d="M9 19.5v1.6M13 19.5v1.6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </>
  ),
  rain: (
    <>
      {CLOUD}
      <path d="M8.5 19.2v2.4M12 19.2v2.4M15.5 19.2v2.4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </>
  ),
  showers: (
    <>
      {CLOUD}
      <path d="M9 19.2 8 22M13 19.2 12 22M17 19.2 16 22" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </>
  ),
  snow: (
    <>
      {CLOUD}
      <path
        d="M9 20.6h.01M12.5 21.4h.01M16 20.6h.01"
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
      />
    </>
  ),
  thunder: (
    <>
      {CLOUD}
      <path d="M12.5 19 10 22.5h2.2l-.7 2.5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    </>
  ),
  unknown: (
    <path
      d="M12 16.5v.01M9.5 9.2a2.6 2.6 0 1 1 3.6 2.4c-.7.3-1.1.9-1.1 1.7v.4"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
    />
  ),
};

const ICON_TONES: Record<WeatherIconKey, string> = {
  clear: "#fbbf24",
  "mostly-clear": "#fcd34d",
  "partly-cloudy": "#cbd5e1",
  overcast: "#94a3b8",
  fog: "#94a3b8",
  drizzle: "#7dd3fc",
  rain: "#38bdf8",
  showers: "#38bdf8",
  snow: "#e0f2fe",
  thunder: "#a78bfa",
  unknown: "#64748b",
};

export function normalizeIconKey(key: string | null | undefined): WeatherIconKey {
  if (key && key in ICONS) return key as WeatherIconKey;
  return "unknown";
}

export function WeatherIcon({
  icon,
  size = 28,
  className,
}: {
  icon: string | null | undefined;
  size?: number;
  className?: string;
}) {
  const key = normalizeIconKey(icon);
  return (
    <svg
      className={className ?? "idash-weather-icon"}
      width={size}
      height={size}
      viewBox="0 0 24 26"
      style={{ color: ICON_TONES[key] }}
      aria-hidden="true"
    >
      {ICONS[key]}
    </svg>
  );
}
