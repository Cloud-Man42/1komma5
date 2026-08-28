/** Approximate sunrise/sunset for a location (NOAA-style, UTC-based). */

function toRad(deg: number): number {
  return (deg * Math.PI) / 180;
}

function toDeg(rad: number): number {
  return (rad * 180) / Math.PI;
}

function dayOfYear(date: Date): number {
  const start = Date.UTC(date.getFullYear(), 0, 0);
  const diff = Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()) - start;
  return Math.floor(diff / 86_400_000);
}

function calcSunEvent(
  lat: number,
  lon: number,
  date: Date,
  sunrise: boolean,
): Date | null {
  const zenith = 90.833;
  const n = dayOfYear(date);
  const lngHour = lon / 15;
  const t = sunrise ? n + (6 - lngHour) / 24 : n + (18 - lngHour) / 24;
  const m = 0.9856 * t - 3.289;
  let l =
    m +
    1.916 * Math.sin(toRad(m)) +
    0.02 * Math.sin(toRad(2 * m)) +
    282.634;
  l = ((l % 360) + 360) % 360;
  let ra = toDeg(Math.atan(0.91764 * Math.tan(toRad(l))));
  ra = ((ra % 360) + 360) % 360;
  const lQuadrant = Math.floor(l / 90) * 90;
  const raQuadrant = Math.floor(ra / 90) * 90;
  ra = ra + (lQuadrant - raQuadrant);
  ra /= 15;
  const sinDec = 0.39782 * Math.sin(toRad(l));
  const cosDec = Math.cos(Math.asin(sinDec));
  const cosH =
    (Math.cos(toRad(zenith)) - sinDec * Math.sin(toRad(lat))) /
    (cosDec * Math.cos(toRad(lat)));
  if (cosH > 1 || cosH < -1) return null;
  let h = sunrise ? 360 - toDeg(Math.acos(cosH)) : toDeg(Math.acos(cosH));
  h /= 15;
  const tm = h + ra - 0.06571 * t - 6.622;
  let ut = tm - lngHour;
  ut = ((ut % 24) + 24) % 24;
  const hours = Math.floor(ut);
  const minutes = Math.round((ut - hours) * 60);
  return new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate(), hours, minutes));
}

export function getSunTimes(
  lat: number,
  lon: number,
  date = new Date(),
): { sunrise: Date | null; sunset: Date | null } {
  return {
    sunrise: calcSunEvent(lat, lon, date, true),
    sunset: calcSunEvent(lat, lon, date, false),
  };
}

export function formatSunTime(iso: Date | null, timezone: string): string {
  if (!iso) return "—";
  return iso.toLocaleTimeString("sv-SE", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  });
}
