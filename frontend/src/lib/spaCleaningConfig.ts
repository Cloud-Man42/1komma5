/** Client-side Arctic Spa filter policy validation (mirrors backend SpaFilterPolicy). */

export function allowedWindowHours(start: string, end: string): number {
  const [sh, sm] = start.split(":").map(Number);
  const [eh, em] = end.split(":").map(Number);
  let startMinutes = sh * 60 + sm;
  let endMinutes = eh * 60 + em;
  if (endMinutes <= startMinutes) endMinutes += 24 * 60;
  return (endMinutes - startMinutes) / 60;
}

export type SpaFilterConfig = {
  filter_cycles_per_day: number;
  filter_duration_minutes: number;
  minimum_cycle_separation_minutes: number;
  allowed_window_start: string;
  allowed_window_end: string;
  min_cleaning_hours_per_day?: number;
  min_run_minutes?: number;
  min_stop_minutes?: number;
  max_starts_per_day?: number;
};

export function totalDailyRuntimeHours(config: SpaFilterConfig): number {
  return (config.filter_cycles_per_day * config.filter_duration_minutes) / 60;
}

export function validateFilterPolicyClient(config: SpaFilterConfig): string | null {
  const windowHours = allowedWindowHours(config.allowed_window_start, config.allowed_window_end);
  const cycleHours = config.filter_duration_minutes / 60;
  if (cycleHours > windowHours) {
    return `Varje filtercykel (${config.filter_duration_minutes} min) är längre än tidsfönstret.`;
  }
  const separationHours = config.minimum_cycle_separation_minutes / 60;
  const minSpan =
    config.filter_cycles_per_day * cycleHours +
    Math.max(0, config.filter_cycles_per_day - 1) * separationHours;
  if (minSpan > windowHours + 1e-9) {
    return `${config.filter_cycles_per_day} cykler à ${config.filter_duration_minutes} min får inte placeras inom ${windowHours} h.`;
  }
  return null;
}

export function buildFilterSummaryClient(config: SpaFilterConfig): string {
  const total = totalDailyRuntimeHours(config);
  const cycleH = Math.floor(config.filter_duration_minutes / 60);
  return (
    `Arctic Spa grundschema: ${config.filter_cycles_per_day} cykler per dygn, ` +
    `${cycleH} h per cykel (${total} h totalt) mellan ${config.allowed_window_start} och ${config.allowed_window_end}.`
  );
}

/** @deprecated use validateFilterPolicyClient */
export function validateCleaningConfigClient(config: SpaFilterConfig): string | null {
  return validateFilterPolicyClient(config);
}

/** @deprecated use buildFilterSummaryClient */
export function buildCleaningSummaryClient(config: SpaFilterConfig): string {
  return buildFilterSummaryClient(config);
}

export function formatCleaningDuration(hours: number): string {
  const totalMinutes = Math.round(hours * 60);
  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  if (h === 0) return `${m} min`;
  if (m === 0) return `${h} h`;
  return `${h} h ${m} min`;
}

export function formatMinutesUntil(minutes: number | null | undefined): string | null {
  if (minutes == null || minutes <= 0) return null;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m} min`;
  if (m === 0) return `${h} h`;
  return `${h} h ${m} min`;
}

export function syncLegacyCleaningFields(config: SpaFilterConfig): SpaFilterConfig {
  const totalHours = totalDailyRuntimeHours(config);
  return {
    ...config,
    min_cleaning_hours_per_day: totalHours,
    min_run_minutes: config.filter_duration_minutes,
    min_stop_minutes: config.minimum_cycle_separation_minutes,
    max_starts_per_day: config.filter_cycles_per_day,
  };
}
