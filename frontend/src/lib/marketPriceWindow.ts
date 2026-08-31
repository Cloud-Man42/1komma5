/** Query window helpers for Heartbeat market price charts. */

export function localHourFraction(now: Date, timezone: string): number {
  const parts = new Intl.DateTimeFormat("sv-SE", {
    timeZone: timezone,
    hour: "numeric",
    minute: "numeric",
    hour12: false,
  }).formatToParts(now);
  const hour = Number(parts.find((p) => p.type === "hour")?.value ?? 0);
  const minute = Number(parts.find((p) => p.type === "minute")?.value ?? 0);
  return hour + minute / 60;
}

/** Full local calendar day (+/- 1h buffer) for intraday price curves. */
export function intradayMarketPriceWindow(
  now = new Date(),
  timezone = "Europe/Stockholm",
): { from: Date; to: Date } {
  const hour = localHourFraction(now, timezone);
  const msSinceMidnight = hour * 60 * 60 * 1000;
  const msUntilEnd = (24 - hour) * 60 * 60 * 1000;
  const bufferMs = 60 * 60 * 1000;
  return {
    from: new Date(now.getTime() - msSinceMidnight - bufferMs),
    to: new Date(now.getTime() + msUntilEnd + bufferMs),
  };
}
