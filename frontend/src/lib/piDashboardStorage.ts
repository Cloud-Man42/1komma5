import type { DisplayOverview, PiConnectionState } from "@/lib/displayOverview";

const storageKey = (slug: string) => `emic:pi:lkg:${slug}`;

export function loadPiLastKnownGood(slug: string): DisplayOverview | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(storageKey(slug));
    if (!raw) return null;
    return JSON.parse(raw) as DisplayOverview;
  } catch {
    return null;
  }
}

export function savePiLastKnownGood(slug: string, overview: DisplayOverview): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(storageKey(slug), JSON.stringify(overview));
  } catch {
    // ignore quota errors
  }
}

export function derivePiConnectionState(
  overview: DisplayOverview | null,
  fetchFailed: boolean,
): PiConnectionState {
  if (!overview) return fetchFailed ? "OFFLINE" : "RECONNECTING";
  if (fetchFailed) {
    const age = overview.freshness?.data_age_seconds ?? null;
    return age != null && age <= 900 ? "RECONNECTING" : "OFFLINE";
  }
  return "CONNECTED";
}

export function formatLastUpdated(overview: DisplayOverview | null): string | null {
  if (!overview?.generated_at) return null;
  const date = new Date(overview.generated_at);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
