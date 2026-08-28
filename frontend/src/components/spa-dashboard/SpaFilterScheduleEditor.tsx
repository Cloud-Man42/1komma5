"use client";

import { useEffect, useMemo, useState } from "react";
import {
  fetchSpaPlan,
  updateSpaControlConfig,
  type SpaControlConfig,
  type SpaPlan,
} from "@/lib/api";
import {
  buildFilterSummaryClient,
  totalDailyRuntimeHours,
  validateFilterPolicyClient,
} from "@/lib/spaCleaningConfig";
import { buildSpaControlUpdatePayload } from "@/lib/spaControlPayload";
import {
  fixedScheduleWarningSv,
  recommendedFixedScheduleTimes,
  strategyLabelSv,
} from "./spaDashboardHelpers";
import { SpaShadowModeToggle } from "./SpaShadowModeToggle";

function formatLocalTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString("sv-SE", { hour: "2-digit", minute: "2-digit" });
}

export function SpaFilterScheduleEditor({
  siteSlug,
  plan,
  control,
  onSaved,
  onControlChanged,
}: {
  siteSlug: string;
  plan: SpaPlan | null;
  control: SpaControlConfig | null;
  onSaved?: () => void;
  onControlChanged?: () => void;
}) {
  const [draft, setDraft] = useState<SpaControlConfig | null>(control);
  const [livePlan, setLivePlan] = useState<SpaPlan | null>(plan);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDraft(control);
  }, [control]);

  useEffect(() => {
    setLivePlan(plan);
  }, [plan]);

  const validationWarning = useMemo(
    () => (draft ? validateFilterPolicyClient(draft) : null),
    [draft],
  );

  const configSummary = useMemo(
    () => (draft ? buildFilterSummaryClient(draft) : null),
    [draft],
  );

  if (!draft) {
    return <p className="sdash-muted">Laddar schema…</p>;
  }

  const windows = livePlan?.daily_windows ?? [];
  const fixedSchedule = draft.strategy === "FIXED_SCHEDULE";
  const fixedScheduleWarning = fixedScheduleWarningSv(draft);
  const recommendedFixed = recommendedFixedScheduleTimes(draft);

  function applyRecommendedFixedSchedule() {
    if (!draft) return;
    setDraft({
      ...draft,
      fixed_schedule_start: recommendedFixed.start,
      fixed_schedule_end: recommendedFixed.end,
    });
  }

  async function handleSave() {
    if (!draft || validationWarning) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const updated = await updateSpaControlConfig(siteSlug, buildSpaControlUpdatePayload(draft));
      setDraft(updated);
      const refreshedPlan = await fetchSpaPlan(siteSlug);
      setLivePlan(refreshedPlan);
      setMessage("Schemat sparades. EMIC räknar om dagens filterplan.");
      onSaved?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte spara schema");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="sdash-schedule-detail" data-testid="spa-filter-schedule-editor">
      <section className="sdash-schedule-section">
        <h3>Dagens plan</h3>
        {!draft.smart_control_enabled ? (
          <p className="sdash-muted">Aktivera smartstyrning nedan för att EMIC ska planera filtercyklerna.</p>
        ) : windows.length === 0 ? (
          <p className="sdash-muted">Ingen plan beräknad ännu. Spara schema så räknas nästa plan om.</p>
        ) : (
          <ul className="sdash-schedule-list">
            {windows.map((window) => (
              <li key={`${window.start}-${window.end}`}>
                <strong>
                  {formatLocalTime(window.start)}–{formatLocalTime(window.end)}
                </strong>
                <span>{window.duration_hours.toLocaleString("sv-SE", { maximumFractionDigits: 1 })} h</span>
                <span>{window.energy_source_label_sv}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="sdash-schedule-section">
        <h3>Redigera schema</h3>
        <p className="sdash-schedule-copy">
          Strategi: <strong>{strategyLabelSv(draft.strategy)}</strong> (byts i SPALÄGE i sidhuvudet).
        </p>
        <div className="sdash-schedule-form">
          <label className="sdash-schedule-field sdash-schedule-field-check">
            <input
              type="checkbox"
              checked={draft.smart_control_enabled}
              onChange={(event) => setDraft({ ...draft, smart_control_enabled: event.target.checked })}
            />
            <span>Smartstyrning aktiv</span>
          </label>

          <label className="sdash-schedule-field sdash-schedule-field-check">
            <input
              type="checkbox"
              checked={draft.filter_optimization_enabled}
              disabled={!draft.smart_control_enabled}
              onChange={(event) =>
                setDraft({ ...draft, filter_optimization_enabled: event.target.checked })
              }
            />
            <span>Smart filteroptimering (EMIC väljer tid inom fönstret)</span>
          </label>

          <label className="sdash-schedule-field">
            <span>Filtercykler per dygn</span>
            <input
              type="number"
              min={1}
              max={8}
              value={draft.filter_cycles_per_day}
              disabled={!draft.smart_control_enabled}
              onChange={(event) =>
                setDraft({ ...draft, filter_cycles_per_day: Number(event.target.value) })
              }
            />
          </label>

          <label className="sdash-schedule-field">
            <span>Varaktighet per cykel (min)</span>
            <input
              type="number"
              min={30}
              max={240}
              step={15}
              value={draft.filter_duration_minutes}
              disabled={!draft.smart_control_enabled}
              onChange={(event) =>
                setDraft({ ...draft, filter_duration_minutes: Number(event.target.value) })
              }
            />
          </label>

          <label className="sdash-schedule-field">
            <span>Minsta paus mellan cykler (min)</span>
            <input
              type="number"
              min={10}
              max={240}
              step={5}
              value={draft.minimum_cycle_separation_minutes}
              disabled={!draft.smart_control_enabled}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  minimum_cycle_separation_minutes: Number(event.target.value),
                })
              }
            />
          </label>

          <label className="sdash-schedule-field">
            <span>Tillåten tid — från</span>
            <input
              type="time"
              value={draft.allowed_window_start}
              disabled={!draft.smart_control_enabled}
              onChange={(event) => setDraft({ ...draft, allowed_window_start: event.target.value })}
            />
          </label>

          <label className="sdash-schedule-field">
            <span>Tillåten tid — till</span>
            <input
              type="time"
              value={draft.allowed_window_end}
              disabled={!draft.smart_control_enabled}
              onChange={(event) => setDraft({ ...draft, allowed_window_end: event.target.value })}
            />
          </label>

          {fixedSchedule ? (
            <>
              {fixedScheduleWarning ? (
                <div className="sdash-schedule-warn" data-testid="fixed-schedule-warning">
                  <p>{fixedScheduleWarning}</p>
                  <p className="sdash-muted">
                    Rekommenderat för Glacier XL ({draft.filter_cycles_per_day}×
                    {Math.max(1, Math.round(draft.filter_duration_minutes / 60))} h):{" "}
                    <strong>
                      {recommendedFixed.start}–{recommendedFixed.end}
                    </strong>{" "}
                    (samma som tillåtet fönster).
                  </p>
                  <button
                    type="button"
                    className="sdash-schedule-apply"
                    disabled={!draft.smart_control_enabled}
                    onClick={applyRecommendedFixedSchedule}
                  >
                    Använd rekommenderat fönster
                  </button>
                </div>
              ) : (
                <p className="sdash-schedule-copy">
                  Eco Pak styr filtercyklerna mellan {draft.fixed_schedule_start} och{" "}
                  {draft.fixed_schedule_end}. EMIC flyttar inte schemat.
                </p>
              )}
              <label className="sdash-schedule-field">
                <span>Fast schema — start</span>
                <input
                  type="time"
                  value={draft.fixed_schedule_start ?? ""}
                  disabled={!draft.smart_control_enabled}
                  onChange={(event) =>
                    setDraft({ ...draft, fixed_schedule_start: event.target.value || null })
                  }
                />
              </label>
              <label className="sdash-schedule-field">
                <span>Fast schema — slut</span>
                <input
                  type="time"
                  value={draft.fixed_schedule_end ?? ""}
                  disabled={!draft.smart_control_enabled}
                  onChange={(event) =>
                    setDraft({ ...draft, fixed_schedule_end: event.target.value || null })
                  }
                />
              </label>
            </>
          ) : null}
        </div>

        {configSummary ? <p className="sdash-schedule-copy">{configSummary}</p> : null}
        <p className="sdash-muted">
          Totalt per dygn:{" "}
          {totalDailyRuntimeHours(draft).toLocaleString("sv-SE", { maximumFractionDigits: 1 })} h filtertid.
        </p>
        {validationWarning ? <p className="sdash-schedule-error">{validationWarning}</p> : null}
        {error ? <p className="sdash-schedule-error">{error}</p> : null}
        {message ? <p className="sdash-schedule-success">{message}</p> : null}

        <button
          type="button"
          className="sdash-schedule-save"
          disabled={saving || !draft.smart_control_enabled || Boolean(validationWarning)}
          onClick={() => void handleSave()}
        >
          {saving ? "Sparar…" : "Spara schema"}
        </button>
      </section>

      <section className="sdash-schedule-section">
        <h3>Shadow mode</h3>
        <SpaShadowModeToggle
          siteSlug={siteSlug}
          control={control}
          onChanged={onControlChanged}
        />
      </section>

      {livePlan?.explanation_sv ? (
        <section className="sdash-schedule-section">
          <h3>Varför detta schema?</h3>
          <p className="sdash-schedule-copy">{livePlan.explanation_sv}</p>
        </section>
      ) : null}
    </div>
  );
}
