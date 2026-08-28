import type { SpaComponentRow } from "./spaDashboardHelpers";

function statusTone(status: string, powerW: number): "active" | "idle" | "low" {
  if (powerW <= 0 || /^av|off$/i.test(status)) return "idle";
  if (/låg|low/i.test(status)) return "low";
  return "active";
}

function ComponentIcon({ id }: { id: string }) {
  if (id.startsWith("pump")) {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" strokeWidth="1.6" />
        <path d="M12 4v16M4 12h16" stroke="currentColor" strokeWidth="1.4" />
      </svg>
    );
  }
  if (id === "heater") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M12 3c-2 4-4 6-4 9a4 4 0 1 0 8 0c0-3-2-5-4-9z"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
        />
      </svg>
    );
  }
  if (id === "circulation") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M12 4a8 8 0 1 0 8 8M12 4v4M12 4l3 3"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M12 4c3 2 5 4 5 7s-2 5-5 7c-3-2-5-4-5-7s2-5 5-7z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
      />
    </svg>
  );
}

export function SpaComponentCard({ row }: { row: SpaComponentRow }) {
  const tone = statusTone(row.status, row.powerW);
  const detail = row.detail ? ` · ${row.detail}` : "";

  return (
    <li className={`sdash-component-card sdash-component-card-${tone}`}>
      <span className="sdash-component-icon" aria-hidden="true">
        <ComponentIcon id={row.id} />
      </span>
      <div className="sdash-component-copy">
        <span className="sdash-component-label">{row.label}</span>
        <strong>
          {row.powerW > 0 ? `${(row.powerW / 1000).toLocaleString("sv-SE", { maximumFractionDigits: 2 })} kW` : "0 kW"}
          {detail}
        </strong>
        <em>{row.status}</em>
      </div>
    </li>
  );
}
