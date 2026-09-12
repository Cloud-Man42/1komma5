export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="admin-table-skeleton" aria-hidden="true">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="admin-table-skeleton-row skeleton" />
      ))}
    </div>
  );
}
