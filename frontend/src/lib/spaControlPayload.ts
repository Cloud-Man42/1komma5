import type { SpaControlConfig } from "@/lib/api";
import { syncLegacyCleaningFields } from "@/lib/spaCleaningConfig";

export function buildSpaControlUpdatePayload(config: SpaControlConfig): Partial<SpaControlConfig> {
  const legacy = syncLegacyCleaningFields(config);
  return {
    smart_control_enabled: config.smart_control_enabled,
    strategy: config.strategy,
    dry_run: config.dry_run,
    shadow_mode: config.shadow_mode,
    min_cleaning_hours_per_day: legacy.min_cleaning_hours_per_day,
    allowed_window_start: config.allowed_window_start,
    allowed_window_end: config.allowed_window_end,
    prefer_solar: config.prefer_solar,
    allow_battery: config.allow_battery,
    min_battery_soc_pct: config.min_battery_soc_pct,
    min_run_minutes: legacy.min_run_minutes,
    min_stop_minutes: legacy.min_stop_minutes,
    max_starts_per_day: legacy.max_starts_per_day,
    filter_cycles_per_day: config.filter_cycles_per_day,
    filter_duration_minutes: config.filter_duration_minutes,
    minimum_cycle_separation_minutes: config.minimum_cycle_separation_minutes,
    filter_optimization_enabled: config.filter_optimization_enabled,
    load_priority: config.load_priority,
    smart_preheat_enabled: config.smart_preheat_enabled,
    normal_temperature_c: config.normal_temperature_c,
    max_preheat_temperature_c: config.max_preheat_temperature_c,
    min_comfort_temperature_c: config.min_comfort_temperature_c,
    fixed_schedule_start: config.fixed_schedule_start,
    fixed_schedule_end: config.fixed_schedule_end,
  };
}
