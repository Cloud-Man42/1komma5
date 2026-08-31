/**
 * Inline stroke icons for the Pi kiosk dashboard.
 *
 * Kept local (no icon dependency) so the kiosk bundle stays small and the
 * stroke weights can be tuned to the reference mockup.
 */

type IconProps = { className?: string };

export type PiIcon = (props: IconProps) => React.ReactElement;

const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.9,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

export function IconHome({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M3 10.5 12 3.5l9 7" />
      <path d="M5.5 9.5V20h13V9.5" />
      <path d="M9.75 20v-5.5h4.5V20" />
    </svg>
  );
}

/** Discreet touch affordance on navigable cards. */
export function IconChevron({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M9.5 6.5 14.5 12l-5 5.5" />
    </svg>
  );
}

export function IconBolt({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M13.5 2.5 5 13.5h5.5L9.5 21.5 18.5 10h-5.5z" />
    </svg>
  );
}

export function IconSun({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <circle cx="12" cy="12" r="4.2" />
      <path d="M12 2.4v2.3M12 19.3v2.3M2.4 12h2.3M19.3 12h2.3M5.2 5.2l1.6 1.6M17.2 17.2l1.6 1.6M18.8 5.2l-1.6 1.6M6.8 17.2l-1.6 1.6" />
    </svg>
  );
}

export function IconBattery({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <rect x="6.5" y="3.5" width="11" height="17" rx="2.6" />
      <path d="M10 3.5V2h4v1.5" />
      <rect x="9" y="9" width="6" height="9" rx="1" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function IconBatteryCharging({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <rect x="6.5" y="3.5" width="11" height="17" rx="2.6" />
      <path d="M10 3.5V2h4v1.5" />
      <path d="M13.2 8 10 13h2.4l-1 4 3.4-5.2h-2.3z" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function IconPylon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M5 21 8.5 3h7L19 21" />
      <path d="M7.4 13h9.2M6.5 17h11M8.9 8.5h6.2" />
      <path d="M9 8.5 15 17M15 8.5 9 17" strokeWidth="1.3" />
    </svg>
  );
}

export function IconPlug({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M9 2.5v5M15 2.5v5" />
      <path d="M6.5 7.5h11v3.2a5.5 5.5 0 0 1-5.5 5.5 5.5 5.5 0 0 1-5.5-5.5z" />
      <path d="M12 16.2v5.3" />
    </svg>
  );
}

export function IconCar({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M3 15.5h18M4.5 15.5l1.6-5.3A2.5 2.5 0 0 1 8.5 8.5h7a2.5 2.5 0 0 1 2.4 1.7l1.6 5.3" />
      <path d="M3 15.5v3h2.6M21 15.5v3h-2.6" />
      <circle cx="7" cy="18.5" r="1.7" />
      <circle cx="17" cy="18.5" r="1.7" />
    </svg>
  );
}

export function IconSpa({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M3 13.5h18v3a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4z" />
      <path d="M7.5 10.5c0-1.6 1.4-1.9 1.4-3.2 0-1-.7-1.6-1.4-2" />
      <path d="M12 10.5c0-1.6 1.4-1.9 1.4-3.2 0-1-.7-1.6-1.4-2" />
      <path d="M16.5 10.5c0-1.6 1.4-1.9 1.4-3.2 0-1-.7-1.6-1.4-2" />
    </svg>
  );
}

export function IconMoney({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 6.8v10.4" />
      <path d="M14.7 9.3c-.5-.9-1.5-1.3-2.7-1.3-1.5 0-2.6.8-2.6 2s1 1.7 2.6 2.1c1.7.4 2.8.9 2.8 2.2s-1.2 2-2.8 2c-1.3 0-2.3-.5-2.8-1.4" />
    </svg>
  );
}

export function IconSettings({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <circle cx="12" cy="12" r="2.9" />
      <path d="M19.4 14.2a7.9 7.9 0 0 0 0-4.4l1.8-1.3-2-3.4-2.1.9a7.8 7.8 0 0 0-3.8-2.2L12.9 1.6h-3.9l-.4 2.2a7.8 7.8 0 0 0-3.8 2.2l-2.1-.9-2 3.4 1.8 1.3a7.9 7.9 0 0 0 0 4.4L.7 15.5l2 3.4 2.1-.9a7.8 7.8 0 0 0 3.8 2.2l.4 2.2h3.9l.4-2.2a7.8 7.8 0 0 0 3.8-2.2l2.1.9 2-3.4z" />
    </svg>
  );
}

export function IconThermometer({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M10 13.6V5a2 2 0 0 1 4 0v8.6a4.2 4.2 0 1 1-4 0z" />
      <circle cx="12" cy="17.5" r="1.6" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function IconDroplet({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M12 2.8c3.4 4 6 6.9 6 10a6 6 0 0 1-12 0c0-3.1 2.6-6 6-10z" />
    </svg>
  );
}

export function IconClock({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5.4l3.6 2.2" />
    </svg>
  );
}

export function IconLeaf({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M4 20c0-8 5-13 16-14 1 10-4 15-11 15-2.4 0-5-.4-5-1z" />
      <path d="M5.5 18.5C9 15 12.5 12.6 17 11" />
    </svg>
  );
}

export function IconUpload({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M12 20V5.5" />
      <path d="M6.5 11 12 5.2 17.5 11" />
      <path d="M4 20.5h16" />
    </svg>
  );
}

export function IconShieldHeart({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M12 2.6 4.5 5.4v6c0 4.4 3.1 8.4 7.5 10 4.4-1.6 7.5-5.6 7.5-10v-6z" />
      <path d="M12 15.4c-1.6-1.2-3.2-2.4-3.2-4a1.8 1.8 0 0 1 3.2-1.1 1.8 1.8 0 0 1 3.2 1.1c0 1.6-1.6 2.8-3.2 4z" />
    </svg>
  );
}

export function IconRecycle({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M8.4 4.9 6 9.1l-3.2-.6" />
      <path d="M2.8 8.5 5.6 4A2.4 2.4 0 0 1 9.8 4l1.5 2.6" />
      <path d="M19.6 10.4l1 3.2 3.1-.1" />
      <path d="M14.4 5.4l3 .1a2.4 2.4 0 0 1 2 3.6l-1.4 2.4" />
      <path d="M9.6 20.6l-2.4-2.2 1.8-2.6" />
      <path d="M17.4 15.2 15.6 18a2.4 2.4 0 0 1-2 1.2H9.6" />
    </svg>
  );
}

export function IconTrendUp({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M3 18l5.5-6 3.5 3L20.5 6" />
      <path d="M15.5 6h5v5" />
    </svg>
  );
}

export function IconPiggy({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M3.5 12.8A5.3 5.3 0 0 1 8.8 7.5h5.4a5.3 5.3 0 0 1 5.3 5.3v1.9a4 4 0 0 1-4 4H7.5a4 4 0 0 1-4-4z" />
      <path d="M6.5 18.7v2M17 18.7v2" />
      <path d="M14.2 7.5 16 4.8" />
      <circle cx="16.4" cy="12.4" r="1" fill="currentColor" stroke="none" />
      <path d="M3.6 12.2H2" />
    </svg>
  );
}

export function IconTag({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M11.2 2.9H20a1.1 1.1 0 0 1 1.1 1.1v8.8a1 1 0 0 1-.3.7l-8 8a1.1 1.1 0 0 1-1.6 0L2.5 13.8a1.1 1.1 0 0 1 0-1.6l8-8a1 1 0 0 1 .7-.3z" />
      <circle cx="16.6" cy="7.4" r="1.5" />
    </svg>
  );
}

export function IconWallet({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <rect x="2.8" y="5.6" width="18.4" height="13" rx="2.4" />
      <path d="M2.8 10.2h18.4" />
      <circle cx="17" cy="14.4" r="1.2" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function IconCloudSun({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <circle cx="8" cy="7.4" r="3" />
      <path d="M8 1.9v1.3M2.6 7.4H1.3M3.9 3.3 3 2.4M12.1 3.3l.9-.9M8 12.9v-1.3" />
      <path d="M10.6 20.6h7.6a3.2 3.2 0 0 0 .3-6.4 4.6 4.6 0 0 0-8.7-1 3.7 3.7 0 0 0 .8 7.4z" />
    </svg>
  );
}

export function IconCheckCircle({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <circle cx="12" cy="12" r="9" />
      <path d="M8.2 12.3l2.6 2.6 5-5.4" />
    </svg>
  );
}

export function IconAlertCircle({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7.6v5.2M12 16.3v.2" />
    </svg>
  );
}

export function IconBrand({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
      <path
        d="M12 1.6 22.4 12 12 22.4 1.6 12z"
        fill="currentColor"
        fillOpacity="0.18"
        stroke="currentColor"
        strokeWidth="1.6"
      />
      <path d="M13.1 6.2 8.2 12.9h3.3l-.7 4.9 4.9-6.9h-3.2z" fill="currentColor" />
    </svg>
  );
}

/** Heartbeat trace used by the sidebar system-status block. */
export function IconPulseLine({ className }: IconProps) {
  return (
    <svg viewBox="0 0 44 16" fill="none" className={className} aria-hidden preserveAspectRatio="none">
      <path
        d="M0 8.5h7l2.4-5.6 3 11L16 4.6l2.2 3.9h5.4l2.3-6 3 10.6 2.6-8.5 2 4h8.5"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
