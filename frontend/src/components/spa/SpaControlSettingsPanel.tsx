"use client";

import { useEffect, useMemo, useState } from "react";
import {
  SpaControlConfig,
  SpaPlan,
  fetchSpaControlConfig,
  fetchSpaPlan,
  updateSpaControlConfig,
  runSpaCleaningNow,
} from "@/lib/api";
import {
  buildFilterSummaryClient,
  formatCleaningDuration,
  formatMinutesUntil,
  syncLegacyCleaningFields,
  totalDailyRuntimeHours,
  validateFilterPolicyClient,
} from "@/lib/spaCleaningConfig";

const STRATEGIES = [
  { id: "SMART", label: "Smart — pris, sol och batteri" },
  { id: "SOLAR_ONLY", label: "Endast solel" },
  { id: "CHEAPEST", label: "Billigaste energi" },
  { id: "FIXED_SCHEDULE", label: "Fast schema" },
];

function buildUpdatePayload(config: SpaControlConfig): Partial<SpaControlConfig> {
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

function FieldHint({ children }: { children: string }) {
  return <span className="spa-field-hint">{children}</span>;
}

function ToggleRow({
  label,
  hint,
  checked,
  onChange,
  disabled,
}: {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <label className="spa-settings-toggle">
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className="spa-settings-toggle-text">
        <span className="spa-settings-toggle-label">{label}</span>
        {hint && <span className="spa-settings-toggle-hint">{hint}</span>}
      </span>
    </label>
  );
}

function formatLocalTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" });
}

export function SpaControlSettingsPanel({ siteSlug }: { siteSlug: string }) {
  const [config, setConfig] = useState<SpaControlConfig | null>(null);
  const [plan, setPlan] = useState<SpaPlan | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    fetchSpaControlConfig(siteSlug)
      .then(setConfig)
      .catch((e) => setError(e instanceof Error ? e.message : "Kunde inte ladda inställningar"));
    fetchSpaPlan(siteSlug)
      .then(setPlan)
      .catch(() => setPlan(null));
  }, [siteSlug]);

  const validationWarning = useMemo(
    () => (config ? validateFilterPolicyClient(config) : null),
    [config],
  );

  const configSummary = useMemo(
    () => (config ? buildFilterSummaryClient(config) : null),
    [config],
  );

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await updateSpaControlConfig(siteSlug, buildUpdatePayload(config));
      setConfig(updated);
      const refreshedPlan = await fetchSpaPlan(siteSlug);
      setPlan(refreshedPlan);
      setMessage("Inställningar sparade.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Kunde inte spara");
    } finally {
      setSaving(false);
    }
  };

  const handleRunNow = async () => {
    setRunning(true);
    setError(null);
    setMessage(null);
    try {
      const result = await runSpaCleaningNow(siteSlug);
      setMessage(result.message);
      const refreshedPlan = await fetchSpaPlan(siteSlug);
      setPlan(refreshedPlan);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Kunde inte starta cleaning");
    } finally {
      setRunning(false);
    }
  };

  if (!config) return <p className="muted">Laddar energiinställningar…</p>;

  const fixedSchedule = config.strategy === "FIXED_SCHEDULE";
  const dailyTarget = plan?.daily_target_hours ?? totalDailyRuntimeHours(config);
  const dailyCompleted = plan?.daily_completed_hours ?? 0;
  const progressPct = plan?.daily_progress_pct ?? 0;
  const plannedStarts = plan?.planned_starts ?? 0;
  const maxStarts = plan?.max_starts_per_day ?? config.filter_cycles_per_day;
  const cycleHours = config.filter_duration_minutes / 60;
  const nextCycleLabel =
    plan?.next_cleaning_start && plan?.next_cleaning_end
      ? `${formatLocalTime(plan.next_cleaning_start)}–${formatLocalTime(plan.next_cleaning_end)}`
      : null;
  const startsIn = formatMinutesUntil(plan?.next_cycle_starts_in_minutes ?? null);

  return (
    <section className="card spa-settings-panel" data-testid="spa-control-settings">
      <header className="spa-settings-header">
        <h3>Inställningar — Energi</h3>
        <p className="muted">
          Styr hur EMIC planerar spa-filtrering och förvärmning. Alla temperaturer anges i grader Celsius (°C).
        </p>
      </header>

      <div className="config-form">
        <fieldset className="spa-settings-section">
          <legend>Styrning</legend>
          <div className="spa-settings-toggles">
            <ToggleRow
              label="Smartstyrning"
              hint="Aktiverar automatisk planering och styrning av filter/cleaning."
              checked={config.smart_control_enabled}
              onChange={(checked) => setConfig({ ...config, smart_control_enabled: checked })}
            />
          </div>
          <div className="form-grid">
            <label className="form-field form-field-wide">
              <span>Strategi</span>
              <select
                value={config.strategy}
                onChange={(e) => setConfig({ ...config, strategy: e.target.value })}
              >
                {STRATEGIES.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </fieldset>

        <fieldset className="spa-settings-section">
          <legend>Test &amp; validering</legend>
          <div className="spa-settings-toggles">
            <ToggleRow
              label="Testläge (dry run)"
              hint="Planerar och loggar beslut utan att skicka kommandon till spabadet."
              checked={config.dry_run}
              onChange={(checked) => setConfig({ ...config, dry_run: checked })}
            />
            <ToggleRow
              label="Shadow mode"
              hint="Jämför EMIC:s plan mot faktiskt beteende utan att ta över styrningen."
              checked={config.shadow_mode}
              onChange={(checked) => setConfig({ ...config, shadow_mode: checked })}
            />
          </div>
        </fieldset>

        <fieldset className="spa-settings-section">
          <legend>Filter &amp; cleaning</legend>
          <div className="spa-filter-baseline" data-testid="filter-baseline">
            <p className="spa-filter-baseline-title">Arctic Spa grundschema</p>
            <ul className="spa-filter-baseline-list">
              <li>{config.filter_cycles_per_day} cykler per dygn</li>
              <li>{cycleHours} timmar per cykel</li>
              <li>{totalDailyRuntimeHours(config)} timmar totalt</li>
            </ul>
            <dl className="spa-filter-control-status">
              <div>
                <dt>Filterkontroll</dt>
                <dd>{plan?.filter_control_source_sv ?? "Arctic Spa"}</dd>
              </div>
              <div>
                <dt>Tidsoptimering</dt>
                <dd>
                  {plan?.timing_optimization_source_sv ??
                    (config.filter_optimization_enabled ? "EMIC" : "Inaktiv")}
                </dd>
              </div>
            </dl>
          </div>
          <div className="spa-settings-toggles">
            <ToggleRow
              label="Smart filteroptimering"
              hint="EMIC ändrar när de fyra filtercyklerna körs men ändrar inte den totala filtreringstiden."
              checked={config.filter_optimization_enabled}
              onChange={(checked) =>
                setConfig({ ...config, filter_optimization_enabled: checked })
              }
            />
          </div>
          <div className="form-grid">
            <label className="form-field">
              <span>Filtercykler per dygn</span>
              <FieldHint>Fast antal sammanhängande cykler (standard 4).</FieldHint>
              <input
                type="number"
                min={1}
                max={8}
                step={1}
                value={config.filter_cycles_per_day}
                onChange={(e) =>
                  setConfig({ ...config, filter_cycles_per_day: Number(e.target.value) })
                }
              />
            </label>
            <label className="form-field">
              <span>Varaktighet per cykel (min)</span>
              <FieldHint>Sammanhängande tid per cykel — delas inte upp (standard 120).</FieldHint>
              <input
                type="number"
                min={30}
                max={240}
                step={15}
                value={config.filter_duration_minutes}
                onChange={(e) =>
                  setConfig({ ...config, filter_duration_minutes: Number(e.target.value) })
                }
              />
            </label>
            <label className="form-field">
              <span>Minsta paus mellan cykler (min)</span>
              <FieldHint>Spridning över dygnet — cykler slås inte ihop.</FieldHint>
              <input
                type="number"
                min={10}
                max={240}
                step={5}
                value={config.minimum_cycle_separation_minutes}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    minimum_cycle_separation_minutes: Number(e.target.value),
                  })
                }
              />
            </label>
            <label className="form-field">
              <span>Tillåten tid — från</span>
              <input
                type="time"
                value={config.allowed_window_start}
                onChange={(e) => setConfig({ ...config, allowed_window_start: e.target.value })}
              />
            </label>
            <label className="form-field">
              <span>Tillåten tid — till</span>
              <input
                type="time"
                value={config.allowed_window_end}
                onChange={(e) => setConfig({ ...config, allowed_window_end: e.target.value })}
              />
            </label>
            {fixedSchedule && (
              <>
                <label className="form-field">
                  <span>Fast schema — start</span>
                  <input
                    type="time"
                    value={config.fixed_schedule_start ?? ""}
                    onChange={(e) =>
                      setConfig({ ...config, fixed_schedule_start: e.target.value || null })
                    }
                  />
                </label>
                <label className="form-field">
                  <span>Fast schema — slut</span>
                  <input
                    type="time"
                    value={config.fixed_schedule_end ?? ""}
                    onChange={(e) =>
                      setConfig({ ...config, fixed_schedule_end: e.target.value || null })
                    }
                  />
                </label>
              </>
            )}
          </div>

          {configSummary && (
            <p className="spa-settings-summary" data-testid="cleaning-config-summary">
              <strong>{configSummary}</strong>
            </p>
          )}
          {plan?.optimization_hint_sv && (
            <p className="spa-field-hint">{plan.optimization_hint_sv}</p>
          )}
          {validationWarning && (
            <p className="form-error" data-testid="cleaning-config-validation">
              {validationWarning}
            </p>
          )}
        </fieldset>

        {config.smart_control_enabled && (
          <fieldset className="spa-settings-section" data-testid="cleaning-daily-plan">
            <legend>Dagens filterplan</legend>
            {nextCycleLabel && (
              <div className="spa-next-cycle" data-testid="next-filter-cycle">
                <p className="spa-next-cycle-title">Nästa filtercykel</p>
                <p className="spa-next-cycle-time">{nextCycleLabel}</p>
                {startsIn && <p className="muted">Startar om: {startsIn}</p>}
              </div>
            )}
            {plan?.enabled && plan.daily_windows.length > 0 ? (
              <>
                <p className="muted">Planerat idag</p>
                <ul className="spa-cleaning-plan-list">
                  {plan.daily_windows.map((window) => (
                    <li key={`${window.start}-${window.end}`}>
                      <span className="spa-cleaning-plan-time">
                        {formatLocalTime(window.start)}–{formatLocalTime(window.end)}
                      </span>
                      <span className="spa-cleaning-plan-duration">
                        {window.duration_hours} h
                      </span>
                      <span className="spa-cleaning-plan-source">{window.energy_source_label_sv}</span>
                    </li>
                  ))}
                </ul>
                <div className="spa-cleaning-plan-totals">
                  <span>
                    {plannedStarts} av {maxStarts} cykler planerade
                  </span>
                  <span>
                    {formatCleaningDuration(
                      plan.daily_windows.reduce((sum, w) => sum + w.duration_hours, 0),
                    )}{" "}
                    av {formatCleaningDuration(dailyTarget)}
                  </span>
                </div>
              </>
            ) : (
              <p className="muted">Ingen plan tillgänglig ännu — spara inställningar eller vänta på nästa planeringscykel.</p>
            )}

            <div className="spa-cleaning-progress" data-testid="cleaning-daily-progress">
              <div className="spa-cleaning-progress-header">
                <span>Filtrering idag</span>
                <span>
                  {formatCleaningDuration(dailyCompleted)} / {formatCleaningDuration(dailyTarget)}
                </span>
              </div>
              <div className="spa-cleaning-progress-bar" role="progressbar" aria-valuenow={progressPct} aria-valuemin={0} aria-valuemax={100}>
                <div className="spa-cleaning-progress-fill" style={{ width: `${progressPct}%` }} />
              </div>
              <p className="spa-cleaning-progress-label">{progressPct} % klart</p>
            </div>
          </fieldset>
        )}

        <fieldset className="spa-settings-section">
          <legend>Energikällor</legend>
          <div className="spa-settings-toggles">
            <ToggleRow
              label="Prioritera solel"
              hint="Försök köra cleaning när solproduktion finns tillgänglig."
              checked={config.prefer_solar}
              onChange={(checked) => setConfig({ ...config, prefer_solar: checked })}
            />
            <ToggleRow
              label="Tillåt batteri"
              hint="Tillåt att spa-filtrering drar från hembatteriet inom gränserna nedan."
              checked={config.allow_battery}
              onChange={(checked) => setConfig({ ...config, allow_battery: checked })}
            />
          </div>
          <div className="form-grid">
            <label className="form-field">
              <span>Min batterinivå (%)</span>
              <input
                type="number"
                min={10}
                max={90}
                value={config.min_battery_soc_pct}
                onChange={(e) =>
                  setConfig({ ...config, min_battery_soc_pct: Number(e.target.value) })
                }
                disabled={!config.allow_battery}
              />
            </label>
            <label className="form-field">
              <span>Lastprioritet (0–100)</span>
              <input
                type="number"
                min={0}
                max={100}
                value={config.load_priority}
                onChange={(e) => setConfig({ ...config, load_priority: Number(e.target.value) })}
              />
            </label>
          </div>
        </fieldset>

        <fieldset className="spa-settings-section">
          <legend>Temperatur (°C)</legend>
          <div className="spa-settings-toggles">
            <ToggleRow
              label="Smart förvärmning"
              hint="Planerar förvärmning inför användning inom angivna temperaturgränser."
              checked={config.smart_preheat_enabled}
              onChange={(checked) => setConfig({ ...config, smart_preheat_enabled: checked })}
            />
          </div>
          <div className="form-grid">
            <label className="form-field">
              <span>Normaltemperatur (°C)</span>
              <input
                type="number"
                min={30}
                max={42}
                step={0.5}
                value={config.normal_temperature_c}
                onChange={(e) =>
                  setConfig({ ...config, normal_temperature_c: Number(e.target.value) })
                }
              />
            </label>
            <label className="form-field">
              <span>Max förvärmning (°C)</span>
              <input
                type="number"
                min={30}
                max={42}
                step={0.5}
                value={config.max_preheat_temperature_c}
                onChange={(e) =>
                  setConfig({ ...config, max_preheat_temperature_c: Number(e.target.value) })
                }
                disabled={!config.smart_preheat_enabled}
              />
            </label>
            <label className="form-field">
              <span>Min komfort (°C)</span>
              <input
                type="number"
                min={30}
                max={42}
                step={0.5}
                value={config.min_comfort_temperature_c}
                onChange={(e) =>
                  setConfig({ ...config, min_comfort_temperature_c: Number(e.target.value) })
                }
                disabled={!config.smart_preheat_enabled}
              />
            </label>
          </div>
        </fieldset>

        <div className="spa-settings-actions">
          <button type="button" className="btn-primary" disabled={saving} onClick={() => void handleSave()}>
            {saving ? "Sparar…" : "Spara inställningar"}
          </button>
          <button
            type="button"
            className="btn-secondary"
            disabled={running || !config.smart_control_enabled}
            onClick={() => void handleRunNow()}
          >
            {running ? "Startar…" : "Kör cleaning nu"}
          </button>
        </div>
        {message && <p className="form-success">{message}</p>}
        {error && <p className="form-error">{error}</p>}
      </div>
    </section>
  );
}
