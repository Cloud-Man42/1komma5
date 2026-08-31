export function PiSparkline({
  values,
  color,
  fill,
}: {
  values: number[];
  color: string;
  fill?: string;
}) {
  if (values.length < 2) {
    return <svg className="pi-sparkline" viewBox="0 0 120 28" aria-hidden="true" />;
  }

  const width = 120;
  const height = 28;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  const coords = values.map((value, index) => {
    const x = (index / (values.length - 1)) * width;
    const y = height - ((value - min) / range) * (height - 4) - 2;
    return { x, y };
  });
  const line = coords.map((p) => `${p.x},${p.y}`).join(" ");
  const area = `${coords[0]?.x ?? 0},${height} ${line} ${coords[coords.length - 1]?.x ?? width},${height}`;

  return (
    <svg className="pi-sparkline" viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      {fill ? <polygon points={area} fill={fill} stroke="none" opacity={0.35} /> : null}
      <polyline points={line} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
    </svg>
  );
}
