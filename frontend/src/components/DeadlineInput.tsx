"use client";

import { combineDeadlineLocal, parseDeadlineLocal } from "@/lib/deadlineInput";

type DeadlineInputProps = {
  value?: string | null;
  onChange?: (iso: string | null) => void;
  dateName?: string;
  timeName?: string;
  idPrefix?: string;
  disabled?: boolean;
};

export function DeadlineInput({
  value,
  onChange,
  dateName = "deadline_date",
  timeName = "deadline_time",
  idPrefix = "deadline",
  disabled = false,
}: DeadlineInputProps) {
  const parts = parseDeadlineLocal(value);
  const dateId = `${idPrefix}-date`;
  const timeId = `${idPrefix}-time`;

  const handleDateChange = (nextDate: string) => {
    if (!onChange) return;
    if (!nextDate) {
      onChange(null);
      return;
    }
    onChange(combineDeadlineLocal(nextDate, parts.time || "07:00"));
  };

  const handleTimeChange = (nextTime: string) => {
    if (!onChange) return;
    if (!parts.date) return;
    onChange(combineDeadlineLocal(parts.date, nextTime));
  };

  return (
    <div className="deadline-input-row" lang="sv-SE">
      <label className="deadline-input-part" htmlFor={dateId}>
        <span className="deadline-input-label">Datum</span>
        <input
          id={dateId}
          type="date"
          lang="sv-SE"
          name={onChange ? undefined : dateName}
          value={onChange ? parts.date : undefined}
          defaultValue={onChange ? undefined : parts.date}
          disabled={disabled}
          onChange={onChange ? (event) => handleDateChange(event.target.value) : undefined}
        />
      </label>
      <label className="deadline-input-part" htmlFor={timeId}>
        <span className="deadline-input-label">Kl</span>
        <input
          id={timeId}
          type="time"
          lang="sv-SE"
          step={60}
          name={onChange ? undefined : timeName}
          value={onChange ? parts.time : undefined}
          defaultValue={onChange ? undefined : parts.time}
          disabled={disabled}
          onChange={onChange ? (event) => handleTimeChange(event.target.value) : undefined}
        />
      </label>
    </div>
  );
}
