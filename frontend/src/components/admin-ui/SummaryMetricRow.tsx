export function SummaryMetricRow({ items }: { items: { label: string; value: string | number }[] }) {
  return (
    <div className="admin-summary-row">
      {items.map((item) => (
        <div key={item.label} className="admin-summary-card">
          <span className="admin-summary-value">{item.value}</span>
          <span className="admin-summary-label">{item.label}</span>
        </div>
      ))}
    </div>
  );
}
