import { toOrePerKwh } from "@/lib/prices";

export function formatPct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  return `${Math.round(value)} %`;
}

export function formatSekKwh(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  return `${value.toFixed(2)} kr/kWh`;
}

export function formatSek(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  return `${value.toFixed(2)} kr`;
}

export function formatConfidence(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  return `${Math.round(value * 100)} %`;
}

export function formatOre(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return "—";
  }
  return `${Math.round(toOrePerKwh(value))} öre/kWh`;
}

export function formatTime(iso: string | null | undefined, timezone: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString("sv-SE", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  });
}

export function formatTimeWindow(
  start: string | null | undefined,
  end: string | null | undefined,
  timezone: string,
): string {
  if (!start || !end) {
    return "Inget fönster";
  }
  return `${formatTime(start, timezone)}–${formatTime(end, timezone)}`;
}

export function loadTypeLabelSv(loadType: string): string {
  switch (loadType.toLowerCase()) {
    case "ev":
      return "Fordon";
    case "spa":
      return "Spa";
    case "battery":
      return "Batteri";
    default:
      return loadType.toUpperCase();
  }
}

export function energySourceLabelSv(source: string | null | undefined): string | null {
  if (!source) return null;
  switch (source.toUpperCase()) {
    case "SOLAR":
      return "Sol";
    case "GRID":
      return "Nät";
    case "BATTERY":
      return "Batteri";
    default:
      return source;
  }
}

export function batteryActionLabel(action: string | null | undefined, fallback: string): string {
  if (!action) return fallback;
  switch (action) {
    case "STORE_IN_BATTERY":
      return "SPARA I BATTERIET";
    case "DISCHARGE_BATTERY":
      return "URLADDA BATTERI";
    case "HOLD_RESERVE":
      return "HÅLL RESERV";
    default:
      return action.replaceAll("_", " ");
  }
}
