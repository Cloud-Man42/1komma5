export type DeadlineParts = {
  date: string;
  time: string;
};

export function parseDeadlineLocal(iso: string | null | undefined): DeadlineParts {
  if (!iso) return { date: "", time: "" };
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return { date: "", time: "" };
  const pad = (value: number) => String(value).padStart(2, "0");
  return {
    date: `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`,
    time: `${pad(date.getHours())}:${pad(date.getMinutes())}`,
  };
}

export function combineDeadlineLocal(date: string, time: string): string | null {
  const trimmedDate = date.trim();
  if (!trimmedDate) return null;
  const trimmedTime = time.trim() || "07:00";
  const combined = new Date(`${trimmedDate}T${trimmedTime}`);
  if (Number.isNaN(combined.getTime())) return null;
  return combined.toISOString();
}

export function formatDeadline(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("sv-SE", {
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

/** @deprecated Use parseDeadlineLocal instead. */
export function toDatetimeLocalValue(iso: string | null | undefined): string {
  const { date, time } = parseDeadlineLocal(iso);
  if (!date) return "";
  return `${date}T${time}`;
}
