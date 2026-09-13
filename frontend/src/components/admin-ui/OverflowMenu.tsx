"use client";

export function OverflowMenu({
  items,
}: {
  items: { label: string; onClick: () => void; danger?: boolean; disabled?: boolean }[];
}) {
  return (
    <details className="admin-overflow-menu">
      <summary className="admin-overflow-trigger" aria-label="Åtgärder">
        ⋯
      </summary>
      <div className="admin-overflow-dropdown" role="menu">
        {items.map((item) => (
          <button
            key={item.label}
            type="button"
            role="menuitem"
            className={`admin-overflow-item${item.danger ? " admin-overflow-danger" : ""}`}
            onClick={item.onClick}
            disabled={item.disabled}
          >
            {item.label}
          </button>
        ))}
      </div>
    </details>
  );
}
