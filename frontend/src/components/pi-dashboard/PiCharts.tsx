/** SVG chart primitives for the Pi kiosk dashboard. */

/** Builds an area + stroke path pair from a value series. */
function areaPaths(values: number[], width = 100, height = 100, pad = 2) {
  if (values.length < 2) return null;
  let min = Math.min(...values);
  let max = Math.max(...values);
  if (max - min < 1e-6) {
    // Flat series still needs a visible baseline rather than a divide-by-zero.
    max = min + 1;
  }
  // Keep zero in frame for signed series (grid import/export) so the sign reads.
  if (min > 0 && min < (max - min) * 0.35) min = 0;

  const span = max - min;
  const usable = height - pad;
  const step = width / (values.length - 1);
  const points = values.map((value, index) => {
    const x = index * step;
    const y = pad + (1 - (value - min) / span) * usable;
    return [x, y] as const;
  });

  const line = points.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`).join("");
  const area = `${line}L${width} ${height}L0 ${height}Z`;
  return { line, area };
}

export function PiAreaChart({
  values,
  colour,
  gradientId,
  className,
}: {
  values: number[];
  colour: string;
  gradientId: string;
  className?: string;
}) {
  const paths = areaPaths(values);
  return (
    <svg
      className={className}
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      aria-hidden
      focusable="false"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={colour} stopOpacity="0.55" />
          <stop offset="60%" stopColor={colour} stopOpacity="0.12" />
          <stop offset="100%" stopColor={colour} stopOpacity="0" />
        </linearGradient>
      </defs>
      {paths ? (
        <>
          <path d={paths.area} fill={`url(#${gradientId})`} />
          <path
            d={paths.line}
            fill="none"
            stroke={colour}
            strokeWidth="1.4"
            strokeLinejoin="round"
            strokeLinecap="round"
            vectorEffect="non-scaling-stroke"
          />
        </>
      ) : null}
      <line
        x1="0"
        y1="99.4"
        x2="100"
        y2="99.4"
        stroke="#16232f"
        strokeWidth="1"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

const GAUGE_R = 42;
const GAUGE_SWEEP = 0.75; // 270deg dial, gap at the bottom
const GAUGE_CIRC = 2 * Math.PI * GAUGE_R;

/**
 * Circular surplus gauge, as drawn in the reference: a 270-degree dial with the
 * gap at the bottom. The green remainder is the full sweep; the amber arc laid
 * over it is the surplus share, so the split point encodes the live value while
 * the ring itself always keeps the same footprint.
 */
/**
 * The reference leaves a short slice of bare groove at the dial's start before
 * the coloured arcs begin, so the arcs are drawn over the trailing 90% of the
 * sweep rather than all of it.
 */
const GAUGE_LEAD_IN = 0.1;

export function PiGauge({ fraction }: { fraction: number | null }) {
  const filled = fraction == null ? 0 : Math.min(1, Math.max(0, fraction));
  const trackLength = GAUGE_CIRC * GAUGE_SWEEP;
  const lead = trackLength * GAUGE_LEAD_IN;
  const arcLength = trackLength - lead;
  const valueLength = arcLength * filled;

  return (
    <svg viewBox="0 0 100 100" aria-hidden focusable="false">
      <g transform="rotate(135 50 50)">
        {/* unfilled dial groove */}
        <circle
          cx="50"
          cy="50"
          r={GAUGE_R}
          fill="none"
          stroke="#2d3947"
          strokeWidth="10.5"
          strokeLinecap="round"
          strokeDasharray={`${trackLength} ${GAUGE_CIRC}`}
        />
        {fraction != null ? (
          <circle
            cx="50"
            cy="50"
            r={GAUGE_R}
            fill="none"
            stroke="#21cc3e"
            strokeWidth="10.5"
            strokeLinecap="round"
            strokeDasharray={`${arcLength} ${GAUGE_CIRC}`}
            strokeDashoffset={-lead}
          />
        ) : null}
        {valueLength > 1 ? (
          <circle
            cx="50"
            cy="50"
            r={GAUGE_R}
            fill="none"
            stroke="#f9b208"
            strokeWidth="10.5"
            strokeLinecap="round"
            strokeDasharray={`${valueLength} ${GAUGE_CIRC}`}
            strokeDashoffset={-lead}
            style={{ filter: "drop-shadow(0 0 2.5px rgba(249, 178, 8, 0.5))" }}
          />
        ) : null}
      </g>
    </svg>
  );
}

export interface EconomyDay {
  day: number;
  savings_sek: number;
  cost_sek: number;
  net_sek: number;
}

/** Rounds an axis maximum up to a readable step (100/200/300/500/1000...). */
function axisMax(values: number[]): number {
  const peak = Math.max(100, ...values.map((v) => Math.abs(v)));
  const steps = [100, 200, 300, 500, 750, 1000, 1500, 2000, 3000, 5000];
  return steps.find((step) => step >= peak) ?? Math.ceil(peak / 1000) * 1000;
}

export function PiEconomyBars({ daily }: { daily: EconomyDay[] }) {
  if (daily.length === 0) {
    return <div className="pi-empty">Data saknas</div>;
  }

  const max = axisMax(daily.flatMap((d) => [d.savings_sek, d.cost_sek, d.net_sek]));
  const groupWidth = 100 / daily.length;
  const barWidth = Math.min(1.8, groupWidth * 0.32);
  const gap = barWidth * 0.28;
  const zeroY = 50;
  const scale = (value: number) => (value / max) * 50;

  /**
   * `sign` forces the plotted direction: the reference draws savings above the
   * axis and cost below it regardless of how the API reports cost, while net
   * keeps its own sign.
   */
  const series: { key: keyof EconomyDay; color: string; offset: number; sign: 1 | -1 | 0 }[] = [
    { key: "savings_sek", color: "#21cc3e", offset: -(barWidth + gap), sign: 1 },
    { key: "cost_sek", color: "#ab37c3", offset: 0, sign: -1 },
    { key: "net_sek", color: "#3aa0e8", offset: barWidth + gap, sign: 0 },
  ];

  const ticks = [
    { label: `${max}`, y: 0 },
    { label: "0", y: zeroY },
    { label: `\u2212${max}`, y: 100 },
  ];

  return (
    <div className="pi-bars">
      <div className="pi-bars-axis">
        <span className="pi-bars-unit">kr</span>
        {ticks.map((tick) => (
          <span key={tick.label} style={{ top: `${tick.y}%` }}>
            {tick.label}
          </span>
        ))}
      </div>
      <svg
        className="pi-bars-svg"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        aria-hidden
        focusable="false"
      >
        <line
          x1="0"
          y1={zeroY}
          x2="100"
          y2={zeroY}
          stroke="#1b2a38"
          strokeWidth="1"
          vectorEffect="non-scaling-stroke"
        />
        {daily.map((point, index) => {
          const centre = groupWidth * (index + 0.5);
          return series.map(({ key, color, offset, sign }) => {
            const raw = point[key] as number;
            const directed = sign === 0 ? raw : sign * Math.abs(raw);
            const magnitude = Math.max(0.6, Math.abs(scale(directed)));
            const y = directed >= 0 ? zeroY - magnitude : zeroY;
            return (
              <rect
                key={`${point.day}-${key}`}
                x={centre + offset - barWidth / 2}
                y={y}
                width={barWidth}
                height={magnitude}
                fill={color}
                rx="0.4"
              />
            );
          });
        })}
      </svg>
    </div>
  );
}

/** X-axis labels for the economy chart: first, quarter marks and last day. */
export function economyAxisLabels(daily: EconomyDay[], monthIndex: number): string[] {
  if (daily.length === 0) return [];
  const month = monthIndex + 1;
  const positions = [0, 0.25, 0.5, 0.75, 1].map((f) => Math.round(f * (daily.length - 1)));
  return [...new Set(positions)].map((i) => `${daily[i].day}/${month}`);
}
