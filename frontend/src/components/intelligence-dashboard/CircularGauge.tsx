export function CircularGauge({
  value,
  label,
  sublabel,
  color = "#4ade80",
  size = 140,
}: {
  value: number;
  label: string;
  sublabel?: string;
  color?: string;
  size?: number;
}) {
  const clamped = Math.min(100, Math.max(0, value));
  const stroke = 10;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;

  return (
    <div className="idash-circular-gauge" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(148,163,184,0.15)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          className="idash-circular-gauge-fill"
        />
      </svg>
      <div className="idash-circular-gauge-center">
        <strong>{label}</strong>
        {sublabel ? <span>{sublabel}</span> : null}
      </div>
    </div>
  );
}
